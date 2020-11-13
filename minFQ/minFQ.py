import os
import sys
import fnmatch, shutil, platform
import fileinput
import logging
import logging.handlers
import time
from pathlib import Path

from minFQ.minknow_connection import MinionManager
from .version import __version__
from minFQ.fastqutils import FastqHandler
import configargparse
from watchdog.observers.polling import PollingObserver as Observer
from minFQ.minotourapi import MinotourAPI
#from minFQ.minknowconnection import MinknowConnectRPC


"""We are setting clear_lines the code to copy and import the rpc service from minKNOW and make
it work on our own code. This prevents us from having to distribute ONT code ourselves."""

root_directory = os.path.dirname(os.path.realpath(__file__))

CLIENT_VERSION = "1.0"


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
    clearline = "\033[2K"  # clear a line
    upline = "\033[1A"  # Move cursor clear_lines a line
    for _ in range(lines):
        sys.stdout.write(upline)
        sys.stdout.write(clearline)


def main():
    """
    Entry point for minFQ, parser CLI arguments
    Returns
    -------

    """

    if platform.system() == "Windows":  # MS
        config_file = os.path.join(os.path.sep, sys.prefix, "minfq_windows.config")
    else:
        config_file = os.path.join(
            os.path.sep, os.path.dirname(os.path.realpath("__file__")), "minfq.config",
        )

    parser = configargparse.ArgParser(
        description="minFQ: A program to analyse minION fastq files in real-time or post-run and monitor the activity of MinKNOW.",
        default_config_files=[config_file],
    )

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
        dest="noFastQ",
    )

    parser.add_argument(
        "-nm",
        "--no_minKNOW",
        action="store_true",
        help="Run minFQ without monitoring minKNOW for live activity.",
        default=False,
        dest="noMinKNOW",
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
        type=str,
        # required=True,
        default=None,
        help="An optional minotour job to run on your server. Please enter the ID shown on the side when running --list, or the name separated by _.",
        dest="job",
    )

    parser.add_argument(
        "-r",
        "--reference",
        type=str,
        # required=True,
        default=None,
        help="An optional minotour reference to map against.",
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
    args = parser.parse_args()
    args.loglevel = getattr(logging, args.loglevel)
    logging.basicConfig(
        format="%(asctime)s %(module)s:%(levelname)s:%(thread)d:%(message)s",
        filename="minFQ.log",
        # level=os.environ.get('LOGLEVEL', 'INFO')
        level=args.loglevel,
    )
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(args.loglevel)
    # set a format which is simpler for console use
    formatter = logging.Formatter("%(levelname)-8s %(message)s")
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger("").addHandler(console)
    log = logging.getLogger(__name__)
    log.info("Initialising minFQ.")
    header = {
        "Authorization": "Token {}".format(args.api_key),
        "Content-Type": "application/json",
    }
    ### List to hold folders we want to watch
    args.WATCHLIST = []
    WATCHDICT = {}

    ### Horrible tracking of run stats.
    # todO fix this horrendous abuse of naMespaces
    args.files_seen = 0
    args.files_processed = 0
    args.files_skipped = 0
    args.reads_seen = 0
    args.reads_corrupt = 0
    args.reads_skipped = 0
    args.reads_uploaded = 0
    args.fastqmessage = "No Fastq Seen"
    args.update = False
    args.read_up_time = time.time()
    args.elapsed = 0
    args.errored = False
    args.error_message = ""

    if args.toml is not None:
        if not os.path.exists(args.toml):
            sys.exit(
                "Toml file not found in this location. "
                "Please check that the specified file path is correct."
            )

    if args.unblocks is not None:
        if not os.path.exists(args.unblocks):
            sys.exit(
                "Unblocked read ids file not found in this location. "
                "Please check that the specified file path is correct."
            )

    if args.list:
        log.info("Checking available jobs.")
        minotourapi = MinotourAPI(args.host_name, args.port_number, header)
        jobs = minotourapi.get_job_options()
        references = minotourapi.get_references()["data"]
        targets = minotourapi.get_target_sets(args.api_key)

        print("The following jobs are available on this minoTour installation:")
        for job in jobs["data"]:
            if not job["name"].startswith("Delete"):
                print(
                    "\t{}:{}".format(job["id"], job["name"].lower().replace(" ", "_"))
                )
        print(
            "If you wish to run an alignment, the following references are available:"
        )
        for reference in references:
            if not reference["private"]:
                print("\t{}:{}".format(reference["id"], reference["name"]))
        print(
            "If you wish to add a target set to the metagenomics task, the following sets are available to you:"
        )
        for target in targets:
            print("\t:{}".format(target))
        sys.exit(0)

    # Below we perform checks if we are trying to set a job.
    if args.job is not None:
        args.job = int(args.job)
        # Instantiate  a connection to Minotour
        minotourapi = MinotourAPI(args.host_name, args.port_number, header)
        # Get availaible jobs
        jobs = minotourapi.get_job_options()
        args.job_id = -1
        jobs_dict = {}

        for job in jobs["data"]:
            log.info(job)
            jobs_dict[job["name"].lower().replace(" ", "_")] = int(job["id"])
            # Compare the names fetched from minoTour in with the name of the Task user specified
            if args.job == job["name"].replace(" ", "_") or args.job == int(job["id"]):
                args.job_id = int(job["id"])
        log.info(jobs_dict)
        if args.job_id == -1:
            log.info("Job {} not found. Please recheck.".format(args.job))
            os._exit(0)

        if args.job == "minimap2" or args.job == jobs_dict.get("minimap2", ""):
            if args.reference == None:
                log.info("You need to specify a reference for a Minimap2 task.")
                os._exit(0)

            references = minotourapi.get_references()["data"]

            args.reference_id = -1
            for reference in references:
                if int(args.reference) == int(reference["id"]):
                    args.reference_id = reference["id"]

            if args.reference_id == -1:
                log.info("Reference not found. Please recheck.")
                os._exit(0)

        if args.job == "metagenomics" or args.job == jobs_dict.get("metagenomics", ""):
            if args.targets:
                targets = minotourapi.get_target_sets(args.api_key)
                if args.targets not in targets:
                    log.info(
                        "Target set not found. Please check spelling and try again."
                    )
                    os._exit(0)

        if (
            args.job == jobs_dict.get(args.job, False)
            or args.job == "track_artic_coverage"
        ):
            log.info("Starting the Artic task.")

    if not args.noMinKNOW and args.ip is None:
        parser.error(
            "To monitor MinKNOW in real time you must specify the IP address of your local machine.\nUsually:\n-ip 127.0.0.1"
        )

    # Makes no sense to run if both no minKNOW and no FastQ is set:
    if args.noFastQ and args.noMinKNOW:
        print("You must monitor either FastQ or MinKNOW.")
        print("This program will now exit.")
        os._exit(0)

    args.read_count = 0
    minotourapi = MinotourAPI(args.host_name, args.port_number, header)
    version = minotourapi.get_server_version()
    log.info(version)
    shall_exit = False

    if not version:
        log.error(
            "Server does not support this client. Please change the client to a previous version or upgrade server."
        )
        shall_exit = True
    clients = version["clients"]

    if CLIENT_VERSION not in clients:
        print(CLIENT_VERSION)
        log.error(
            "Server does not support this client. Please change the client to a previous version or upgrade server."
        )
        shall_exit = True

    if not shall_exit:
        rundict = {}
        if not args.noFastQ:
            log.info("Setting clear_lines FastQ monitoring.")
            # This block handles the fastq
            # Add our watchdir to our WATCHLIST
            if args.watchdir is not None:
                args.WATCHLIST.append(args.watchdir)
        # if we are connecting to minKNOW
        if not args.noMinKNOW:
            # this block is going to handle the running of minknow monitoring by the client.
            minknow_connection = MinionManager(args=args, header=header)
            log.info("MinKNOW RPC Monitoring Working.")

        # GET away you horrible code
        sys.stdout.write("To stop minFQ use CTRL-C.\n")
        event_handler = FastqHandler(args, header, rundict)
        observer = Observer()
        observer.start()
        try:
            while 1:
                line_counter = 0
                if not args.noFastQ and args.WATCHLIST:
                    for folder in args.WATCHLIST:
                        if folder and folder not in WATCHDICT:
                            # We have a new folder that hasn't been added.
                            # We need to add this to our list to schedule and catalogue the files.
                            args.update = True
                            WATCHDICT[folder] = {}
                            event_handler.addfolder(folder)
                            log.info("FastQ Monitoring added for {}".format(folder))
                    if args.update:
                        observer.unschedule_all()
                        for folder in args.WATCHLIST:
                            if folder and os.path.exists(folder):
                                observer.schedule(
                                    event_handler, path=folder, recursive=True
                                )
                        args.update = False

                    sys.stdout.write("{}\n".format(args.fastqmessage))
                    sys.stdout.write("FastQ Upload Status:\n")
                    sys.stdout.write(
                        "Files queued/processed/skipped/time/per file:{}/{}/{}/{}/{}\n".format(
                            args.files_seen - args.files_processed - args.files_skipped,
                            args.files_processed,
                            args.files_skipped,
                            args.read_up_time,
                            args.elapsed,
                        )
                    )
                    sys.stdout.write(
                        "New reads seen/uploaded/skipped:{}/{}/{}\n".format(
                            args.reads_seen - args.reads_uploaded - args.reads_skipped,
                            args.reads_uploaded,
                            args.reads_skipped,
                        )
                    )
                    sys.stdout.write(", ".join(args.WATCHLIST) + "\n")

                    line_counter += 5

                if not args.noMinKNOW:
                    sys.stdout.write("MinKNOW Monitoring Status:\n")
                    sys.stdout.write(
                        "Connected minIONs: {}\n".format(
                            minknow_connection.count
                        )
                    )
                    line_counter += 2

                sys.stdout.flush()
                time.sleep(5)
                if not args.verbose:
                    clear_lines(line_counter)
                if args.errored:
                    log.info("Errored - Will take a few seconds to clean clear_lines!")
                    log.error(args.error_message)
                    if not args.noMinKNOW:
                        minknow_connection.stop_monitoring()
                    if not args.noFastQ:
                        observer.stop()
                        observer.join()
                    event_handler.stopt()
                    sys.exit(0)

        except KeyboardInterrupt:
            log.info("Exiting - Will take a few seconds to clean clear_lines!")
            if not args.noMinKNOW:
                minknow_connection.stop_monitoring()
            if not args.noFastQ:
                observer.stop()
                observer.join()
            event_handler.stopt()
            sys.exit(0)



if __name__ == "__main__":
    main()
