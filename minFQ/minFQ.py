import os
import sys
import platform
import logging
import logging.handlers
import time

CLIENT_VERSION = "1.2"
from minFQ.minknow_connection import MinionManager
from minFQ.fastq_handler import FastqHandler
import configargparse
from watchdog.observers.polling import PollingObserver as Observer
from minFQ.minotourapi import MinotourAPI
from minFQ.utils import clear_lines, add_arguments_to_parser, configure_logging, validate_args, \
    check_server_compatibility, SequencingStatistics, list_minotour_options, check_job_from_client, \
    write_out_fastq_stats

#from minFQ.minknowconnection import MinknowConnectRPC


root_directory = os.path.dirname(os.path.realpath(__file__))

def start_minknow_and_basecalled_monitoring(sequencing_statistics, args, log, header, minotour_api):
    """
    Start the minKnow monitoring and basecalled data monitoring in accordance with arguments passed by user
    Parameters
    ----------
    sequencing_statistics: minFQ.utils.SequencingStatistics
        Tracker class for files being monitored, and the metrics about upload
    args: argparse.NameSpace
        The command line arguments that were passed to the script
    log: logging.Logger
        The logger for this cript
    header: dict
        The dictionary with headers for the requests, including authentiction
    minotour_api: minFQ.minotourapi.MinotourAPI
        The minotourAPI class

    Returns
    -------

    """
    already_watching_set = set()
    sequencing_statistics.read_count = 0
    runs_being_monitored_dict = {}
    if not args.no_fastq:
        log.info("Setting clear_lines FastQ monitoring.")
        # This block handles the fastq
        # Add our watchdir to our WATCHLIST
        if args.watch_dir is not None:
            sequencing_statistics.directory_watch_list.append(args.watch_dir)
        # if we are connecting to minKNOW
        if not args.no_minknow:
            # this block is going to handle the running of minknow monitoring by the client.
            minknow_connection = MinionManager(args=args, header=header, sequencing_statistics=sequencing_statistics)
            log.info("MinKNOW RPC Monitoring Working.")
        sys.stdout.write("To stop minFQ use CTRL-C.\n")
        event_handler = FastqHandler(args, header, runs_being_monitored_dict, sequencing_statistics, minotour_api)
        observer = Observer()
        observer.start()
        try:
            while 1:
                line_counter = 0
                if not args.no_fastq and sequencing_statistics.directory_watch_list:
                    for folder in sequencing_statistics.directory_watch_list:
                        if folder and folder not in already_watching_set:
                            # We have a new folder that hasn't been added.
                            # We need to add this to our list to schedule and catalogue the files.
                            sequencing_statistics.update = True
                            already_watching_set.add(folder)
                            event_handler.addfolder(folder)
                            log.info("FastQ Monitoring added for {}".format(folder))
                    if sequencing_statistics.update:
                        observer.unschedule_all()
                        for folder in sequencing_statistics.directory_watch_list:
                            if folder and os.path.exists(folder):
                                observer.schedule(
                                    event_handler, path=folder, recursive=True
                                )
                        sequencing_statistics.update = False
                    line_counter = write_out_fastq_stats(sequencing_statistics, line_counter)

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

        except KeyboardInterrupt:
            log.info("Exiting - Will take a few seconds to clean clear_lines!")
            if not args.no_minknow:
                minknow_connection.stop_monitoring()
            if not args.no_fastq:
                observer.stop()
                observer.join()
                event_handler.stopt()
            sys.exit(0)


def main():
    """
    Entry point for minFQ, parses CLI arguments and sets off correct scripts
    Returns
    -------

    """

    if platform.system() == "Windows":  # MS
        config_file = os.path.join(os.path.sep, sys.prefix, "minfq_windows.config")
    else:
        config_file = os.path.join(
            os.path.sep, os.path.dirname(os.path.realpath("__file__")), "minfq_unix.config",
        )

    parser = configargparse.ArgParser(
        description="minFQ: A program to analyse minION fastq files in real-time or post-run and monitor the activity of MinKNOW.",
        default_config_files=[config_file],
    )
    parser = add_arguments_to_parser(parser)
    # Get the arguments namespace
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
    ### List to hold folders we want to watch
    sequencing_statistics = SequencingStatistics()

    if args.list:
        list_minotour_options(log, args, minotour_api)
    # Below we perform checks if we are trying to set a job.
    if args.job is not None:
        check_job_from_client(args, log, minotour_api, parser)
    start_minknow_and_basecalled_monitoring(sequencing_statistics, args, log, header, minotour_api)

if __name__ == "__main__":
    main()
