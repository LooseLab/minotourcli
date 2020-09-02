import os
import sys
import fnmatch, shutil, platform
import fileinput
import logging
import logging.handlers
import time
from pathlib import Path
from .version import __version__


PATCH_INIT = """

import platform
def _minknow_path(operating_system=platform.system()):
    return {
        "Darwin": os.path.join(os.sep, "Applications", "MinKNOW.app", "Contents", "Resources"),
        "Linux": os.path.join(os.sep, "opt", "ont", "MinKNOW"),
        "Windows": os.path.join(os.sep, "C:\\\Program Files", "OxfordNanopore", "MinKNOW"),
    }.get(operating_system, None)
"""

"""We are setting up the code to copy and import the rpc service from minKNOW and make
it work on our own code. This prevents us from having to distribute ONT code ourselves."""

root_directory = os.path.dirname(os.path.realpath(__file__))

"""def copyfiles(srcdir, dstdir, filepattern):
    def failed(exc):
        raise exc
    dstdir = os.path.join(root_directory,dstdir)
    for dirpath, dirs, files in os.walk(srcdir, topdown=True, onerror=failed):
        for file in fnmatch.filter(files, filepattern):
            shutil.copy2(os.path.join(dirpath, file), dstdir)
            editfile(os.path.join(dstdir,file),'minknow.rpc','minFQ.rpc')
        break # no recursion
        """


def copyfiles(srcdir, dstdir, filepattern, module):
    def failed(exc):
        raise exc

    dstdir = os.path.join(root_directory, dstdir)
    for dirpath, dirs, files in os.walk(srcdir, topdown=True, onerror=failed):
        for file in fnmatch.filter(files, filepattern):
            shutil.copy2(os.path.join(dirpath, file), dstdir)
            editfile(
                os.path.join(dstdir, file),
                "minknow.{}".format(module),
                "minFQ.{}".format(module),
            )
            editfile(
                os.path.join(dstdir, file),
                "minknow.paths.minknow_base_dir()",
                "_minknow_path()",
            )
            editfile(os.path.join(dstdir, file), "import minknow.paths", "")
            if file == "__init__.py":
                with open(os.path.join(dstdir, file), "a") as out:
                    out.write(PATCH_INIT)
        break  # no recursion


def editfile(filename, text_to_search, replacement_text):
    with fileinput.FileInput(filename, inplace=True) as file:
        for line in file:
            print(line.replace(text_to_search, replacement_text), end="")


dstRPC = "rpc"

OPER = platform.system()

### We're going to force the replacement of the RPC each time minFQ is running.

if os.path.exists(os.path.join(root_directory, "rpc")):
    print("Removing previous RPC.")
    shutil.rmtree(os.path.join(root_directory, "rpc"))


if OPER == "Windows":
    RPCPATH = os.path.join(
        "ont-python", "Lib", "site-packages", "minknow", "rpc"
    )
else:
    RPCPATH = os.path.join(
        "ont-python", "lib", "python2.7", "site-packages", "minknow", "rpc"
    )


if not os.path.exists(os.path.join(root_directory, "rpc")):
    os.makedirs(os.path.join(root_directory, "rpc"))
if os.path.isfile(os.path.join(root_directory, "rpc", "__init__.py")):
    RPC_SUPPORT = True
    from minknowconnection import MinknowConnectRPC

    print("RPC Available")
    pass
else:
    print("No RPC")
    if OPER == "Darwin":
        minknowbase = os.path.join(
            os.sep, "Applications", "MinKNOW.app", "Contents", "Resources"
        )
    elif OPER == "Linux":
        if Path("/opt/ont/minknow").exists():
            minknowbase = os.path.join(os.sep, "opt", "ont", "minknow")
        else:
            minknowbase = os.path.join(os.sep, "opt", "ont", "MinKNOW")
    elif OPER == "Windows":
        minknowbase = os.path.join(
            os.sep, "Program Files", "OxfordNanopore", "MinKNOW"
        )
    else:
        print("Not configured for {} yet. Sorry.".format(OPER))
        sys.exit()
    sourceRPC = os.path.join(minknowbase, RPCPATH)

    if os.path.exists(sourceRPC):

        copyfiles(sourceRPC, dstRPC, "*.py", "rpc")
        RPC_SUPPORT = True
        from minknowconnection import MinknowConnectRPC

        print("RPC Configured")

    else:

        RPC_SUPPORT = False
        print(
            "Can not find MinKnow on this computer. You can use this client to process Fastq files, but not to monitor the sequencing process."
        )

sys.path.insert(0, os.path.join(root_directory, "rpc"))

from fastqutils import FastqHandler
from minknowcontrolutils import HelpTheMinion
import configargparse
from watchdog.observers.polling import PollingObserver as Observer

from minotourapi import MinotourAPI

CLIENT_VERSION = "1.0"


def up(lines=1):
    clearline = "\033[2K"  # clear a line
    upline = "\033[1A"  # Move cursor up a line
    for _ in range(lines):
        sys.stdout.write(upline)
        sys.stdout.write(clearline)


def main():

    global OPER

    OPER = platform.system()

    if OPER is "Windows":  # MS

        OPER = "windows"

    else:

        OPER = "linux"

    if OPER is "linux":

        config_file = os.path.join(
            os.path.sep,
            os.path.dirname(os.path.realpath("__file__")),
            "minfq_posix.config",
        )
    if OPER is "windows":

        config_file = os.path.join(
            os.path.sep, sys.prefix, "minfq_windows.config"
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
        # required=True,
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
        "-V",
        "--version",
        action="version",
        version="%(prog)s (" + __version__ + ")",
    )

    parser.add_argument(
        "-T",
        "--toml",
        default=None,
        required=False,
        help="Path to the configuration file for an experiment",
        dest="toml"
    )
    parser.add_argument(
        "-U",
        "--unblocks",
        default=None,
        required=False,
        help="Path to an unblocked read_ids text file.",
        dest="unblocks"
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s %(module)s:%(levelname)s:%(thread)d:%(message)s",
        filename="minFQ.log",
        # level=os.environ.get('LOGLEVEL', 'INFO')
        level=args.loglevel,
    )

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    # formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
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

    args.WATCHLIST=[]
    WATCHDICT = dict()

    ### Horrible tracking of run stats.
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

    ### Check if we are connecting to https or http

    ## Moving this to the minotourapi class.
    # if args.host_name.startswith("https://"):
    #    args.full_host = "{}:{}/".format(args.host_name, str(args.port_number))
    # else:
    #    args.full_host = "https://{}:{}/".format(args.host_name, str(args.port_number))

    # if not validators.url(args.full_host):
    #    print("Please check your url.")
    #    print("You entered:")
    #    print("{}".format(args.host_name))
    #    sys.exit()
    if args.toml is not None:
        if not os.path.exists(args.toml):
            print("Toml file not found in this location. "
                  "Please check that the specified file path is correct.")
            os._exit(2)

    if args.unblocks is not None:
        if not os.path.exists(args.unblocks):
            print("Unblocked read ids file not found in this location. "
                  "Please check that the specified file path is correct.")
            os._exit(2)

    if args.list:

        log.info("Checking available jobs.")

        minotourapi = MinotourAPI(args.host_name, args.port_number, header)

        jobs = minotourapi.get_job_options()

        references = minotourapi.get_references()["data"]

        targets = minotourapi.get_target_sets(args.api_key)

        print(
            "The following jobs are available on this minoTour installation:"
        )

        for job in jobs["data"]:
            if not job["name"].startswith("Delete"):
                print("\t{}:{}".format(job["id"], job["name"].lower().replace(" ", "_")))

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

        os._exit(0)

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
                log.info(
                    "You need to specify a reference for a Minimap2 task."
                )
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

        if args.job == jobs_dict.get(args.job, False) or args.job == "track_artic_coverage":
            log.info("Starting the Artic task.")

    if not args.noMinKNOW and args.ip is None:
        parser.error(
            "To monitor MinKNOW in real time you must specify the IP address of your local machine.\nUsually:\n-ip 127.0.0.1"
        )

    if not args.noFastQ:
        if args.run_name is None:
            parser.error(
                "When monitoring read data MinoTour requires a default name to assign the data to if it cannot determine flowcell and sample name. Please set this using the -n option."
            )
            os._exit(0)
        #if args.watchdir is None:
        #    parser.error(
        #        "When monitoring read data MinoTour needs to know where to look! Please specify a watch directory with the -w flag."
        #    )
        #    os._exit(0)

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
    print(clients)

    if CLIENT_VERSION not in clients:
        print(CLIENT_VERSION)
        log.error(
            "Server does not support this client. Please change the client to a previous version or upgrade server."
        )

        shall_exit = True

    if not shall_exit:

        rundict = dict()

        if not args.noFastQ:
            log.info("Setting up FastQ monitoring.")

            # This block handles the fastq
            # Add our watchdir to our WATCHLIST
            args.WATCHLIST.append(args.watchdir)



        if not args.noMinKNOW:

            if RPC_SUPPORT:

                # this block is going to handle the running of minControl.
                # log.info("Configuring MinKNOW Monitoring.")
                minwsip = "ws://" + args.ip + ":9500/"

                MinKNOWConnectionRPC = MinknowConnectRPC(minwsip, args, header)
                log.info("MinKNOW RPC Monitoring Working.")

            else:

                print(
                    "There is no support for MinKnow monitoring on this computer."
                )

        sys.stdout.write("To stop minFQ use CTRL-C.\n")

        event_handler = FastqHandler(args, header, rundict)

        observer = Observer()
        observer.start()

        try:


                #observer.start()

            while 1:
                #### This code is constantly running - so this might be where we can change the minFQ watchfolders?
                linecounter = 0
                if not args.noFastQ:

                    if len(args.WATCHLIST) > 0:
                        for folder in args.WATCHLIST:
                            if folder:
                                if folder not in WATCHDICT.keys():
                                    # We have a new folder that hasn't been added.
                                    # We need to add this to our list to schedule and catalogue the files.
                                    args.update = True
                                    WATCHDICT[folder] = dict()
                                    event_handler.addfolder(folder)
                                    log.info("FastQ Monitoring added for {}".format(folder))
                        if args.update:
                            observer.unschedule_all()
                            for folder in args.WATCHLIST:
                                if folder:
                                    if os.path.exists(folder):
                                        observer.schedule(
                                            event_handler, path=folder, recursive=True
                                        )
                            args.update=False



                    sys.stdout.write("{}\n".format(args.fastqmessage))
                    sys.stdout.write("FastQ Upload Status:\n")
                    sys.stdout.write(
                        "Files queued/processed/skipped/time/elapsed:{}/{}/{}/{}/{}\n".format(
                            args.files_seen
                            - args.files_processed
                            - args.files_skipped,
                            args.files_processed,
                            args.files_skipped,
                            args.read_up_time,
                            args.elapsed,
                        )
                    )
                    sys.stdout.write(
                        "New reads seen/uploaded/skipped:{}/{}/{}\n".format(
                            args.reads_seen
                            - args.reads_uploaded
                            - args.reads_skipped,
                            args.reads_uploaded,
                            args.reads_skipped,
                        )
                    )

                    linecounter += 5

                if not args.noMinKNOW:

                    sys.stdout.write("MinKNOW Monitoring Status:\n")
                    sys.stdout.write(
                        "Connected minIONs: {}\n".format(
                            MinKNOWConnectionRPC.minIONnumber()
                        )
                    )

                    linecounter += 2

                sys.stdout.flush()
                print (args.WATCHLIST)

                time.sleep(5)
                if not args.verbose:
                    up(linecounter)

        except KeyboardInterrupt:

            log.info("Exiting - Will take a few seconds to clean up!")

            if not args.noMinKNOW:
                MinKNOWConnectionRPC.disconnect_nicely()

            if not args.noFastQ:
                observer.stop()
                observer.join()



            os._exit(0)


if __name__ == "__main__":

    main()