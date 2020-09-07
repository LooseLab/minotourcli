import logging
import os
import sys
import time

from .version import __version__
from minFQ.minotourapi import MinotourAPI

CLIENT_VERSION = "1.0"


class SequencingStatistics:
    """
    A class to store data about the sequencing, between different threads.
    """
    def __init__(self):
        self.files_seen = 0,
        self.files_processed = 0,
        self.files_skipped = 0,
        self.reads_seen = 0,
        self.reads_corrupt = 0,
        self.reads_skipped = 0,
        self.reads_uploaded = 0,
        self.fastq_message = "No Fastq Seen",
        self.update = False,
        self.read_up_time = time.time(),
        self.read_count = 0,
        self.directory_watch_list = []

    @property
    def elapsed(self):
        """

        Returns
        -------

        """
        return self.convert(time.time() - self.read_up_time)

    def convert(self, seconds):
        """
        Convert seconds to Hours:Minutes:Seconds format
        Returns
        -------
        str
            Hours:Minutes:Seconds format generated from given second amount
        """
        min, sec = divmod(seconds, 60)
        hour, min = divmod(min, 60)
        return "%d:%02d:%02d" % (hour, min, sec)


def write_out_fastq_stats(upload_stats, line_counter):
    """
    Write out information to the terminal about our fastq monitoring
    Parameters
    ----------
    upload_stats: minFQ.utils.SequencingStatistics
        Class with statistics and info about our monitoring
    line_counter: int
        The number of lines that we need to clear from the terminal print out

    Returns
    -------
    int


    """
    sys.stdout.write("{}\n".format(upload_stats.fastq_message))
    sys.stdout.write("FastQ Upload Status:\n")
    sys.stdout.write(
        "Files queued/processed/skipped/time elapsed:{}/{}/{}/{}\n".format(
            upload_stats.files_seen - upload_stats.files_processed - upload_stats.files_skipped,
            upload_stats.files_processed,
            upload_stats.files_skipped,
            upload_stats.elapsed,
        )
    )
    sys.stdout.write(
        "New reads seen/uploaded/skipped:{}/{}/{}\n".format(
            upload_stats.reads_seen - upload_stats.reads_uploaded - upload_stats.reads_skipped,
            upload_stats.reads_uploaded,
            upload_stats.reads_skipped,
        )
    )
    return line_counter + 5


def check_upload_directories(upload_stats, WATCH_DICT, event_handler, observer, log):
    """
    Check the watch list of directories to see if we've added a new one. If we have,
    unschedule the watch dog observer, and restart it with the old directories and this new one as well
    Parameters
    ----------
    upload_stats: minFQ.utils.SequencingStatistics
        Class with statistics and info about our monitoring
    WATCH_DICT: dict
        A dictionary of Files we are watching
    event_handler: minFQ.fastqutils.FastqHandler
        File class handler
    observer: watchdog.observers.polling.PollingObserver
        The observer that watches the listed directories for change
    log: logging.Logger
        The logger that we are using in this file

    Returns
    -------
    None
    """
    for folder in upload_stats.directory_watch_list:
        if folder and folder not in WATCH_DICT:
            # We have a new folder that hasn't been added.
            # We need to add this to our list to schedule and catalogue the files.
            upload_stats.update = True
            WATCH_DICT[folder] = {}
            event_handler.addfolder(folder)
            log.info("FastQ Monitoring added for {}".format(folder))
    if upload_stats.update:
        observer.unschedule_all()
        for folder in upload_stats.directory_watch_list:
            if folder and os.path.exists(folder):
                observer.schedule(
                    event_handler, path=folder, recursive=True
                )
        upload_stats.update = False


def check_server_compatibility(minotour_api, log):
    """
    Check the minoTOur servers compatibility with minFQ
    Parameters
    ----------
    minotour_api: minFQ.minotourapi.MinotourAPI
        Minotour api connection Class
    log: logging.Logger
        Logger for this script

    Returns
    -------
    None
    """
    version = minotour_api.get_server_version()
    if not version:
        log.error(
            "Server does not support this client. Please change the client to a previous version or upgrade server."
        )
        sys.exit()
    clients = version["clients"]
    if CLIENT_VERSION not in clients:
        print(CLIENT_VERSION)
        log.error(
            "Server does not support this client. Please change the client to a previous version or upgrade server."
        )
        sys.exit()


def check_job_from_client(args, log, minotour_api, parser):
    """
    Start a job from the minFQ client if specified by user.

    Parameters
    ----------
    args: argparse.Namespace
        Namespace for chosen arguments after parsing
    log: logging.Logger
        The logger for this script
    minotour_api: minFQ.minotourapi.MinotourAPI
        API class for connecting to minoTour
    parser: configargparse.ArgumentParser
        command line argument parser
    Returns
    -------

    """
    args.job = int(args.job)
    # Get availaible jobs
    jobs = minotour_api.get_job_options()
    if args.job not in jobs:
        parser.error("Can't find the job type chosen. Please double check that it is the same ID shown by --list.")

    if args.job == "minimap2" or args.job == 4:
        if args.reference == None:
            log.warning("You need to specify a reference for a Minimap2 task.")
            sys.exit(0)
        references = minotour_api.get_references({"cli": True})["data"]
        if args.reference not in references:
            log.error("Reference not found. Please recheck.")
            sys.exit(0)
    if args.job == "metagenomics" or args.job == 10:
        if args.targets:
            targets = minotour_api.get_target_sets(args.api_key)
            if args.targets not in targets:
                log.info(
                    "Target set not found. Please check spelling and try again."
                )
                sys.exit(0)

    if (
            args.job == 16
            or args.job == "track_artic_coverage"
    ):
        log.info("Starting the Artic task.")


def list_minotour_options(log, args, minotour_api):
    """
    List the options for jobs we can start, references and threat sets for metagenomics
    Parameters
    ----------
    log: logging.Logger
        The logger for this script
    args: argparse.Namespace
        Namespace for chosen arguments after parsing
    minotour_api: minFQ.minotourapi.MinotourAPI
        Dictionary of header info for requests sent to minoTour

    Returns
    -------
    None

    """
    log.info("Checking available jobs.")
    # TODO combine below into new single API end point
    jobs = minotour_api.get_job_options()
    references = minotour_api.get_references()["data"]
    targets = minotour_api.get_target_sets(args.api_key)
    log.info("The following jobs are available on this minoTour installation:")
    for job_id, job_info in jobs["data"].items():
        if not job_info["name"].startswith("Delete"):
            log.info(
                "\t{}:{}".format(job_id, job_info["name"].lower().replace(" ", "_"))
            )
    log.info(
        "If you wish to run an alignment, the following references are available:"
    )
    for reference in references:
        log.info("\t{}:{}".format(reference["id"], reference["name"]))
    log.info(
        "If you wish to add a target set to the metagenomics task, the following sets are available to you:"
    )
    for target in targets:
        log.info("\t:{}".format(target))
    sys.exit(0)


def validate_args(args, parser):
    """
    Check the args before setting up all connections. Error out if any mistakes are found.
    Parameters
    ----------
    args: argparse.Namespace
        Namespace for chosen arguments after parsing
    parser: configargparse.ArgumentParser
        command line argument parser

    Returns
    -------
    None
    """
    if args.toml is not None:
        if not os.path.exists(args.toml):
            parser.error(
                "Toml file not found in this location. "
                "Please check that the specified file path is correct."
            )
    if args.unblocks is not None:
        if not os.path.exists(args.unblocks):
            parser.error(
                "Unblocked read ids file not found in this location. "
                "Please check that the specified file path is correct."
            )
    if args.no_fastq and args.no_minknow:
        parser.error("You must monitor either FastQ or MinKNOW.\n This program will now exit.")
    if not args.no_minknow and args.ip is None:
        parser.error(
            "To monitor MinKNOW in real time you must specify the IP address of your local machine.\nUsually: -ip 127.0.0.1"
        )
    return None


def add_args(parser):
    """
    Add arguments to the command line parser, de-cluttering main
    Parameters
    ----------
    parser: configargparse.ArgumentParser
        command line argument parser
    Returns
    -------
    parser: configargparse.ArgumentParser
        parser class updated with the command line arguments to accept
    """
    parser.add_argument(
        "-hn",
        "--hostname",
        type=str,
        # required=True,
        default="127.0.0.1",
        help="The host name for the minoTour server.",
        dest="host_name",
    )

    parser.add_argument(
        "-p",
        "--port",
        type=int,
        # required=True,
        default=80,
        help="The port number for the minoTour server.",
        dest="port_number",
    )

    parser.add_argument(
        "-k",
        "--key",
        type=str,
        required=True,
        default=None,
        help="The api key for uploading data.",
        dest="api_key",
    )

    parser.add_argument(
        "-w",
        "--watch-dir",
        type=str,
        # required=True,
        default=None,
        help="The path to the folder containing the downloads directory with fast5 reads to analyse - e.g. C:\\data\\minion\\downloads (for windows).",
        dest="watchdir",
    )

    parser.add_argument(
        "-i",
        "--ignore_existing",
        action="store_true",
        required=False,
        default=False,
        help="The client will ignore previously existing fastq files and will only monitor newly created files..",
        dest="ignoreexisting",
    )

    parser.add_argument(
        "-s",
        "--skip_sequence",
        action="store_true",
        required=False,
        help="If selected only read metrics, not sequence, will be uploaded to the databse.",
        dest="skip_sequence",
    )

    parser.add_argument(
        "-nf",
        "--no_fastq",
        action="store_true",
        help="Run minFQ without monitoring fastq files.",
        default=False,
        dest="no_fastq",
    )

    parser.add_argument(
        "-nm",
        "--no_minknow",
        action="store_true",
        help="Run minFQ without monitoring minKNOW for live activity.",
        default=False,
        dest="no_minknow",
    )

    parser.add_argument(
        "-rc",
        "--remote_control",
        action="store_true",
        default=False,
        help="This option allows your runs to be remotely started and stopped and for runs to be remotely renamed. As standard this is not enbabled.",
        dest="enable_remote",
    )

    parser.add_argument(
        "-ip",
        "--ip-address",
        type=str,
        dest="ip",
        required=False,
        default=None,
        help="The IP address of the minKNOW machine - Typically 127.0.0.1.",
    )

    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default=None,
        help="This provides a backup name for a flowcell. MinoTour will use the run names and flowcell ids it finds in reads if available.",
        dest="run_name",
    )

    parser.add_argument(
        "--unique",
        action="store_true",
        default=False,
        help="If you are flushing a flowcell, this option will force the flowcell to be named as a combination of flowcell ID and sample name. Thus data will be grouped appropriately.",
        dest="force_unique",
    )

    parser.add_argument(
        "-f",
        "--is_flowcell",
        action="store_true",
        help="If you add this flag, all runs added here will be considered as a single flow cell with the name set by the name flag.",
        dest="is_flowcell",
    )

    parser.add_argument(
        "-tc",
        "--treatment-control",
        type=int,
        required=False,
        default=None,
        help="Optionally split reads based in treatment and control groups based on the channel number. The integer value informed is used to mover ish read to the control group.",
        dest="treatment_control",
    )

    parser.add_argument(
        "-j",
        "--job",
        type=str,
        default=None,
        help="An optional minotour job to run on your server. Please enter the ID shown on the side when running --list.",
        dest="job",
    )

    parser.add_argument(
        "-r",
        "--reference",
        type=str,
        default=None,
        help="An optional minotour reference to map against. Please enter the ID shown on the side when running --list.",
        dest="reference",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        required=False,
        help="List available tasks, target sets and references at this server.",
        dest="list",
    )

    parser.add_argument(
        "-ts",
        "--targets",
        type=str,
        default=None,
        help="Set the target set for the metagenomics",
        dest="targets",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display debugging information.",
        default=False,
        dest="verbose",
    )

    parser.add_argument(
        "-ll",
        "--loglevel",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
        dest="loglevel",
    )

    parser.add_argument(
        "-g",
        "--gui",
        action="store_true",
        required=False,
        default=False,
        help="Configure the code for GUI use - not yet implemented.",
        dest="GUI",
    )
    parser.add_argument(
        "-V", "--version", action="version", version="%(prog)s (" + __version__ + ")",
    )

    parser.add_argument(
        "-T",
        "--toml",
        default=None,
        required=False,
        help="Path to the configuration file for an experiment",
        dest="toml",
    )
    parser.add_argument(
        "-U",
        "--unblocks",
        default=None,
        required=False,
        help="Path to an unblocked read_ids text file.",
        dest="unblocks",
    )
    return parser


def configure_logging(log_level):
    """
    Configure the logging to be used by this script.
    Parameters
    ----------
    log_level: str
        Logging level to print out at. One of INFO, DEBUG, ERROR, WARNING
    Returns
    -------
    log: logging.Logger
        A configured logger.
    """
    logging.basicConfig(
        format="%(asctime)s %(module)s:%(levelname)s:%(thread)d:%(message)s",
        filename="minFQ.log",
        # level=os.environ.get('LOGLEVEL', 'INFO')
        level=log_level,
    )
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(log_level)
    # set a format which is simpler for console use
    formatter = logging.Formatter("%(levelname)-8s %(message)s")
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger("").addHandler(console)
    log = logging.getLogger(__name__)
    return log
