import logging
import os
import sys
import time
from collections import defaultdict

from minFQ.endpoints import EndPoint
from .version import __version__


class SequencingStatistics:
    """
    A class to store data about the sequencing, between different threads.
    """

    def __init__(self):
        self.screen_num_rows = 0
        self.screen_num_cols = 0
        self.files_seen = 0
        self.files_processed = 0
        self.files_skipped = 0
        self.reads_seen = 0
        self.reads_corrupt = 0
        self.reads_skipped = 0
        self.reads_uploaded = 0
        self.fastq_message = "No Fastq Seen"
        self.update = False
        self.read_up_time = time.time()
        self.read_count = 0
        self.directory_watch_list = []
        self.errored = False
        self.error_message = ""
        self.time_per_file = time.time()
        self.minfq_info = {}
        self.minfq_initialisation_time = time.time()
        self.fastq_info = defaultdict(lambda: defaultdict(int))
        self._connected_positions = {}
        self.minfq_y = 2
        self.minknow_y = 10
        self._fastq_y = 16
        self.minotour_url = ""
        self.minknow_sample_col_x = 67
        self.connected_positions_test = {
            "MS00000": {
                "device_id": "MS00000",
                "running": "yes",
                "sample_id": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "up_time": "01:00:36",
            },
            "MS00002": {
                "device_id": "MS00002",
                "running": "no",
                "sample_id": "",
                "up_time": "01:20:36",
            },
            "MS00003": {
                "device_id": "MS00003",
                "running": "yes",
                "sample_id": "Hi_there_friends",
                "up_time": "00:05:36",
            },
        }
        self.fastq_info_test = {
            "MS00000": {
                "run_id": "ae9d6455f89107767ed80917b59f032d3e2037c6",
                "skipped": 109,
                "uploaded": 10000000,
                "directory": "/fun/times/abound",
            },
            "MS00001": {
                "run_id": "ae9d6455f89107767ed80917b59f032d3e2037c6",
                "skipped": 109,
                "uploaded": 30000,
                "directory": "/fun/times/abound/2",
            },
            "MS00002": {
                "run_id": "ae9d6455f89107767ed80917b59f032d3e2037c6",
                "skipped": 19,
                "uploaded": 102000000,
                "directory": "/fun/times/abound/3",
            },
        }

    @property
    def fastq_y(self):
        """
        Return te number of ocnnected positions to calulcate where to write the fastq statistics
        Returns
        -------

        """
        return self._fastq_y + len(self._connected_positions)

    @property
    def connected_positions(self):
        if self._connected_positions:
            return {
                key: {
                    k: self.convert(time.time() - v) if isinstance(v, float) else v
                    for k, v in value.items()
                }
                for key, value in self._connected_positions.items()
            }
        else:
            return {}

    def update_minknow_cols_x(self, minknow=True):
        """
        Update the minknow cols x finding the widest value of each column. If more than 64 chars truncate it.
        Returns
        -------
        None or dict
            Returns dict of char width if minknow is false
        """
        a = self.connected_positions if minknow else self.fastq_info_test
        char_widths = {}
        for position_values in a.values():
            char_widths.update(
                {
                    key: len(str(inner_values))
                    for key, inner_values in position_values.items()
                    if len(str(inner_values)) > char_widths.get(key, 0)
                }
            )
        if minknow:
            if char_widths.get("sample_id", 0) > 16:
                self.minknow_sample_col_x = 67 + char_widths["sample_id"] - 8
            else:
                self.minknow_sample_col_x = 67
        else:
            return char_widths

    @property
    def minfq_uptime(self):
        """
        How long this minFQ instance has been up
        Returns
        -------
        str
        """
        return self.convert(time.time() - self.minfq_initialisation_time)

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

    @property
    def per_file(self):
        """
        Time to upload the current file
        Returns
        -------
        str
            Hours:Minutes:Seconds format generated from given second amount since this file upload began
        """
        return self.convert(time.time() - self.time_per_file)


def write_out_minfq_info(stdscr, sequencing_statistics):
    """

    Parameters
    ----------
    stdscr: _curses.window
        curses window
    sequencing_statistics: minFQ.utils.SequencingStatistics
        Class tracking stats about minFQ
    Returns
    -------

    """
    stdscr.addstr(1, 0, "                     ")
    stdscr.addstr(
        sequencing_statistics.minfq_y,
        0,
        "MinFQ Stats\n------------------------------------------\n"
        "MinFQ up time: {}\n"
        "Connected to minoTour at: {}\n"
        "Total FASTQ files Queued: {} \t\t Total Reads Queued: {}\n"
        "Total FASTQ files Uploaded: {} \t\t Total Reads Uploaded: {}\n"
        "Total FASTQ files Skipped: {} \t\t Total Reads Skipped: {}\n"
        "".format(
            sequencing_statistics.minfq_uptime,
            sequencing_statistics.minotour_url,
            sequencing_statistics.files_seen
            - sequencing_statistics.files_processed
            - sequencing_statistics.files_skipped,
            sequencing_statistics.reads_seen
            - sequencing_statistics.reads_uploaded
            - sequencing_statistics.reads_skipped,
            sequencing_statistics.files_processed,
            sequencing_statistics.reads_uploaded,
            sequencing_statistics.files_skipped,
            sequencing_statistics.reads_skipped,
        ),
    )


def write_out_minknow_info(stdscr, sequencing_statistics):
    """
    Write out information related to this minFQ instances connection to minKNOW
    Parameters
    ----------
    stdscr: _curses.window
        The window containing the terminal messages
    sequencing_statistics: minFQ.utils.SequencingStatistics
        class tracking the sequencing statistics of the run

    Returns
    -------
    None
    """
    stdscr.addstr(
        sequencing_statistics.minknow_y,
        0,
        "MinKNOW Stats\n---------------------------------------------\nPositions connected: {}\n".format(
            len(sequencing_statistics.connected_positions)
        ),
    )
    cols_y = sequencing_statistics.minknow_y + 4
    sequencing_statistics.update_minknow_cols_x()
    stdscr.clrtobot()
    stdscr.addstr(cols_y, 0, "Position")
    stdscr.addstr(cols_y, 16, "Running")
    stdscr.addstr(cols_y, 32, "Run Status")
    stdscr.addstr(cols_y, 57, "Sample")
    stdscr.addstr(
        cols_y, sequencing_statistics.minknow_sample_col_x, "Connection up Time"
    )
    for index, value in enumerate(sequencing_statistics.connected_positions.values()):
        stdscr.addstr(cols_y + index + 1, 0, value["device_id"])
        stdscr.addstr(cols_y + index + 1, 16, value["running"])
        stdscr.addstr(cols_y + index + 1, 32, value.get("acquisition_status", ""))
        stdscr.clrtoeol()
        stdscr.addstr(cols_y + index + 1, 57, value["sample_id"])
        stdscr.addstr(
            cols_y + index + 1,
            sequencing_statistics.minknow_sample_col_x,
            str(value["up_time"]),
        )

    # "Position \t\t Running \t\t Sample \t\t Connection uptime")


def write_out_fastq_info(stdscr, sequencing_statistics):
    """
    write out base-called data upload metrics
    Parameters
    ----------
    stdscr: _curses.window
        The window containing the terminal messages
    sequencing_statistics: minFQ.utils.SequencingStatistics
        class tracking the sequencing statistics of the run

    Returns
    -------
    None

    """
    stdscr.addstr(
        sequencing_statistics.fastq_y,
        0,
        "Base-called data upload stats\n------------------------------\nDirectories watched: {}\n".format(
            len(sequencing_statistics.directory_watch_list)
        ),
    )
    cols_y = sequencing_statistics.fastq_y + 4
    # char_widths = sequencing_statistics.update_minknow_cols_x(False)
    # sample_extra_width = char_widths.get("sample", 0)
    if sequencing_statistics.directory_watch_list:
        stdscr.addstr(cols_y, 0, "Run id")
        stdscr.addstr(cols_y, 44, "Queued")
        stdscr.addstr(cols_y, 59, "Uploaded")
        stdscr.addstr(cols_y, 74, "Skipped")
        stdscr.addstr(cols_y, 89, "Directory")
        stdscr.addstr(cols_y + 1, 44, "Files/Reads")
        stdscr.addstr(cols_y + 1, 59, "Files/Reads")
        stdscr.addstr(cols_y + 1, 74, "Files/Reads")
    else:
        stdscr.addstr(cols_y, 0, "Run id")
        stdscr.addstr(cols_y, 15, "Queued")
        stdscr.addstr(cols_y, 30, "Uploaded")
        stdscr.addstr(cols_y, 45, "Skipped")
        stdscr.addstr(cols_y, 60, "Directory")
        stdscr.addstr(cols_y + 1, 15, "Files/Reads")
        stdscr.addstr(cols_y + 1, 30, "Files/Reads")
        stdscr.addstr(cols_y + 1, 45, "Files/Reads")

    for index, value in enumerate(sequencing_statistics.fastq_info.values()):
        stdscr.addstr(cols_y + index + 2, 0, str(value.get("run_id", "")))
        files_queued = (
            value.get("files_seen", 0)
            - value.get("files_processed", 0)
            - value.get("files_skipped", 0)
        )
        reads_queued = (
            value.get("reads_seen", 0)
            - value.get("reads_uploaded", 0)
            - value.get("reads_skipped", 0)
        )
        stdscr.addstr(
            cols_y + index + 2, 44, "{}/{}".format(str(files_queued), str(reads_queued))
        )
        stdscr.addstr(
            cols_y + index + 2,
            59,
            "{}/{}".format(
                str(value.get("files_processed", 0)), str(value.get("reads_uploaded", 0))
            ),
        )
        stdscr.addstr(cols_y + index + 2, 74, "{}/{}".format(
            str(value.get("files_skipped", 0)), str(value.get("reads_skipped", 0)))
        )
        stdscr.addstr(cols_y + index + 2, 89, str(value.get("directory", 0)))


def clear_lines(lines=1):
    """
    Some weird print function, clears lines to print our new code
    Parameters
    ----------
    lines: int
        NUmber of line to go clear_lines and clear

    Returns
    -------
    None
    """
    clear_line = "\033[2K"  # clear a line
    up_line = "\033[1A"  # Move cursor clear_lines a line
    for _ in range(lines):
        sys.stdout.write(up_line)
        sys.stdout.write(clear_line)


def add_arguments_to_parser(parser):
    """
    Add command line arguments to the parser.
    Parameters
    ----------
    parser: configargparse.ArgumentParser
        The argument parser instance
    Returns
    -------
    parser: configargparse.ArgumentParser
        The parser with the added arguments
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
        dest="watch_dir",
    )

    parser.add_argument(
        "-i",
        "--ignore_existing",
        action="store_true",
        required=False,
        default=False,
        help="The client will ignore previously existing fastq files and will only monitor newly created files..",
        dest="ignore_existing",
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
        "--no_minKNOW",
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
        default="127.0.0.1",
        help="The IP address of the minKNOW machine - Typically 127.0.0.1.",
    )

    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default=None,
        help="This provides a backup name for a flowcell. MinoTour will use the run names and flowcell ids it finds in reads or from minKNOW if available.",
        dest="run_name_manual",
    )

    parser.add_argument(
        "--unique",
        action="store_true",
        default=True,
        help="If you are flushing a flowcell, this option will force the flowcell to be named as a combination of flowcell ID and sample name. Thus data will be grouped appropriately. Default true.",
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
        type=int,
        # required=True,
        default=None,
        help="An optional minotour job to run on your server. Please enter the ID shown on the side when running --list.",
        dest="job",
    )

    parser.add_argument(
        "-r",
        "--reference",
        type=int,
        # required=True,
        default=None,
        help="An optional minotour reference to map against. please enter the numerical id shown when running --list",
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
        type=int,
        default=None,
        help="Set the target set for the metagenomics, if desired. Please enter the numerical id shown when running --list",
        dest="targets",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Don't clear the screen. Helps when debugging.",
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
        help="Path to the channels configuration file for a read until experiment.",
        dest="toml",
    )
    parser.add_argument(
        "-U",
        "--unblocks",
        default=None,
        required=False,
        help="Absolute path to an unblocked read_ids text file. Not necessary, should be picked up automatically.",
        dest="unblocks",
    )
    return parser


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
        "Files queued/Processed/Skipped/Up time/This file:{}/{}/{}/{}/{}\n".format(
            upload_stats.files_seen
            - upload_stats.files_processed
            - upload_stats.files_skipped,
            upload_stats.files_processed,
            upload_stats.files_skipped,
            upload_stats.elapsed,
            upload_stats.per_file,
        )
    )
    sys.stdout.write(
        "New reads seen/Uploaded/Skipped:{}/{}/{}\n".format(
            upload_stats.reads_seen
            - upload_stats.reads_uploaded
            - upload_stats.reads_skipped,
            upload_stats.reads_uploaded,
            upload_stats.reads_skipped,
        )
    )
    sys.stdout.write(
        "Monitoring the following directories: {}\n".format(
            upload_stats.directory_watch_list
        )
    )
    return line_counter + 5


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
        filemode="w",
        # level=os.environ.get('LOGLEVEL', 'INFO')
        level=log_level,
    )
    # define a Handler which writes INFO messages or higher to the sys.stderr
    log = logging.getLogger("minFQ")
    return log


def validate_args(args):
    """
    Check the args before setting up all connections. Error out if any mistakes are found.
    Parameters
    ----------
    args: argparse.Namespace
        Namespace for chosen arguments after parsing
    Returns
    -------
    None
    """
    error_string = None
    if args.watch_dir:
        if not os.path.exists(args.watch_dir):
            error_string = "The watch directory specified {} does not exists. Please check specified path.".format(
                args.watch_dir
            )

        if args.no_fastq:
            error_string = (
                "If not monitoring FASTQ please do no provide a watch directory."
            )

    if args.toml is not None:
        if not os.path.exists(args.toml):
            error_string = "Toml file not found in this location. Please check that the specified file path is correct."

    if args.unblocks is not None:
        if not os.path.exists(args.unblocks):
            error_string = (
                "Unblocked read ids file not found in this location."
                " Please check that the specified file path is correct."
            )
    if args.no_fastq and args.no_minknow:
        error_string = (
            "You must monitor either FastQ or MinKNOW.\n This program will now exit."
        )
    if not args.no_minknow and args.ip is None:
        error_string = (
            "To monitor MinKNOW in real time you must specify the IP address"
            " of your local machine.\nUsually: -ip 127.0.0.1"
        )

    if error_string:
        raise Exception(error_string)


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
    str
    """
    version = minotour_api.get_json(EndPoint.VERSION)
    clients = version["clients"]
    if not any([__version__.startswith(client) for client in clients]):
        log.error(
            "Server does not support this client. Please change the client to a previous version or upgrade server."
        )
        raise Exception(
            "Server does not support this client. "
            "Please change the client to a previous version or upgrade server."
        )
    else:
        return "minFQ version: {} is compatible with minoTour server specified.\n".format(__version__)


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
    jobs = minotour_api.get_json(EndPoint.TASK_TYPES, params={"cli": True})["data"]
    references = minotour_api.get_json(EndPoint.REFERENCES)["data"]
    params = {"api_key": args.api_key, "cli": True}
    targets = minotour_api.get_json(EndPoint.TARGET_SETS, params=params)
    log.info("The following jobs are available on this minoTour installation:")
    for job_info in jobs:
        if not job_info["name"].startswith("Delete"):
            log.info(
                "\t{}:{}".format(
                    job_info["id"], job_info["name"].lower().replace(" ", "_")
                )
            )
    log.info("If you wish to run an alignment, the following references are available:")
    for reference in references:
        log.info("\t{}:{}".format(reference["id"], reference["name"]))
    log.info(
        "If you wish to add a target set to the metagenomics task, the following sets are available to you:"
    )
    index = 1
    for target in targets:
        log.info("\t{}:{}".format(index, target))
        index += 1
    sys.exit(0)


def check_job_from_client(args, log, minotour_api, parser):
    """
    Check that we can start the specified job on the server.
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
    jobs = minotour_api.get_json(EndPoint.TASK_TYPES, params={"cli": True})["data"]
    jobs = [job["id"] for job in jobs]
    if args.job not in jobs:
        parser.error(
            "Can't find the job type chosen. Please double check that it is the same ID shown by --list."
        )

    if args.job == "minimap2" or args.job == 4:
        if args.reference == None:
            log.error("You need to specify a reference for a Minimap2 task.")
            sys.exit(0)
        references = minotour_api.get_json(EndPoint.REFERENCES, params={"cli": True})
        if args.reference not in [reference["id"] for reference in references["data"]]:
            log.error("Reference not found. Please recheck.")
            sys.exit(0)
    if args.job == "metagenomics" or args.job == 10:
        if args.targets:
            if not isinstance(args.targets, int):
                sys.exit("Please use the numerical identifier for the target set.")
            params = {"api_key": args.api_key, "cli": True}
            targets = minotour_api.get_json(EndPoint.TARGET_SETS, params=params)
            if args.targets > len(targets):
                log.error("Target set not found. Please check spelling and try again.")
                sys.exit(0)
