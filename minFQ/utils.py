import logging
import os
import sys
import time
import requests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib.parse import urlparse

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
    event_handler: minFQ.fastq_handler.FastqHandler
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
            event_handler.add_folder(folder)
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
    response, jobs = minotour_api.get("/reads/tasktypes/", parameters={"cli": True})
    if args.job not in jobs:
        parser.error("Can't find the job type chosen. Please double check that it is the same ID shown by --list.")

    if args.job == "minimap2" or args.job == 4:
        if args.reference == None:
            log.warning("You need to specify a reference for a Minimap2 task.")
            sys.exit(0)
        response, references = minotour_api.get("/reference/", {"cli": True})
        if args.reference not in references["data"]:
            log.error("Reference not found. Please recheck.")
            sys.exit(0)
    if args.job == "metagenomics" or args.job == 10:
        if args.targets:
            params = {"api_key": args.api_key, "cli": True}
            response, targets = minotour_api.get("/metagenomics/targetsets", parameters=params)
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
    response, jobs = minotour_api.get("/reads/tasktypes/", parameters={"cli": True})
    response, references = minotour_api.get("/reference/")
    params = {"api_key": args.api_key, "cli": True}
    response, targets = minotour_api.get("/metagenomics/targetsets", parameters=params)
    log.info("The following jobs are available on this minoTour installation:")
    for job_id, job_info in jobs["data"].items():
        if not job_info["name"].startswith("Delete"):
            log.info(
                "\t{}:{}".format(job_id, job_info["name"].lower().replace(" ", "_"))
            )
    log.info(
        "If you wish to run an alignment, the following references are available:"
    )
    for reference in references["data"]:
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


def update_minion_stats(self):
    # TODO REWRITE
    """
    Update the statistics about a run that we have recorded from minKnow.
    Sent to Minotour and stored in minIon run stats table.
    Contains information about the run, not just minKNOW/minION.
    Returns
    -------
    None
    """

    asictemp = self.temperature_data.minion.asic_temperature.value
    heatsinktemp = self.temperature_data.minion.heatsink_temperature.value
    biasvoltage = int(self.bias_voltage)
    voltage_val = int(self.bias_voltage)  # todo this likely is wrong
    voltage_value = biasvoltage  # todo check this = probably wrong
    yield_val = self.acquisition_data.yield_summary.selected_events
    read_count = self.acquisition_data.yield_summary.read_count
    channel_panda = pd.DataFrame.from_dict(
        self.channel_states, orient="index", dtype=None
    )
    channel_dict = {}
    channel_dict["strand"] = 0
    channel_dict["adapter"] = 0
    channel_dict["good_single"] = 0
    channel_dict["pore"] = 0
    try:
        channelpandastates = channel_panda.groupby([0,]).size()
        # print (channelpandastates)
        log.debug(channelpandastates)
        for state, value in channelpandastates.iteritems():
            log.debug("{} {}".format(state, value))
            #    print (state,value)
            channel_dict[state] = value
        # print ("\n\n\n\n\n\n")
        instrand = 0  # channeldict["strand"]+channeldict["adapter"]
        openpore = 0  # channeldict["good_single"]+channeldict["pore"]
        meanratio = 0  # todo work out if we can still do this
    except:
        #("error")
        meanratio = 0
        instrand = 0
        openpore = 0
        pass

    # Capturing the histogram data from MinKNOW
    # print (self.runinformation)

    payload = {
        "minion": str(self.minotour_minion["url"]),
        "run": self.minotour_run_url,
        "sample_time": str(datetime.datetime.now()),
        "event_yield": yield_val,
        "asic_temp": asictemp,
        "heat_sink_temp": heatsinktemp,
        "voltage_value": voltage_value,
        "mean_ratio": meanratio,
        "open_pore": openpore,
        "in_strand": instrand,
        "minKNOW_histogram_values": str(self.histogram_data.histogram_data[0].bucket_values),
        "minKNOW_histogram_bin_width": self.histogram_data.bucket_ranges[0].end,
        #ToDo Determine if this actually exsits!
        #"actual_max_val": self.histogram_data.histogram_data.actual_max_val,
        "minKNOW_read_count": read_count,
        "n50_data": self.histogram_data.histogram_data[0].n50,
        "estimated_selected_bases": self.acquisition_data.yield_summary.estimated_selected_bases,

    }

    if hasattr(self.acquisition_data.yield_summary,"basecalled_bases"):
        payload["basecalled_bases"] = self.acquisition_data.yield_summary.basecalled_bases
        payload["basecalled_fail_read_count"] = self.acquisition_data.yield_summary.basecalled_fail_read_count
        payload["basecalled_pass_read_count"] = self.acquisition_data.yield_summary.basecalled_pass_read_count

    for channel in channel_dict:
        payload[str(channel)] = channel_dict[channel]
    log.debug("This our new payload: {}".format(payload))

    result = self.minotour_api.create_minion_statistic(
        payload, self.run_primary_key
    )
    log.debug("This is our result: {}".format(result))


def update_minion_info(self):
    # TODO REWRITE

    """
    Update the minion status information. Send it to minotour.
    Data may be None, if it is not present in the MinKnow status.
    Logic is supposed to be just information about MinKNOW/the minION device.
    Returns
    -------
    None

    """
    #if len(self.acquisition_data) < 1:

    ### changing as acquisition data will be None if nothing in it
    log.debug(self.acquisition_data)
    if self.acquisition_data is not None:
        minknowstatus = AcquisitionState.Name(self.acquisition_data.state)
        current_script = self.minknow_api_connection.protocol.get_run_info().protocol_id
    else:
        current_script = "Nothing Running"
        #ToDO: move minknowstatus to MinKNOWStatus object and work out how to handle a first connect with no active or previous run
        minknowstatus = "No Run"

    if not self.disk_space_info:
        self.disk_space_info = self.minknow_api_connection.instance.get_disk_space_info()
        log.debug(self.disk_space_info)

    payload = {
        "minion": str(self.minotour_minion["url"]),
        "minKNOW_status": minknowstatus,
        "minKNOW_current_script": current_script,
        "minKNOW_exp_script_purpose": self.minknow_api_connection.protocol.get_protocol_purpose().purpose,
        "minKNOW_flow_cell_id": self.get_flowcell_id(),
        "minKNOW_real_sample_rate": self.minknow_api_connection.device.get_sample_rate().sample_rate,
        "minKNOW_asic_id": self.flowcell_data.asic_id_str,
        "minKNOW_total_drive_space": self.disk_space_info.filesystem_disk_space_info[
            0
        ].bytes_capacity,
        "minKNOW_disk_space_till_shutdown": self.disk_space_info.filesystem_disk_space_info[
            0
        ].bytes_when_alert_issued,
        "minKNOW_disk_available": self.disk_space_info.filesystem_disk_space_info[
            0
        ].bytes_available,
        "minKNOW_warnings": self.disk_space_info.filesystem_disk_space_info[
            0
        ].recommend_stop,
        "minknow_version": self.minknow_version,
    }
    try:
        payload[
            "minKNOW_script_run_id"
        ] = self.minknow_api_connection.protocol.get_current_protocol_run().acquisition_run_ids[
            0
        ]
    except:
        #print ("!!!!!! big error")
        pass
    if hasattr(self, "sampleid"):
        log.debug(self.sampleid)
        log.debug(type(self.sampleid))
        log.debug(dir(self.sampleid))
        payload["minKNOW_sample_name"] = str(self.sampleid.sample_id.value)
        payload["minKNOW_run_name"] = str(self.sampleid.protocol_group_id.value)

    if hasattr(self, "run_information"):
        if hasattr(self.run_information, "run_id"):
            payload["minKNOW_hash_run_id"] = str(self.run_information.run_id)

    if hasattr(self, "runinfo_api"):
        payload["wells_per_channel"] = self.runinfo_api.flow_cell.wells_per_channel

    if self.minion_status:  # i.e the minION status already exists

        self.minion_status = self.minotour_api.update_minion_info_mt(
            payload, self.minotour_minion
        )

    else:

        self.minion_status = self.minotour_api.create_minion_info_mt(
            payload, self.minotour_minion
    )


def update_minion_run_info(self):
    # TODO REWRITE

    """
    Update the minion_run_info table in Minotour, sent once at the start of the run.
    Returns
    -------

    """
    payload = {
        "minion": str(self.minotour_minion["url"]),
        "minKNOW_current_script": str(
            self.minknow_api_connection.protocol.get_run_info().protocol_id
        ),
        "minKNOW_sample_name": str(self.sampleid.sample_id.value),
        "minKNOW_exp_script_purpose": str(
            self.minknow_api_connection.protocol.get_protocol_purpose()
        ),
        "minKNOW_flow_cell_id": self.get_flowcell_id(),
        "minKNOW_run_name": str(self.sampleid.sample_id.value),
        "run": self.minotour_run_url,
        "minKNOW_version": str(
            self.minknow_api_connection.instance.get_version_info().minknow.full
        ),
        "minKNOW_hash_run_id": str(self.run_information.run_id),
        "minKNOW_script_run_id": str(
            self.minknow_api_connection.protocol.get_current_protocol_run().acquisition_run_ids[
                0
            ]
        ),
        "minKNOW_real_sample_rate": int(
            str(self.minknow_api_connection.device.get_sample_rate().sample_rate)
        ),
        "minKNOW_asic_id": self.flowcell_data.asic_id_str,
        "minKNOW_start_time": self.run_information.start_time.ToDatetime().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "minKNOW_colours_string":
            MessageToJson(
                self.minknow_api_connection.analysis_configuration.get_channel_states_desc(),
                preserving_proto_field_name=True,
                including_default_value_fields=True,
            ),
        "minKNOW_computer": str(self.computer_name),
        "target_temp": self.temperature_data.target_temperature,
        "flowcell_type": self.flowcell_data.user_specified_product_code,
    }

    context_info = self.minknow_api_connection.protocol.get_context_info().context_info
    for key in context_info:
        payload[key] = context_info[key]
    run_info = self.minknow_api_connection.protocol.get_run_info()
    if run_info.user_info.HasField("protocol_group_id"):
        payload["experiment_id"] = run_info.user_info.protocol_group_id.value
    else:
        payload["experiment_id"] = "Not Known"

    update_run_info = self.minotour_api.update_minion_run_info(
        payload, self.run_primary_key
    )
    log.debug(update_run_info)


def minknow_command(self):
    """
    This function will recieve commands for a specific minION and handle the interaction.
    :return:
    """
    pass


def run_start(self):
    """
    This function will fire when a run first begins.
    It will drive the creation of a run.
    :return:
    """
    self.minotour_api.update_minion_event(
        self.minotour_minion, self.computer_name, "sequencing"
    )

    log.debug("run start observed")
    log.debug("MINION:", self.minotour_minion)
    # We wait for 10 seconds to allow the run to start
    time.sleep(self.interval)
    try:
        self.run_information = self.minknow_api_connection.acquisition.get_current_acquisition_run()
        self.create_run(self.run_information.run_id)
        log.debug("run created!!!!!!!")
        #### Grab the folder and if we are allowed, add it to the watchlist?
        FolderPath = self.minknow_api_connection.protocol.get_current_protocol_run().output_path
        # print ("New Run Seen {}".format(FolderPath))
        if not self.args.no_fastq:
            if FolderPath not in self.upload_data.directory_watch_list:
                self.upload_data.directory_watch_list.append(str(os.path.normpath(FolderPath)))
        self.update_minion_run_info()
        log.debug("update minion run info complete")

    except Exception as err:
        log.error("Problem:", err)


def first_connect(self):
    """
    This function will run when we first connect to the MinION device.
    It will provide the information to minotour necessary to remotely control the minION device.
    :return:
    """
    log.debug("First connection observed")
    log.debug("All is well with connection. {}".format(self.minotour_minion))
    # TODO change to use the minknow status/state
    self.minotour_api.update_minion_event(self.minotour_minion, self.computer_name, "connected")
    #if self.status==AcquisitionState.ACQUISITION_RUNNING:

    if str(self.acquisition_status).startswith("ACQUISITION_RUNNING") or str(self.acquisition_status).startswith("ACQUISITION_STARTING"):
        self.device_active = True
        #self.run_start()

    def get_flowcell_id(self):
        # ToDo make this function work out if we need to create a flowcell id for this run.

        if len(self.flowcell_data.user_specified_flow_cell_id) > 0:
            log.debug("We have a self named flowcell")
            flowcell_id = self.flowcell_data.user_specified_flow_cell_id
        else:
            log.debug("the flowcell id is fixed")
            flowcell_id = self.flowcell_data.flow_cell_id

        return flowcell_id


def run_stop(self):
    """
    This function will clean up when a run finishes.
    :return:
    """
    ## ToDo We need to remove the run from the rundict when we stop a run to prevent massive memory problems.
    self.minotour_api.update_minion_event(self.minotour_minion, self.computer_name, "active")
    FolderPath = str(
        os.path.normpath(
            self.minknow_api_connection.protocol.get_current_protocol_run().output_path
        )
    )
    if not self.args.noFastQ:
        if FolderPath in self.args.WATCHLIST:
            time.sleep(self.long_interval)
            self.args.WATCHLIST.remove(FolderPath)
            self.args.update = True


def create_run(self, runid):
    """
    Fired to create a run in Minotour, and return a hyperlinked URL to the database entry, and the run primary key.
    Parameters
    ----------
    runid: str
        The string of the run ID hash as provided by minknow

    Returns
    -------
    None

    """
    log.debug(self.minotour_api)
    run = self.minotour_api.get_run_by_runid(runid)
    log.debug(run)
    if not run:
        log.debug(">>> no run {}".format(runid))
        #
        # get or create a flowcell
        #
        flowcell = self.minotour_api.get_flowcell_by_name(self.get_flowcell_id())[
            "data"
        ]
        log.debug(flowcell)
        if not flowcell:
            log.debug(">>> no flowcell")
            flowcell = self.minotour_api.create_flowcell(self.get_flowcell_id())
        is_barcoded = False  # TODO do we known this info at this moment? This can be determined from run info.
        has_fastq = True  # TODO do we known this info at this moment? This can be determined from run info

        create_run = self.minotour_api.create_run(
            self.sampleid.sample_id.value,
            runid,
            is_barcoded,
            has_fastq,
            flowcell,
            self.minotour_minion,
            self.run_information.start_time.ToDatetime().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )
        log.debug(">>> after self.minotourapi.create_run")
        if not create_run:
            log.error("Run not created!")
        else:
            log.info(create_run)
            self.minotour_run_url = create_run["url"]
            self.run_primary_key = create_run["id"]  # I
    else:
        self.minotour_run_url = run["url"]
        self.run_primary_key = run["id"]
    log.debug("***** self.run_primary_key: {}".format(self.run_primary_key))
    log.debug("**** run stats updated")


def send_message(self, severitylevel, message):
    self.minknow_api_connection.log.send_user_message(
        severity=severitylevel, user_message=message
    )


def get_messages(self):
    while True:
        if not self.minotour_run_url:
            time.sleep(1)
            continue
        messages = self.minknow_api_connection.log.get_user_messages(
            include_old_messages=True
        )
        for message in messages:

            payload = {
                "minion": self.minotour_minion["url"],
                "message": message.user_message,
                "run": "",
                "identifier": message.identifier,
                "severity": message.severity,
                "timestamp": message.time.ToDatetime().strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )[:-3],
            }

            if self.minotour_run_url:
                payload["run"] = self.minotour_run_url

            messagein = self.minotour_api.create_message(payload, self.minotour_minion)


# https://www.peterbe.com/plog/best-practice-with-retries-with-requests
def requests_retry_session(
    retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None,
):
    """
    Retry a connection to requests todo currently unused
    Parameters
    ----------
    retries
    backoff_factor
    status_forcelist
    session

    Returns
    -------

    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session