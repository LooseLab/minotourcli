"""
File Routines for handling fastq files and monitoring locations. Built on watchdog.
"""
import gzip
import logging
import sys
import threading
import time
import toml as toml_manager

from minFQ.endpoints import EndPoint
from minFQ.fastq_handler_utils import (
    parse_fastq_description,
    get_file_size,
    get_runid,
    check_fastq_path,
    unseen_files_in_watch_folder_dict,
    _prepare_toml,
    OpenLine,
    create_run_collection, average_quality, check_is_pass,
)
from watchdog.events import FileSystemEventHandler

log = logging.getLogger(__name__)


# ##Function modified from https://raw.githubusercontent.com/lh3/readfq/master/readfq.py

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
    fastq_file_path,
    run_dict,
    args,
    fastq_file,
    counter,
    sequencing_statistic,
    description_dict,
):
    """

    Parameters
    ----------
    name: str
        The fastq read id
    seq: str
        The sequence string for this fastq read
    qual: str
        The quality string for this fastq read
    fastq_file_path: str
        The absolute path to this fastq file
    run_dict: dict
        Dictionary containg runs that we have seen before and their RunCollection
    args: argparse.NameSpace
        The command line argumanets chosen
    fastq_file: dict
        Dictionary with the minoTour record info for the fastq file this read comes from
    counter: int
        The counter for the number of reads taht we have seen
    sequencing_statistic: SequencingStatistics
        The sequencing statistics class to track metrics about the run
    description_dict: dict
        The description dictionary, split by key to value

    Returns
    -------

    """
    log.debug("Parsing reads from file {}".format(fastq_file_path))
    fastq_read = {
        "read": description_dict.get("read", None),
        "run_id": description_dict.get("runid", None),
        "channel": description_dict.get("ch", None),
        "start_time": description_dict.get("start_time", None),
        "read_id": name,
        "sequence_length": len(seq),
        "fastq_file": fastq_file["id"],
        "quality": qual,
        "sequence": seq
    }
    if args.skip_sequence:
        fastq_read["sequence"] = ""
        fastq_read["quality"] = ""
    if args.toml is not None:
        try:
            toml_dict = toml_manager.load(args.toml)
            toml_dict = _prepare_toml(toml_dict)
        except FileNotFoundError as e:
            sys.exit(
                "Error, toml file not found. Please check that it hasn't been moved."
            )
        run_dict[fastq_read["run_id"]].add_toml_file(toml_dict)
    if args.unblocks is not None:
        run_dict[fastq_read["run_id"]].unblocked_file = args.unblocks
    ### Check the overlap between the current file path and the folders being watched:
    for folder in sequencing_statistic.directory_watch_list:
        if folder is not None:
            if fastq_file_path.startswith(folder):
                if run_dict[fastq_read["run_id"]].run_folder != folder:
                    ## We have found the folder that this fastq file comes from.
                    run_dict[fastq_read["run_id"]].add_run_folder(folder)


    if counter <= 1:
        ## This is the first read we have seen from this file - so we are going to check for updates in the unblocked read file.
        if run_dict[fastq_read["run_id"]].unblocked_file is not None:
            with OpenLine(
                run_dict[fastq_read["run_id"]].unblocked_file,
                run_dict[fastq_read["run_id"]].unblocked_line_start,
            ) as fh:
                _d = {line: 1 for line in fh}
                lines_returned = len(_d)
                run_dict[fastq_read["run_id"]].unblocked_dict.update(_d)
            run_dict[fastq_read["run_id"]].unblocked_line_start += lines_returned

    if fastq_read["read_id"] not in run_dict[fastq_read["run_id"]].read_names:
        quality = qual
        # Turns out this is not the way to calculate quality...
        # This is slow.
        if quality is not None:
            fastq_read["quality_average"] = round(average_quality(quality), 2,)
        fastq_read["is_pass"] = check_is_pass(fastq_file_path, fastq_read["quality_average"])
        # use 'No barcode' for non-barcoded reads
        barcode_name = description_dict.get("barcode", None)
        fastq_read["barcode_name"] = barcode_name.replace(" ", "_") if barcode_name else "No_barcode"
        # Parse the channel out of the description and lookup it's corresponding condition
        # set it to the reads barcode
        if run_dict[fastq_read["run_id"]].toml is not None:
            fastq_read["barcode_name"] = run_dict[fastq_read["run_id"]].toml[
                int(fastq_read["channel"])
            ]
        is_unblocked = fastq_read["read_id"] in run_dict[fastq_read["run_id"]].unblocked_dict
        fastq_read["rejected_barcode_name"] = "Unblocked" if is_unblocked else "Sequenced"
        # add control-treatment if passed as argument
        if args.treatment_control:
            is_control = int(fastq_read["channel"]) % args.treatment_control == 0
            suffix = " - control" if is_control else " - treatment"
            fastq_read["barcode_name"] = fastq_read["barcode_name"] + suffix
        # Add the read to the class dictionary to be uploaded, pretty important
        run_dict[fastq_read["run_id"]].add_read(fastq_read)
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
    minotour_api: minFQ.minotourapi.MinotourAPI
        The minotour API class instance for convenience request to the server
    sequencing_stats: minFQ.utils.SequencingStatistics
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
    payload = {
        "file_name": str(check_fastq_path(fastq_path)),
        "run_id": run_id,
        "md5": "0",
        "run": None
    }
    if run_id in run_dict:
        fastq_file = minotour_api.post(
            EndPoint.FASTQ_FILE, json=payload, base_id=run_id
        )
    counter = 0
    # fq = pyfastx.Fastq(fastq_path)
    # gen = (read for read in fq)
    # for read in gen:
    handle = gzip.open if fastq_path.endswith(".gz") else open
    with handle(fastq_path, "rt") as fh:
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
                        sequencing_stats,
                    )
                    fastq_file = minotour_api.post(
                        EndPoint.FASTQ_FILE, json=payload, base_id=run_id
                    )
                    run_dict[run_id].get_readnames_by_run(fastq_file["id"])
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
        payload = {
            "file_name": str(check_fastq_path(fastq_path)),
            "run_id": run_id,
            "md5": get_file_size(fastq_path),
            "run": run_dict[run_id].run,
        }
        fastq_file = minotour_api.put(EndPoint.FASTQ_FILE, json=payload, base_id=run_id)
    except Exception as err:
        log.error("Problem with uploading file {}".format(err))
    sequencing_stats.time_per_file = time.time()
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
        sequencing_statistic: minFQ.utils.SequencingStatistics
            The class for tracking files and metrics about the upload
        minotour_api: minFQ.minotourapi.MinotourAPI
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

    def addfolder(self, folder):
        self.fastq_files_to_create.update(
            unseen_files_in_watch_folder_dict(
                folder,
                self.args.ignore_existing,
                self.minotour_api,
                self.fastq_dict,
                self.sequencing_statistic,
            )
        )

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
            log.debug("still ticking")

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
