import os
import sys
import platform
import logging
import logging.handlers
import time
import curses
import traceback


from minFQ.minknow_connection import MinionManager
from minFQ.fastq_handler import FastqHandler
import configargparse
from watchdog.observers.polling import PollingObserver as Observer
from minFQ.minotourapi import MinotourAPI
from minFQ.utils import (
    add_arguments_to_parser,
    configure_logging,
    validate_args,
    check_server_compatibility,
    SequencingStatistics,
    list_minotour_options,
    check_job_from_client,
    write_out_minfq_info, write_out_minknow_info, write_out_fastq_info,
    refresh_pad
)


def start_minknow_and_basecalled_monitoring(
    sequencing_statistics, args, log, header, minotour_api, stdscr, screen
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
    Returns
    -------

    """
    already_watching_set = set()
    sequencing_statistics.read_count = 0
    runs_being_monitored_dict = {}
    if not args.no_fastq:
        # This block handles the fastq
        # Add our watchdir to our WATCHLIST
        if args.watch_dir is not None:
            sequencing_statistics.directory_watch_list.append(args.watch_dir)
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
    stdscr.addstr("To stop minFQ use CTRL-C.\n")
    stdscr.addstr("Fetching Data...\n")
    refresh_pad(screen, stdscr)
    event_handler = FastqHandler(
        args, header, runs_being_monitored_dict, sequencing_statistics, minotour_api
    )
    observer = Observer()
    observer.start()
    try:
        while 1:
            # todo these should be abstracted into one function as they are verrrry similar
            write_out_minfq_info(stdscr, sequencing_statistics)
            write_out_minknow_info(stdscr, sequencing_statistics)
            write_out_fastq_info(stdscr, sequencing_statistics)
            refresh_pad(screen, stdscr)
            if not args.no_fastq and sequencing_statistics.directory_watch_list:
                for folder in sequencing_statistics.directory_watch_list:
                    if folder and folder not in already_watching_set:
                        # check that the folder exists, before adding it to be scheduled
                        if os.path.exists(folder):
                            # We have a new folder that hasn't been added.
                            # We need to add this to our list to schedule and catalogue the files.
                            sequencing_statistics.update = True
                            # TODO bug here where we never remove directories from the already watching set - eventually this would lead to a massive set of strings in this set if minFQ is never quit
                            already_watching_set.add(folder)
                            event_handler.addfolder(folder)
                            log.info("FastQ Monitoring added for {}".format(folder))
                        else:
                            log.warning(
                                "Waiting for minKNOW to create folder {} before updating watchdog.".format(
                                    folder
                                )
                            )
                if sequencing_statistics.update:
                    observer.unschedule_all()
                    for folder in sequencing_statistics.directory_watch_list:
                        if folder and os.path.exists(folder):
                            observer.schedule(
                                event_handler, path=folder, recursive=True
                            )
                        else:
                            log.warning(
                                "Tried to add {}, but folder most likely does not exist".format(
                                    folder
                                )
                            )
                    sequencing_statistics.update = False
                # line_counter = write_out_fastq_stats(
                #     sequencing_statistics
                # )

            # if not args.no_minknow:
            #     # stdscr.write("MinKNOW Monitoring Status:\n")
            #     for device in sequencing_statistics.connected_positions:
            #         # stdscr.addstr(
            #         #     "Connected minIONs: {}\n".format(device)
            #         # )
            #         stdscr.refresh()

            time.sleep(0.5)
            # if not args.verbose:
            #     clear_lines(line_counter)
            if sequencing_statistics.errored:
                log.info("Errored - Will take a few seconds to clean clear_lines!")
                log.error(sequencing_statistics.error_message)
                if not args.no_minknow:
                    minknow_connection.stop_monitoring()
                if not args.no_fastq:
                    observer.stop()
                    observer.join()
                event_handler.stopt()
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
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.noecho()
    stdscr.clear()
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
    log = configure_logging(getattr(logging, args.loglevel))
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
            list_minotour_options(log, args, minotour_api)
        # Below we perform checks if we are trying to set a job.
        if args.job is not None:
            check_job_from_client(args, log, minotour_api, parser)
        start_minknow_and_basecalled_monitoring(
            sequencing_statistics, args, log, header, minotour_api, stdscr, screen
        )
    except Exception as e:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.curs_set(1)
        curses.endwin()
        print(e)
        sys.exit(0)

