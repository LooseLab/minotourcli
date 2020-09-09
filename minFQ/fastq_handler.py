"""
File Routines for handling fastq files and monitoring locations. Built on watchdog.
"""
import logging
import os
import subprocess
import threading
import time
import gzip
import numpy as np
from minFQ.fastq_handler_utils import file_dict_of_folder_simple, parse_fastq_file
from minFQ.run_collection import Runcollection
from minFQ.minotourapi import MinotourAPI
from watchdog.events import FileSystemEventHandler

log = logging.getLogger(__name__)


class OpenLine:
    def __init__(self, fp, start=1, number=-1, f=open, f_kwds=None):
        """

        Generic function to return a generator for reading a file from a given line.

        Parameters
        ----------
        fp : str
            Filepath to the file.
        start : int
            Starting line number. Default 1.
        number : int
            The number of lines to read. If -1, will read to EOF. Default -1
        f : func
            The opening function that is used on the provided filepath. Default open
        f_kwds: dict
            The keyword args to pass to the open function. Default None.
        """
        self.fp = fp
        self.start = start
        self.number = number
        self.open_func = f
        self.current_line = 0

        if number == -1:
            self.number = float("inf")

        if f_kwds is None:
            self.f_kwds = {}
        else:
            self.f_kwds = f_kwds

    def __enter__(self):
        with self.open_func(self.fp, **self.f_kwds) as fh:
            for i, L in enumerate(fh, start=1):
                if i < self.start:
                    continue
                if i >= self.start + self.number:
                    break
                self.current_line = i
                yield L.strip()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return True


class FastqHandler(FileSystemEventHandler):
    # TODO check this out another time
    def __init__(self, args, header, run_dict, upload_data):
        """
        Collect information about files already in the folders
        """
        self.file_descriptor = {}
        self.args = args
        self.upload_data = upload_data
        self.header = header
        # adding files to the file_descriptor is really slow - therefore lets skip that and only update the files when we want to basecall thread_number
        self.MinotourConnection = MinotourAPI(
            self.args.host_name, self.args.port_number, self.header
        )
        self.run_dict = run_dict
        self.fastq_dict = dict()
        # self.unblocked_read_ids_dict = {}
        # self.unblocked_line_start = 1
        self.toml_dict = {}
        self.creates = {}
        self.processing = {}
        self.running = True

        self.t = threading.Thread(target=self.process_files)
        self.grouprun = None

        try:
            self.t.start()
        except KeyboardInterrupt:
            self.t.stop()
            raise

    def add_folder(self, folder):
        self.creates.update(
            file_dict_of_folder_simple(
                folder, self.args, self.MinotourConnection, self.fastq_dict,
            )
        )

    def stopt(self):
        self.running = False

    def len_creates(self):
        return len(self.creates)

    def len_processed(self):
        return len(self.processed)

    def process_files(self):
        """
        Process fastq files in a threaded manner |
        :return:
        """
        while self.running:
            current_time = time.time()
            for fastqfile, createtime in sorted(
                self.creates.items(), key=lambda x: x[1]
            ):
                delay_time = 10
                # file created 5 sec ago, so should be complete. For simulations we make the time longer.
                if int(createtime) + delay_time < time.time():
                    del self.creates[fastqfile]
                    c = parse_fastq_file(
                        fastqfile,
                        self.run_dict,
                        self.args,
                        self.header,
                        self.MinotourConnection,
                        upload_data=self.upload_data
                        # self.unblocked_read_ids_dict,
                        # self.unblocked_line_start
                    )

                    # self.unblocked_line_start += new_unblocked_line_start
                    self.upload_data.files_processed += 1
                    self.args.read_up_time = time.time()
            if current_time + 5 > time.time():
                time.sleep(5)
            log.debug("still ticking")

    def on_created(self, event):
        """Watchdog counts a new file in a folder it is watching as a new file"""
        """This will add a file which is added to the watchfolder to the creates and the info file."""

        log.debug("Processing file {}".format(event.src_path))
        # time.sleep(5)
        if (
            event.src_path.endswith(".fastq")
            or event.src_path.endswith(".fastq.gz")
            or event.src_path.endswith(".fq")
            or event.src_path.endswith(".fq.gz")
        ):
            self.upload_data.files_seen += 1
            self.creates[event.src_path] = time.time()

    def on_modified(self, event):
        if (
            event.src_path.endswith(".fastq")
            or event.src_path.endswith(".fastq.gz")
            or event.src_path.endswith(".fq")
            or event.src_path.endswith(".fq.gz")
        ):
            log.debug("Modified file {}".format(event.src_path))
            self.creates[event.src_path] = time.time()

    def on_moved(self, event):
        if any(
            (
                event.dest_path.endswith(".fastq"),
                event.dest_path.endswith(".fastq,gz"),
                event.dest_path.endswith(".gq"),
                event.dest_path.endswith(".fq.gz"),
            )
        ):
            log.debug("Modified file {}".format(event.dest_path))
            self.creates[event.dest_path] = time.time()
