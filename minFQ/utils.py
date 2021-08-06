import json
import logging
import operator
import os
import sys
import time
from collections import defaultdict, OrderedDict
import curses
from pprint import pformat

from minFQ.endpoints import EndPoint
from .version import __version__

log = logging.getLogger(__name__)


class CursesHandler(logging.Handler):
    """ todo spruce up message
    Logging handler to emit logs to the curses window in the correct format
    """

    def __init__(self, screen, log_pad):
        """

        Parameters
        ----------
        screen: _curses.window
            The main terminal screen
        log_pad: _curses.window
            The pad that we are printing out log too.
        """
        logging.Handler.__init__(self)
        self.screen = screen
        self.log_pad = log_pad

    def emit(self, record):
        try:
            msg = self.format(record)
            screen = self.screen
            log_pad = self.log_pad
            fs = "\n%s"
            log_pad.addstr(fs % msg)
            # screen.box()
            # refresh_pad(screen, log_pad)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


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
        self.to_watch_directory_list = []
        self.watched_directory_set = set()
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
            return OrderedDict(
                sorted(
                    {
                        key: {
                            k: self.convert(time.time() - v)
                            if isinstance(v, float)
                            else v
                            for k, v in value.items()
                        }
                        for key, value in self._connected_positions.items()
                    }.items(),
                    key=operator.itemgetter(0),
                )
            )
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
            if char_widths.get("sample_id", 0) > 8:
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

    def check_fastq_info(self):
        """
        Check that a fastq info isn't out of data. Pop an entry if acquistion_finished = True and there an files queued
        Returns
        -------
        None
        """
        iteration_safe_dict = json.loads(json.dumps(self.fastq_info))
        for run_id, info_dict in iteration_safe_dict.items():
            files_queued = (
                info_dict.get("files_seen", 0)
                - info_dict.get("files_processed", 0)
                - info_dict.get("files_skipped", 0)
            )
            if info_dict.get("acquisition_finished", False) and not files_queued:
                log.info(
                    "{} being popped as files queued is {} and acquisition is finished ({})".format(
                        run_id, files_queued, info_dict["acquisition_finished"]
                    )
                )
                self.fastq_info.pop(run_id)
                log.info(pformat(self.fastq_info))


def refresh_pad(screen, pad):
    """

    Parameters
    ----------
    screen: _curses.window
        Main curses we add the pad too
    pad: _curses.window
        Curses window
    sequencing_stats: minFQ.utils.SequencingStatistics
        Sequencing stats class stores info

    Returns
    -------
    None
    """
    num_rows, num_cols = screen.getmaxyx()
    # pad.addstr(0, 0, "{} rows, {} cols".format(num_rows, num_cols))
    pad.refresh(0, 0, 0, 0, num_rows - 1, num_cols - 1)
    # sequencing_stats.screen_num_rows = num_rows
    # sequencing_stats.screen_num_cols = num_cols


def ascii_minotour(stdscr):
    """
    Add an ascii minotour in the top right because why not
    Parameters
    ----------
    stdscr

    Returns
    -------

    """
    stdscr.addstr(0, 92, "     .                .", curses.color_pair(2))
    stdscr.addstr(1, 92, "     -+:...       ..:+=", curses.color_pair(2))
    stdscr.addstr(2, 92, "      :+*##%%%%%%##*+:", curses.color_pair(2))
    stdscr.addstr(3, 92, "    :-=+**.*%%%%#.**++=-.", curses.color_pair(2))
    stdscr.addstr(4, 92, " :*@@@@@@@-*%%%%%.@@@@@@@%=", curses.color_pair(2))
    stdscr.addstr(5, 92, "+@@@@@@@@@%.+%%#-+@@@@@@@@@*", curses.color_pair(2))
    stdscr.addstr(6, 92, "@@@@@%.-*@@@*==+%@@%- =@@@@@", curses.color_pair(2))
    stdscr.addstr(7, 92, ":@@@@#   :@@@@@@@@+   -@@@@=", curses.color_pair(2))
    stdscr.addstr(8, 92, " .+@@@+##-:@@@@@@+.*#=%@@#- ", curses.color_pair(2))
    stdscr.addstr(9, 92, "    =#@@@@ #@@@@@.=@@@%+.   ", curses.color_pair(2))
    stdscr.addstr(10, 92, "       :-.:*%%%%%- -:   ", curses.color_pair(2))
    stdscr.addstr(11, 92, "         +%%+--=#%#-        ", curses.color_pair(2))
    stdscr.addstr(12, 92, "        :##      *%+      ", curses.color_pair(2))
    stdscr.addstr(13, 92, "       .:=*:     +*-.", curses.color_pair(2))


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
        "Connected to minoTour at: {}\n".format(
            sequencing_statistics.minfq_uptime, sequencing_statistics.minotour_url
        ),
    )
    stdscr.addstr(
        sequencing_statistics.minfq_y + 4,
        0,
        "Total FASTQ files Queued: {}".format(
            sequencing_statistics.files_seen
            - sequencing_statistics.files_processed
            - sequencing_statistics.files_skipped
        ),
    )
    stdscr.addstr(
        sequencing_statistics.minfq_y + 4,
        43,
        "Total Reads Queued: {}".format(
            sequencing_statistics.reads_seen
            - sequencing_statistics.reads_uploaded
            - sequencing_statistics.reads_skipped
        ),
    )
    stdscr.addstr(
        sequencing_statistics.minfq_y + 5,
        0,
        "Total FASTQ files Uploaded: {}".format(sequencing_statistics.files_processed,),
    )
    stdscr.addstr(
        sequencing_statistics.minfq_y + 5,
        43,
        "Total Reads Uploaded: {}".format(sequencing_statistics.reads_uploaded),
    )
    stdscr.addstr(
        sequencing_statistics.minfq_y + 6,
        0,
        "Total FASTQ files Already seen: {}".format(
            sequencing_statistics.files_skipped
        ),
    )
    stdscr.addstr(
        sequencing_statistics.minfq_y + 6,
        43,
        "Total Reads Uploaded: {} ".format(sequencing_statistics.reads_skipped),
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
        "Base-called data upload stats\n------------------------------\nDirectories watched: {}".format(
            len(sequencing_statistics.watched_directory_set)
        ),
    )
    stdscr.addstr(
        sequencing_statistics.fastq_y + 3,
        0,
        str(sequencing_statistics.fastq_message)
    )
    cols_y = sequencing_statistics.fastq_y + 5
    stdscr.addstr(cols_y, 0, "Run id")
    stdscr.addstr(cols_y, 15, "Queued")
    stdscr.addstr(cols_y, 30, "Uploaded")
    stdscr.addstr(cols_y, 45, "Already Seen")
    stdscr.addstr(cols_y, 60, "Directory")
    stdscr.addstr(cols_y + 1, 15, "Files/Reads")
    stdscr.addstr(cols_y + 1, 30, "Files/Reads")
    stdscr.addstr(cols_y + 1, 45, "Files/Reads")
    iteration_safe_dict = json.loads(json.dumps(sequencing_statistics.fastq_info))
    for index, value in enumerate(iteration_safe_dict.values()):
        stdscr.addstr(cols_y + index + 2, 0, str(value.get("run_id", ""))[:10])
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
            cols_y + index + 2, 15, "{}/{}".format(str(files_queued), str(reads_queued))
        )
        stdscr.addstr(
            cols_y + index + 2,
            30,
            "{}/{}".format(
                str(value.get("files_processed", 0)),
                str(value.get("reads_uploaded", 0)),
            ),
        )
        stdscr.addstr(
            cols_y + index + 2,
            45,
            "{}/{}".format(
                str(value.get("files_skipped", 0)), str(value.get("reads_skipped", 0))
            ),
        )
        stdscr.addstr(cols_y + index + 2, 60, str(value.get("directory", 0)))


def test(stdscr):
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.curs_set(1)
    curses.endwin()
    return __version__


def add_arguments_to_parser(parser, stdscr):
    """
    Add command line arguments to the parser.
    Parameters
    ----------
    parser: configargparse.ArgumentParser
        The argument parser instance
    stdscr: _curses.window
        The curses window object
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
        help="Set the logging level, default INFO.",
        dest="loglevel",
    )

    parser.add_argument(
        "-V", "--version", action="version", version=test(stdscr),
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
    parser.add_argument(
        "-ps",
        "--primer-scheme",
        type=int,
        default=None,
        required=False,
        help="Set the primer scheme to use for artic tasks. Valid options can be seen using --list.",
        dest="primer_scheme"
    )
    return parser


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
            error_string = "The watch directory specified {} does not exist. Please check specified path.".format(
                args.watch_dir
            )

        if args.no_fastq:
            error_string = (
                "If not monitoring FASTQ please do not provide a watch directory."
            )
    if args.job and args.job == 16:
        if not args.reference:
            error_string = "Reference required for Artic job type. Please provide."
        if not args.primer_scheme:
            error_string = "Primer Scheme required for Artic job type. Please provide."

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
            "Server does not support this client. Please check server version or upgrade/downgrade client."
        )
        log.error("Server supports minFQ versions:")
        for client in clients:
            log.error(client)
        raise Exception(
            "Server does not support this client. "
            "Please change the client to a previous version or upgrade server."
        )
    else:
        return "minFQ version: {} is compatible with minoTour server specified.\n".format(
            __version__
        )


def list_minotour_options(log, args, minotour_api, stdscr, screen):
    """
    List the options for jobs we can start, references and threat sets for metagenomics
    Parameters
    ----------
    log: logging.Logger
        The logger for this script
    args: argparse.Namespace
        Namespace for chosen arguments after parsing
    minotour_api: minFQ.minotourapi.MinotourAPI
        API convenience class
    stdscr: _curses.pad
        The window for the curses display
    screen: _curses.window
        The window for the curses display
    Returns
    -------
    None
    """
    stdscr.clear()
    stdscr.addstr(
        0, 0, "Fetching available Jobs, References and Targets...", curses.color_pair(5)
    )
    # TODO combine below into new single API end point
    jobs = minotour_api.get_json(EndPoint.TASK_TYPES, params={"cli": True})["data"]
    references = minotour_api.get_json(EndPoint.REFERENCES)["data"]
    schemes = minotour_api.get_json(EndPoint.PRIMER_SCHEMES)["data"]
    params = {"api_key": args.api_key, "cli": True}
    targets = minotour_api.get_json(EndPoint.TARGET_SETS, params=params)
    stdscr.addstr(
        2, 0, "The following jobs are available on this minoTour installation:"
    )
    line_num = 3
    for job_info in jobs:
        if not job_info["name"].startswith("Delete"):
            stdscr.addstr(
                line_num,
                0,
                "\t{}:{}".format(
                    job_info["id"], job_info["name"].lower().replace(" ", "_")
                ),
                curses.color_pair(3),
            )
            line_num += 1
    line_num += 1
    stdscr.addstr(
        line_num,
        0,
        "If you wish to run an alignment, the following references are available:",
    )
    line_num += 1
    for reference in references:
        stdscr.addstr(
            line_num,
            0,
            "\t{}:{}".format(reference["id"], reference["name"]),
            curses.color_pair(4),
        )
        line_num += 1
    line_num += 1
    stdscr.addstr(
        line_num,
        0,
        "If you wish to add a target set to the metagenomics task, the following sets are available to you:",
    )
    line_num += 1
    index = 1
    for target in targets:
        stdscr.addstr(
            line_num, 0, "\t{}:{}".format(index, target), curses.color_pair(2)
        )
        index += 1
        line_num += 1
    line_num += 1
    stdscr.addstr(
        line_num,
        0,
        "Artic primer scheme choice - MANDATORY for starting artic Jobs - use the ID number on the right",
    )
    line_num += 1
    for scheme in schemes:
        stdscr.addstr(
            line_num, 0, "\t{} : {} - {}".format(scheme["id"], scheme["scheme_species"], scheme["scheme_version"]), curses.color_pair(2)
        )
        index += 1
        line_num += 1
    refresh_pad(screen, stdscr)
    curses.napms(6000)
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.curs_set(1)
    curses.endwin()
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
    if args.job == "artic" or args.job == 16:
        if not args.primer_scheme:
            log.error("Primer scheme required for artic job.")
            sys.exit(1)