"""
File Routines for handling fastq files and monitoring locations. Built on watchdog.
"""
import logging
import os
import subprocess
import sys
import threading
import time
import gzip
import pyfastx
import numpy as np
import toml as toml_manager

from minFQ.fastq_handler_utils import (
    split_all,
    parse_fastq_description,
    get_file_size,
    get_runid,
    check_fastq_path,
    unseen_files_dict_of_watch_folder,
    _prepare_toml,
    OpenLine,
    create_run_collection, average_quality, check_is_pass,
)
from minFQ.run_collection import Runcollection
from minFQ.minotourapi import MinotourAPI
from watchdog.events import FileSystemEventHandler

log = logging.getLogger(__name__)


###Function modified from https://raw.githubusercontent.com/lh3/readfq/master/readfq.py

# Todo replace with pyfastx
def readfq(fp):  # this is a generator function
    last = None  # this is a buffer keeping the last unprocessed line
    while True:  # mimic closure; is it a bad idea?
        if not last:  # the first record or a record following a fastq
            for l in fp:  # search for the start of the next record
                if l[0] in ">@":  # fasta/q header line
                    last = l[:-1]  # save this line
                    break
        if not last:
            break
        desc, name, seqs, last = last[1:], last[1:].partition(" ")[0], [], None
        for l in fp:  # read the sequence
            if l[0] in "@+>":
                last = l[:-1]
                break
            seqs.append(l[:-1])
        if not last or last[0] != "+":  # this is a fasta record
            yield desc, name, "".join(seqs), None  # yield a fasta record
            if not last:
                break
        else:  # this is a fastq record
            seq, leng, seqs = "".join(seqs), 0, []
            for l in fp:  # read the quality
                seqs.append(l[:-1])
                leng += len(l) - 1
                if leng >= len(seq):  # have read enough quality
                    last = None
                    yield desc, name, seq, "".join(seqs)  # yield a fastq record
                    break
            if last:  # reach EOF before reading enough quality
                yield desc, name, seq, None  # yield a fasta record instead
                break


def parse_fastq_record(
    name,
    seq,
    qual,
    fastq,
    rundict,
    args,
    fastqfile,
    counter,
    sequencing_statistic,
    description_dict,
):
    """

    Parameters
    ----------
    name
    seq
    qual
    fastq
    rundict
    args
    fastqfile
    counter
    sequencing_statistic
    description_dict: dict
        The description dictionary

    Returns
    -------

    """
    log.debug("Parsing reads from file {}".format(fastq))
    fastq_read = {
        "read": description_dict.get("read", None),
        "runid": description_dict.get("runid", None),
        "channel": description_dict.get("ch", None),
        "start_time": description_dict.get("start_time", None),
        "read_id": name,
        "sequence_length": len(seq),
        "fastqfile": fastqfile["id"],
        "quality": qual,
        "sequence": seq
    }
    if args.skip_sequence:
        fastq_read["sequence"] = ""
        fastq_read["quality"] = ""
        # get or create fastfile if not in dictionary?
        # fastq_read['fastqfilename'] = fastqfileid
        # We need to get the toml dict here.
    ## This is going to need refactoring...
    if args.toml is not None:
        try:
            toml_dict = toml_manager.load(args.toml)
            toml_dict = _prepare_toml(toml_dict)
        except FileNotFoundError as e:
            sys.exit(
                "Error, toml file not found. Please check that it hasn't been moved."
            )
        rundict[fastq_read["runid"]].add_toml_file(toml_dict)
    ### Check the overlap between the current file path and the folders being watched:
    for folder in sequencing_statistic.directory_watch_list:
        if folder is not None:
            if fastq.startswith(folder):
                if rundict[fastq_read["runid"]].runfolder != folder:
                    ## We have found the folder that this fastq file comes from.
                    rundict[fastq_read["runid"]].add_run_folder(folder)

    ### Check for unblocked read files

        if args.unblocks is not None:
            rundict[fastq_read["runid"]].unblocked_file = args.unblocks

    if rundict[fastq_read["runid"]].unblocked_file is None:
        if os.path.exists(
            os.path.join(
                rundict[fastq_read["runid"]].runfolder, "unblocked_read_ids.txt"
            )
        ):
            rundict[fastq_read["runid"]].unblocked_file = os.path.join(
                rundict[fastq_read["runid"]].runfolder, "unblocked_read_ids.txt"
            )

    if rundict[fastq_read["runid"]].toml is None:
        ## Look and see if a toml file exists in the run folder.
        if os.path.exists(
            os.path.join(rundict[fastq_read["runid"]].runfolder, "channels.toml")
        ):
            try:
                toml_dict = toml_manager.load(
                    os.path.join(
                        rundict[fastq_read["runid"]].runfolder, "channels.toml"
                    )
                )
                toml_dict = _prepare_toml(toml_dict)

            except FileNotFoundError as e:
                log.error(
                    "Error, toml file not found. Please check that it hasn't been moved."
                )
                os._exit(2)

            rundict[fastq_read["runid"]].add_toml_file(toml_dict)

    if counter <= 1:
        ## This is the first read we have seen from this file - so we are going to check for updates in the unblocked read file.
        if rundict[fastq_read["runid"]].unblocked_file is not None:
            with OpenLine(
                rundict[fastq_read["runid"]].unblocked_file,
                rundict[fastq_read["runid"]].unblocked_line_start,
            ) as fh:
                _d = {line: 1 for line in fh}
                lines_returned = len(_d)
                rundict[fastq_read["runid"]].unblocked_dict.update(_d)
            rundict[fastq_read["runid"]].unblocked_line_start += lines_returned
    if fastq_read["read_id"] not in rundict[fastq_read["runid"]].read_names:
        quality = qual
        # Turns out this is not the way to calculate quality...
        # This is slow.
        if quality is not None:
            fastq_read["quality_average"] = round(average_quality(quality), 2,)
        fastq_read["is_pass"] = check_is_pass(fastq, fastq_read["quality_average"])
        # print (quality_average)

        # use 'No barcode' for non-barcoded reads
        barcode_name = description_dict.get("barcode", None)

        if barcode_name:

            fastq_read["barcode_name"] = barcode_name

        else:

            fastq_read["barcode_name"] = "No barcode"

        # Parse the channel out of the description and lookup it's corresponding condition
        # set it to the reads barcode
        if rundict[fastq_read["runid"]].toml is not None:
            fastq_read["barcode_name"] = rundict[fastq_read["runid"]].toml[
                int(fastq_read["channel"])
            ]
        if (
            rundict[fastq_read["runid"]].unblocked_dict
            and fastq_read["read_id"] in rundict[fastq_read["runid"]].unblocked_dict
        ):
            fastq_read["rejected_barcode_name"] = "Unblocked"
        else:
            fastq_read["rejected_barcode_name"] = "Sequenced"

        # add control-treatment if passed as argument
        if args.treatment_control:

            if int(fastq_read["channel"]) % args.treatment_control == 0:

                fastq_read["barcode_name"] = fastq_read["barcode_name"] + " - control"

            else:

                fastq_read["barcode_name"] = fastq_read["barcode_name"] + " - treatment"

        # check if sequence is sent or not

        # For speed lets throw away t12he quality
        # fastq_read["quality"] = ""
        # Add the read to the class dictionary to be uploaded, pretty important
        rundict[fastq_read["runid"]].add_read(fastq_read)

    else:
        sequencing_statistic.reads_skipped += 1


def parse_fastq_file(
    fastq_path, run_dict, args, header, minotour_api, sequencing_stats
):
    """
    
    Parameters
    ----------
    fastq_path: str
        Path to the fastq file to parse
    run_dict: dict
        Dictionary conating the run 
    args: argparse.NameSpace
        The namespace of the parsed command line args
    header: dict
        The authentication header to make requests to the server
    minotour_api: MinotourAPI
        The minotour API class instance for convenience request to the server
    sequencing_stats: SequencingStatistics
        The class to track the sequencing upload metrics and files

    Returns
    -------
    int 
        The updated number of lines we have already seen from the unblocked read ids file
    """
    # The updated number of lines we have already seen from the unblocked read ids file
    log.debug("Parsing fastq file {}".format(fastq_path))
    # Get runId from the path
    run_id = get_runid(fastq_path)
    # fixme manual post request
    fastq_file = minotour_api.create_file_info(
        str(check_fastq_path(fastq_path)), run_id, "0", None
    )
    counter = 0
    # fq = pyfastx.Fastq(fastq_path)
    # gen = (read for read in fq)
    # for read in gen:
    with open(fastq_path, "r") as fh:
        for desc, name, seq, qual in readfq(fh):
            description_dict = parse_fastq_description(desc)
            counter += 1
            sequencing_stats.reads_seen += 1
            sequencing_stats.fastq_message = "processing read {}".format(counter)
            try:
                ### We haven't seen this run before - so we need to check stuff.
                # create runCOllection in the runDict
                if description_dict["runid"] not in run_dict:
                    create_run_collection(
                        run_id,
                        run_dict,
                        args,
                        header,
                        description_dict,
                        fastq_file["id"],
                        sequencing_stats,
                    )
                parse_fastq_record(
                    name,
                    seq,
                    qual,
                    fastq_path,
                    run_dict,
                    args,
                    fastq_file,
                    counter=counter,
                    sequencing_statistic=sequencing_stats,
                    description_dict=description_dict,
                )

            except Exception as e:
                sequencing_stats.reads_corrupt += 1
                print(e)
                log.error(e)
                log.error("This gzipped file failed to upload - {}.".format(fastq_path))
                raise Exception
                # continue
    # This chunk of code will mean we commit reads every time we get a new file?
    for runs in run_dict:
        run_dict[runs].read_names = []
        run_dict[runs].commit_reads()
    try:
        # Update the fastq file entry on the server that says we provides file size to database record
        # fixme manual post
        fastq_file = minotour_api.create_file_info(
            str(check_fastq_path(fastq_path)),
            run_id,
            get_file_size(fastq_path),
            run_dict[run_id].run,
        )
    except Exception as err:
        log.error("Problem with uploading file {}".format(err))

    return counter


class FastqHandler(FileSystemEventHandler):
    def __init__(self, args, header, rundict, sequencing_statistic, minotour_api):
        """
        Collect information about fastq files that have been written out.
        Parameters
        ----------
        args: argparse.NameSpace
            The arguments provided on the command line
        header: dict
            The authentication header for the requests
        rundict: dict
            The dictionary for tracking the runs
        sequencing_statistic: SequencingStatistics
            The class for tracking files and metrics about the upload
        minotour_api: MinotourAPI
            The API class for convenience connecting to MinoTour server
        """
        self.sequencing_statistic = sequencing_statistic
        self.file_descriptor = {}
        self.args = args
        self.header = header
        # adding files to the file_descriptor is really slow - therefore lets skip that and only update the files when we want to basecall thread_number
        self.minotour_api = minotour_api
        self.rundict = rundict
        # Dict of all fastq files that we have seen, irrespective of if they exists on server or not
        self.fastq_dict = {}
        self.toml_dict = {}
        self.fastq_files_to_create = {}
        self.processing = {}
        self.running = True
        self.t = threading.Thread(target=self.process_files)
        try:
            self.t.start()
        except Exception as e:
            self.running = False
            self.args.errored = True
            self.args.error_message = "Flowcell name is required. This may be old FASTQ data, please provide a name with -n."
            log.error(
                "Flowcell name is required. This may be old FASTQ data, please provide a name with -n."
            )
            # raise BaseException()

    def addfolder(self, folder):
        self.fastq_files_to_create.update(
            unseen_files_dict_of_watch_folder(
                folder,
                self.args.ignore_existing,
                self.minotour_api,
                self.fastq_dict,
                self.sequencing_statistic,
            )
        )

    def addrunmonitor(self, runpath):
        """
        Add a new folder for checking reads in.
        :param runpath: the final part of the folder structure - effectively the sample name
        :return:
        """
        pass

    def stopt(self):
        self.running = False

    def lencreates(self):
        return len(self.fastq_files_to_create)

    def process_files(self):
        """
        Process fastq files in a thread. This is the work horse for read fastqs. We have one of these per watch directory in the watch list
        :return:
        """
        while self.running:
            current_time = time.time()
            # sort by created time descending
            for fastqfile, createtime in sorted(
                self.fastq_files_to_create.items(), key=lambda x: x[1]
            ):
                # file created 5 sec ago, so should be complete. For simulations we make the time longer.
                # remove the file from fastq files to create as we are doing that now
                del self.fastq_files_to_create[fastqfile]
                parse_fastq_file(
                    fastqfile,
                    self.rundict,
                    self.args,
                    self.header,
                    self.minotour_api,
                    self.sequencing_statistic,
                )
                self.sequencing_statistic.files_processed += 1

                if not self.running:
                    break
            if current_time + 5 > time.time():
                time.sleep(5)
            log.info("still ticking")

    def on_created(self, event):
        """Watchdog counts a new file in a folder it is watching as a new file"""
        """This will add a file which is added to the watchfolder to the creates and the info file."""
        # if (event.src_path.endswith(".fastq") or event.src_path.endswith(".fastq.gz")):
        #     self.creates[event.src_path] = time.time()

        log.debug("Processing file {}".format(event.src_path))
        # time.sleep(5)
        if (
            event.src_path.endswith(".fastq")
            or event.src_path.endswith(".fastq.gz")
            or event.src_path.endswith(".fq")
            or event.src_path.endswith(".fq.gz")
        ):
            self.sequencing_statistic.files_seen += 1
            self.fastq_files_to_create[event.src_path] = time.time()

    def on_modified(self, event):
        if (
            event.src_path.endswith(".fastq")
            or event.src_path.endswith(".fastq.gz")
            or event.src_path.endswith(".fq")
            or event.src_path.endswith(".fq.gz")
        ):
            log.debug("Modified file {}".format(event.src_path))
            self.fastq_files_to_create[event.src_path] = time.time()

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
            self.fastq_files_to_create[event.dest_path] = time.time()
