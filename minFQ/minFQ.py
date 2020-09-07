import os
import sys
import platform
import logging
import time

from minFQ.minknow_connection import MinionManager
from minFQ.utils import add_args, configure_logging, list_minotour_options, validate_args, check_job_from_client, \
    check_server_compatibility, SequencingStatistics, check_upload_directories, write_out_fastq_stats
from minFQ.fastqutils import FastqHandler
import configargparse
from watchdog.observers.polling import PollingObserver as Observer
from minFQ.minotourapi import MinotourAPI


"""We are setting clear_lines the code to copy and import the rpc service from minKNOW and make
it work on our own code. This prevents us from having to distribute ONT code ourselves."""

root_directory = os.path.dirname(os.path.realpath(__file__))


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


def monitor_sequencing(args, log, header):
    """

    Returns
    -------

    """
    upload_stats = SequencingStatistics()

    if not args.no_minknow:
        # if we are connecting to minKNOW
        # this block is going to handle the running of minknow monitoring by the client.
        minknow_connection = MinionManager(args=args, header=header)
        log.info("MinKNOW RPC Monitoring Working.")

    if not args.no_fastq:
        ### Horrible tracking of run stats.
        WATCH_DICT = {}
        rundict = {}
        log.info("Setting clear_lines FastQ monitoring.")
        # This block handles the fastq
        # Add our watchdir to our WATCHLIST
        upload_stats.directory_watch_list.append(args.watchdir)
        sys.stdout.write("To stop minFQ use CTRL-C.\n")
        # sort out watch dog stuff
        event_handler = FastqHandler(args, header, rundict)
        observer = Observer()
        observer.start()
    try:
        while 1:
            line_counter = 0
            if not args.no_fastq and upload_stats.directory_watch_list:
                # fixme global use of args name space, replace with SequencingStats
                check_upload_directories(upload_stats, WATCH_DICT, event_handler, observer, log)
                line_counter = write_out_fastq_stats(upload_stats, line_counter)
            if not args.no_minknow:
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

    except KeyboardInterrupt:
        log.info("Exiting - Will take a few seconds to clean clear_lines!")
        if not args.no_minknow:
            minknow_connection.stop_monitoring()
        if not args.no_fastq:
            observer.stop()
            observer.join()
        event_handler.stopt()
        sys.exit(0)
    except Exception as e:
        log.error(e)
    finally:
        print("Finally done.")


def main():
    """
    Entry point for minFQ, parses CLI arguments, starts monitoring
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
    parser = add_args(parser)
    args = parser.parse_args()
    log = configure_logging(getattr(logging, args.loglevel))
    log.info("Initialising minFQ.")
    header = {
        "Authorization": "Token {}".format(args.api_key),
        "Content-Type": "application/json",
    }
    validate_args(args, parser)
    minotour_api = MinotourAPI(args.host_name, args.port_number, header)
    check_server_compatibility(minotour_api, log)

    # fixMe set up upload stats dict here, instead of passing args around
    args.job_id = 0

    if args.list:
        list_minotour_options(log, args, minotour_api)
    # Below we perform checks if we are trying to set a job.
    if args.job is not None:
        check_job_from_client(args, log, minotour_api, parser)
    # Do all our monitoring in here
    monitor_sequencing(args, log, header)


if __name__ == "__main__":
    main()
