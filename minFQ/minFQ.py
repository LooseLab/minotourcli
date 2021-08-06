import os
import sys
import platform
import logging
import time
import curses

from minFQ.minknow_connection import MinionManager
from minFQ.fastq_handler import FastqHandler
import configargparse
from watchdog.observers.polling import PollingObserver as Observer
from minFQ.minotourapi import MinotourAPI
from minFQ.utils import (
    add_arguments_to_parser,
    validate_args,
    check_server_compatibility,
    SequencingStatistics,
    list_minotour_options,
    check_job_from_client,
    write_out_minfq_info, write_out_minknow_info, write_out_fastq_info,
    refresh_pad, ascii_minotour,
    CursesHandler
)

logging.basicConfig(
    format="%(asctime)s %(module)s:%(levelname)s:%(thread)d:%(message)s",
    filename="minFQ.log",
    filemode="w",
    level=logging.INFO,
)

log = logging.getLogger()
log.setLevel(logging.DEBUG)

# define a Handler which writes INFO messages or higher to the sys.stderr
# log = logging.getLogger("minFQ")


def start_minknow_and_basecalled_monitoring(
    sequencing_statistics, args,  header, minotour_api, stdscr, screen, log_win
):
    """
    Start the minKnow monitoring and basecalled data monitoring in accordance with arguments passed by user
    Parameters
    ----------
    sequencing_statistics: minFQ.utils.SequencingStatistics
        Tracker class for files being monitored, and the metrics about upload
    args: argparse.NameSpace
        The command line arguments that were passed to the script
    log: logging.Logger
        The logger for this script
    header: dict
        The dictionary with headers for the requests, including authentiction
    minotour_api: minFQ.minotourapi.MinotourAPI
        The minotourAPI class
    stdscr: _curses.window
        Curses window for printing out
    screen: _curses.window
        The main curses screen
    log_win: _curses.window
        The logging window we write to
    Returns
    -------

    """
    sequencing_statistics.read_count = 0
    runs_being_monitored_dict = {}
    if not args.no_fastq:
        # This block handles the fastq
        # Add our watchdir to our WATCHLIST
        if args.watch_dir is not None:
            sequencing_statistics.to_watch_directory_list.append(args.watch_dir)
        # if we are connecting to minKNOW
    if not args.no_minknow:
        # this block is going to handle the running of minknow monitoring by the client.
        stdscr.addstr("Connecting to minknow instance at {}".format(args.ip))
        refresh_pad(screen, stdscr)
        minknow_connection = MinionManager(
            args=args, header=header, sequencing_statistics=sequencing_statistics
        )
    curses.napms(2000)
    stdscr.clear()
    event_handler = FastqHandler(
        args, header, runs_being_monitored_dict, sequencing_statistics, minotour_api
    )
    observer = Observer()
    observer.start()
    stats = True
    try:
        while True:
            try:
                c = stdscr.getch()
                if c == ord("l"):
                    stats = False
                elif c == ord("s"):
                    stats = True
            except curses.ERR:
                stats = True
            # todo these should be abstracted into one function as they are verrrry similar
            if stats:
                stdscr.addstr(0, 0, "To stop minFQ use CTRL-C. To see the logs, Press l. To return to stats, Press s.", curses.color_pair(4))
                stdscr.addstr(1, 0, "Fetching Data...")
                write_out_minfq_info(stdscr, sequencing_statistics)
                ascii_minotour(stdscr)
                write_out_minknow_info(stdscr, sequencing_statistics)
                write_out_fastq_info(stdscr, sequencing_statistics)
                refresh_pad(screen, stdscr)
                stdscr.overwrite(screen)
            else:
                log_win.overwrite(screen)
                # log_win.addstr(0, 0, "To stop minFQ use CTRL-C. To see the logs, Press l. To see info, Press s.", curses.color_pair(4))
                refresh_pad(screen, log_win)
            screen.refresh()
            if not args.no_fastq and sequencing_statistics.to_watch_directory_list:
                for folder in sequencing_statistics.to_watch_directory_list: # directory watchlist has the new run dir
                    log.warning("Checking folder {} that is in our to watch directory".format(folder))
                    if folder and folder not in sequencing_statistics.watched_directory_set:
                        # check that the folder exists, before adding it to be scheduled
                        if os.path.exists(folder):
                            # We have a new folder that hasn't been added.
                            # We need to add this to our list to schedule and catalogue the files.
                            # TODO bug here where we never remove directories from the already watching set - eventually this would lead to a massive set of strings in this set if minFQ is never quit
                            sequencing_statistics.watched_directory_set.add(folder)
                            event_handler.addfolder(folder)
                            log.info("FastQ Monitoring added for {}".format(folder))
                            sequencing_statistics.to_watch_directory_list.remove(folder)
                            sequencing_statistics.update = True
                        else:
                            log.warning(
                                "Waiting for minKNOW to create folder {} before updating watchdog.".format(
                                    folder
                                )
                            )
                log.warning("Updating observers is {}".format(sequencing_statistics.update))
                if sequencing_statistics.update:
                    observer.unschedule_all()
                    for folder in sequencing_statistics.watched_directory_set:
                        if folder and os.path.exists(folder):
                            log.info("Scheduling observer for {}, which does exist".format(folder))
                            observer.schedule(
                                event_handler, path=folder, recursive=True
                            )
                        else:
                            log.warning(
                                "Tried to add {}, but folder does not exist".format(
                                    folder
                                )
                            )
                    sequencing_statistics.update = False
                # check if we need to remove any fastq info
            sequencing_statistics.check_fastq_info()
            time.sleep(1)

            if sequencing_statistics.errored:
                log.error("Errored - Will take a few seconds to clean clear_lines!")
                log.error(sequencing_statistics.error_message)
                if not args.no_minknow:
                    minknow_connection.stop_monitoring()
                if not args.no_fastq:
                    observer.stop()
                    observer.join()
                observer.stop()
                observer.join()
                event_handler.stopt()
                curses.nocbreak()
                stdscr.keypad(False)
                curses.echo()
                curses.endwin()
                print(repr(sequencing_statistics.error_message))
                print("Exiting after error - Will take a few seconds to close threads.")
                sys.exit(0)

    except (KeyboardInterrupt, Exception) as e:
        stdscr.addstr("Exiting - Will take a few seconds to close threads.")
        if not args.no_minknow:
            minknow_connection.stop_monitoring()
        observer.stop()
        observer.join()
        event_handler.stopt()
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        print(repr(e))
        print("Exiting - Will take a few seconds to close threads.")
        sys.exit(0)


def main():
    """
    Entry point for minFQ, parses CLI arguments and sets off correct scripts
    Returns
    -------

    """
    screen = curses.initscr()
    num_rows, num_cols = screen.getmaxyx()
    stdscr = curses.newpad(200, 200)
    stdscr.scrollok(True)
    stdscr.nodelay(True)
    curses.noecho()
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_BLUE, -1)
    curses.init_pair(4, curses.COLOR_MAGENTA, -1)
    curses.init_pair(5, curses.COLOR_YELLOW, -1)
    stdscr.clear()
    ## create log window
    num_rows, num_cols = screen.getmaxyx()
    log_win = curses.newpad(60, 200)
    log_win.scrollok(True)
    log_win.nodelay(True)
    log_win.idlok(True)
    log_win.leaveok(True)

    mh = CursesHandler(screen, log_win)
    mh.setLevel(logging.DEBUG)
    formatterDisplay = logging.Formatter("%(asctime)s %(module)s:%(levelname)s:%(thread)d:%(message)s")
    mh.setFormatter(formatterDisplay)
    log.addHandler(mh)
    if platform.system() == "Windows":  # MS
        config_file = os.path.join(os.path.sep, sys.prefix, "minfq_windows.config")
    else:
        config_file = os.path.join(
            os.path.sep,
            os.path.dirname(os.path.realpath("__file__")),
            "minfq_unix.config",
        )

    parser = configargparse.ArgParser(
        description="minFQ: A program to analyse minION fastq files in real-time or post-run and monitor the activity of MinKNOW.",
        default_config_files=[config_file],
    )
    parser = add_arguments_to_parser(parser, stdscr)
    # Get the arguments namespace
    args = parser.parse_args()
    handler = logging.getLogger().handlers[0]
    # old_level = console_handler.level
    # console_handler.setLevel(logging.DEBUG)
    handler.setLevel(getattr(logging, args.loglevel.upper()))
    log.setLevel(getattr(logging, args.loglevel.upper()))
    # log = configure_logging(getattr(logging, args.loglevel.upper()), screen, log_win)
    stdscr.addstr(str("""Welcome to
           _      ______ _____ 
          (_)     |  ___|  _  |
 _ __ ___  _ _ __ | |_  | | | |
| '_ ` _ \| | '_ \|  _| | | | |
| | | | | | | | | | |   \ \/' /
|_| |_| |_|_|_| |_\_|    \_/\_\ \n"""), curses.color_pair(2))
    refresh_pad(screen, stdscr)
    header = {
        "Authorization": "Token {}".format(args.api_key),
        "Content-Type": "application/json",
        "Content-Encoding": "gzip"
    }
    stdscr.addstr("""MMMMMMMMMMMNNMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWWWMMMMMMMMMMM
MMMMMMMMMMWkkNMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWKOXMMMMMMMMMMM
MMMMMMMMMMWx:dKNWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWWXkcoXMMMMMMMMMMM
MMMMMMMMMMMKl;:lxkO0KKKXXNNNNWWWWWNNNNXXXKKK0Oxoc;:kWMMMMMMMMMMM
MMMMMMMMMMMWKd:;,,;;;:::ccclllllllllcccc:::;;,,,;lONMMMMMMMMMMMM
MMMMMMMMMMMMMWXOxollcc::;;,,,,,,,,,,,,;:::cclodk0NMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMWWXK00KOo;,,,,,,,,,,:d0KK0KNWWMMMMMMMMMMMMMMMMM
MMMMMMMMMNKkxoc:;;,,''xW0c,,,,,,,,,,,,lKWx'',,;;:loxOKWMMMMMMMMM
MMMMWXko;'.          .dWk;,,,,,,,,,,,,:kWd           .':oONMMMMM
MMNkc.                oWO:,,,,,,,,,,,,c0Wo                .cONMM
WO;                   :XXd;,,,,,,,,,,;dNK;                   ;0W
x.                     lNKo;,,,,,,,,;oXXc                     .k
.                       lXXxc,,,,,;cxXXc                       '
            .co;.        'xXKOxddxOXXd'        .:oc.            
           .xWMW0o'        'lxkOOkxl'        'oKWMWd.          .
'          ;XMMMMMXl.                      .oXMMMMMK,          ,
k.         ,0MMMMMMWO,                    ,OWMMMMMMO'         .O
WO'        .dWMMMMMMMX:                  cXMMMMMMMWo         'OM
MMKl.       'OKdc:lkNMK;                :XMXxl:cdKk.       .lXMM
MMMW0c.      ..     ;KM0,              ;KM0,     ..      .c0WMMM
MMMMMWKo,.           oMMd             .xMWl           .,dKWMMMMM
MMMMMMMMW0o;.        oMM0'            ,KMWl        .;d0WMMMMMMMM
MMMMMMMMMMMWXko:,. .cKMMWl            lWMMK:  .,:oOXWMMMMMMMMMMM
MMMMMMMMMMMMMMMMWXO0NWWKx:''''''''''',cxKWMN0OXWMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMWKd:;,,,,,,,,,,,,,,,:dKWMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMWXx:,,,,;:loddddol:;,,,,:xKWMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMNOc;,,,;lkKNWMMMMWNKkc;,,,;cONMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMNx;,,,;oXWMMMMMMMMMMWKl;,,,;dNMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMNk:,,:OWMMMMMMMMMMMMWk;,,:kNMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMWNx:,;xNMMMMMMMMMMMMNx;,:xNWMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMNKko:;,,:xNMMMMMMMMMMNx:,,;:okKNMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMWXkdddddddxKWMMMMMMMMMXxdddddddkXWMMMMMMMMMMMMMMM\n""", curses.color_pair(4))
    stdscr.addstr("Welcome to minFQ, the upload client for minoTour.\n")
    refresh_pad(screen, stdscr)
    try:
        validate_args(args)
        minotour_api = MinotourAPI(args.host_name, args.port_number, header)
        test_message = minotour_api.test()
        stdscr.addstr(test_message, curses.color_pair(1))
        refresh_pad(screen, stdscr)
        compatibility_message = check_server_compatibility(minotour_api, log)
        stdscr.addstr(compatibility_message, curses.color_pair(2))
        refresh_pad(screen, stdscr)
        ### List to hold folders we want to watch
        sequencing_statistics = SequencingStatistics()
        sequencing_statistics.screen_num_cols = num_cols
        sequencing_statistics.screen_num_rows = num_rows
        sequencing_statistics.minotour_url = "{}:{}".format(args.host_name, args.port_number)
        if args.list:
            list_minotour_options(log, args, minotour_api, stdscr, screen)
        # Below we perform checks if we are trying to set a job.
        if args.job is not None:
            check_job_from_client(args, log, minotour_api, parser)
        start_minknow_and_basecalled_monitoring(
            sequencing_statistics, args,  header, minotour_api, stdscr, screen, log_win
        )
    except Exception as e:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.curs_set(1)
        curses.endwin()
        print(e)
        sys.exit(0)

