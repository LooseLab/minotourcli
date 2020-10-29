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
import toml as toml_manager
from minFQ.minotourapiclient import Runcollection
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


###Function modified from https://raw.githubusercontent.com/lh3/readfq/master/readfq.py


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


def md5Checksum(filePath):
    """
    Returns the size of the filepath in bytes.
    :param filePath: The path to file in the watch directory
    :return:
    """
    return os.path.getsize(filePath)


def check_fastq_path(path):
    """
    Check if the folders we are looking at are pass or fail files
    :param path:
    :return:
    """
    folders = splitall(path)

    try:
        if folders[-2] in ("pass", "fail"):

            return "{}_{}".format(folders[-2], folders[-1])

        elif folders[-3] in ("pass", "fail"):

            return "{}_{}_{}".format(folders[-3], folders[-2], folders[-1])
        else:

            return "{}".format(folders[-1])

    except Exception as e:

        return "{}".format(folders[-1])


def splitall(path):
    """
    Split the path into it's relative parts so we can check all the way down the tree
    :param path: Path provided by the user to the watch directory
    :return: A list of paths created from the base path, so we can use relative and absolute paths
    """
    allparts = []
    while 1:
        parts = os.path.split(path)

        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def check_is_pass(path, avg_quality):

    folders = os.path.split(path)

    if "pass" in folders[0]:

        return True

    elif "fail" in folders[0]:

        return False

    else:
        if avg_quality != None:

            if avg_quality >= 7:

                return True  # This assumes we have been unable to find either pass
                # or fail and thus we assume the run is a pass run.

            else:

                return False

        else:

            return True


def parse_fastq_description(description):
    """
    Parse the description found in a fastq reads header

    Parameters
    ----------
    description: str
        A string of the fastq reads description header

    Returns
    -------
    description_dict: dict
        A dictionary containing the keys and values found in the fastq read headers
    """
    description_dict = dict()

    descriptors = description.split(" ")
    # Delete symbol for header
    del descriptors[0]

    for item in descriptors:
        bits = item.split("=")
        description_dict[bits[0]] = bits[1]

    return description_dict


def _prepare_toml(toml_dict):
    """
    Prepares the dictionary of the toml, places the channel number as key and conditon name as value
    Returns
    -------
    None
    """
    _d = {}
    # Reverse the dict so we can lookup name by channel
    for key in toml_dict["conditions"].keys():
        channels = toml_dict["conditions"][key]["channels"]
        name = toml_dict["conditions"][key]["name"]
        _d.update({channel: name for channel in channels})
    return _d


def parse_fastq_record(
    desc, name, seq, qual, fastq, rundict, args, header, fastqfile, counter
):
    """
    Parse a single fastq entry for a read
    :param desc: The full header of the read
    :type desc: str
    :param name: The Read ID
    :type name: str
    :param seq: The sequence of the read
    :type seq: str`
    :param qual: The quality string
    :type qual: str
    :param fastq: File path to the fastq file
    :type fastq: str
    :param rundict: A dictionary storing runIDs
    :type rundict: dict
    :param args: The command line arguments passed to minFQ
    :param header: The security header for minoTour
    :type header: dict
    :param fastqfile: The information on the fastq file that we have placed into minoTour
    :param counter: Tells us which read in the file this is
    :type counter: int
    :return:
    """
    log.debug("Parsing reads from file {}".format(fastq))

    fastq_read = {}

    description_dict = parse_fastq_description(desc)

    fastq_read["read"] = description_dict.get("read", None)

    fastq_read["runid"] = description_dict.get("runid", None)

    fastq_read["channel"] = description_dict.get("ch", None)

    fastq_read["start_time"] = description_dict.get("start_time", None)

    fastq_read["read_id"] = name

    fastq_read["sequence_length"] = len(str(seq))

    fastq_read["fastqfile"] = fastqfile["id"]

    # get or create fastfile if not in dictionary?

    # fastq_read['fastqfilename'] = fastqfileid

    # We want to add the toml file to the rundict in some way.

    if fastq_read["runid"] not in rundict:

        ### We haven't seen this run before - so we need to check stuff.

        rundict[fastq_read["runid"]] = Runcollection(args, header)

        rundict[fastq_read["runid"]].add_run(description_dict, args)

        rundict[fastq_read["runid"]].get_readnames_by_run(fastqfile["id"])

        # We need to get the toml dict here.
        ## This is going to need refactoring...
        if args.toml is not None:

            try:
                toml_dict = toml_manager.load(args.toml)
                toml_dict = _prepare_toml(toml_dict)

            except FileNotFoundError as e:
                log.error(
                    "Error, toml file not found. Please check that it hasn't been moved."
                )
                os._exit(2)

            rundict[fastq_read["runid"]].add_toml_file(toml_dict)

        ### Check the overlap between the current file path and the folders being watched:

        for folder in args.WATCHLIST:
            if folder is not None:
                if fastq.startswith(folder):
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
    if fastq_read["read_id"] not in rundict[fastq_read["runid"]].readnames:
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
        if args.skip_sequence:

            fastq_read["sequence"] = ""
            fastq_read["quality"] = ""

        else:

            fastq_read["sequence"] = str(seq)
            fastq_read["quality"] = qual
            # For speed lets throw away t12he quality
            # fastq_read["quality"] = ""
        # Add the read to the class dictionary to be uploaded, pretty important
        rundict[fastq_read["runid"]].add_read(fastq_read)

    else:
        args.reads_skipped += 1


def average_quality(quality):
    return -10 * np.log10(
        np.mean(
            10
            ** (
                np.array(
                    (-(np.array(list(quality.encode("utf8"))) - 33)) / 10, dtype=float
                )
            )
        )
    )


def get_runid(fastq):
    """
    Open a fastq file, read the first line and parse out the Run ID
    :param fastq: path to the fastq file to be parsed
    :type fastq: str
    :return runid: The run ID of this fastq file as a string
    """
    runid = ""
    if fastq.endswith(".gz"):
        with gzip.open(fastq, "rt") as file:
            for _ in range(1):
                line = file.readline()

    else:
        with open(fastq, "r") as file:
            for _ in range(1):
                line = file.readline()

    for _ in line.split():
        if _.startswith("runid"):
            # print (_.split("=")[1])
            runid = _.split("=")[1]

    return runid


def parse_fastq_file(fastq, rundict, fastqdict, args, header, MinotourConnection):
    """
    Parse a fastq file
    :param fastq: A path to a fastq file in the watch directory
    :type fastq: str
    :param rundict:  Dictionary of runs
    :type rundict: dict
    :param fastqdict: Dictionary of fastq files
    :type fastqdict: dict
    :param args: The
    :param header: The authorisation header for connecting to the minoTour client
    :type header: dict
    :param MinotourConnection: class for interacting with minoTour API
    :return counter: Number of lines of a fastqfile we have parsed
    :return unblocked_line_start: The updated number of lines we have already seen from the unblocked read ids file
    """
    log.debug("Parsing fastq file {}".format(fastq))
    # Get runId from the path
    runid = get_runid(fastq)

    fastqfile = MinotourConnection.create_file_info(
        str(check_fastq_path(fastq)), runid, "0", None
    )

    counter = 0

    #### We want to look see if we have a toml on the disk or in the args. If it is in the arguments it wil be applied to any file that doesn't have a toml associated with it.

    # if we don't have a unblocked ids file, we can still give the condition
    """
    if args.unblocks is not None:
        print ("reading in the unblocks")
        with OpenLine(args.unblocks, unblocked_line_start) as fh:
            _d = {line: 1 for line in fh}

            lines_returned = len(_d)

            unblocked_dict.update(_d)

        unblocked_line_start += lines_returned

        print (len(unblocked_dict))
    """
    if fastq.endswith(".gz"):

        with gzip.open(fastq, "rt") as fp:
            try:
                for desc, name, seq, qual in readfq(fp):
                    counter += 1

                    args.reads_seen += 1

                    args.fastqmessage = "processing read {}".format(counter)

                    parse_fastq_record(
                        desc,
                        name,
                        seq,
                        qual,
                        fastq,
                        rundict,
                        args,
                        header,
                        fastqfile,
                        counter,
                    )

            except Exception as e:
                args.reads_corrupt += 1
                log.error(e)
                log.error("This gzipped file failed to upload - {}.".format(fastq))
                raise Exception
                # continue

    else:

        with open(fastq, "r") as fp:
            try:
                # now = time.time()
                for desc, name, seq, qual in readfq(fp):

                    counter += 1

                    args.reads_seen += 1

                    args.fastqmessage = "processing read {}".format(counter)

                    parse_fastq_record(
                        desc,
                        name,
                        seq,
                        qual,
                        fastq,
                        rundict,
                        args,
                        header,
                        fastqfile,
                        counter,
                    )
                # print ("Taken {} to process one file.\n\n\n\n\n\n\n".format((time.time()-now)))

            except Exception as e:

                args.reads_corrupt += 1
                log.error(e)
                log.error(
                    "This uncompressed file failed to upload in {}.".format(fastq)
                )
                log.error(e)
                # continue

        # continue

    # This chunk of code will mean we commit reads every time we get a new file?

    for runs in rundict:
        rundict[runs].readnames = list()
        rundict[runs].commit_reads()

    try:
        fastqfile = MinotourConnection.create_file_info(
            str(check_fastq_path(fastq)), runid, md5Checksum(fastq), rundict[runid].run,
        )
    except Exception as err:
        log.error("Problem with uploading file {}".format(err))

    return counter


def file_dict_of_folder_simple(path, args, MinotourConnection, fastqdict):
    """
    I believe that this is a tracker for FastqFiles in the folder, and returns a list of files in the folder that we haven't seen
    :param path: Watch directory
    :param args: The args provided to minFQ
    :param MinotourConnection: The connection class that has methods for containing to the minoTour instance
    :param fastqdict: A dictionary of fastqfiles
    :return: file_list_dict
    """
    # Dictionary for tracking files
    file_list_dict = dict()

    if not args.ignoreexisting:

        counter = 0

        if os.path.isdir(path):

            log.info("caching existing fastq files in: %s" % (path))

            args.fastqmessage = "caching existing fastq files in: %s" % (path)

            ## ToDo Consider moving these to top level
            novelrunset = set()

            seenfiletracker = dict()

            for path, dirs, files in os.walk(path):

                for f in files:

                    if f.endswith(".fastq") or f.endswith(".fastq.gz"):
                        log.debug("Processing File {}\r".format(f))
                        counter += 1

                        args.files_seen += 1
                        #### Here is where we want to check if the files have been created and what the checksums are
                        #### If the file checksums do not match, we pass the file to the rest of the script.
                        #### When we finish analysing a file, we will need to update this information n the server.
                        #### Currently just using size.
                        md5Check = md5Checksum(os.path.join(path, f))

                        runid = get_runid(os.path.join(path, f))

                        if (
                            runid not in novelrunset
                            and runid not in seenfiletracker.keys()
                        ):

                            result = MinotourConnection.get_file_info_by_runid(runid)
                            #### Here we want to parse through the results and store them in some kind of dictionary in order that we can check what is happening
                            # We are parsing through the fastq files we have seen for this run so we don't reprocess them
                            if result is not None:
                                for entry in result:
                                    if entry["runid"] not in seenfiletracker.keys():
                                        seenfiletracker[entry["runid"]] = dict()
                                    seenfiletracker[entry["runid"]][
                                        entry["name"]
                                    ] = entry["md5"]
                        else:
                            result = None

                        filepath = os.path.join(path, f)

                        checkfilepath = check_fastq_path(filepath)

                        if checkfilepath not in fastqdict.keys():

                            fastqdict[checkfilepath] = dict()

                        fastqdict[checkfilepath]["runid"] = runid
                        fastqdict[checkfilepath]["md5"] = md5Check

                        """Here we are going to check if the files match or not. """
                        seenfile = False
                        if (
                            runid in seenfiletracker.keys()
                            and checkfilepath in seenfiletracker[runid].keys()
                        ):
                            seenfile = True
                            if int(md5Check) == int(
                                seenfiletracker[runid][checkfilepath]
                            ):
                                args.files_skipped += 1
                            else:
                                file_list_dict[filepath] = os.stat(filepath).st_mtime
                                novelrunset.add(runid)

                        if not seenfile:
                            file_list_dict[filepath] = os.stat(filepath).st_mtime
                            novelrunset.add(runid)

        log.info("processed %s files" % (counter))

        args.fastqmessage = "processed %s files" % (counter)

        log.info(
            "found %d existing fastq files to process first." % (len(file_list_dict))
        )

    else:
        args.fastqmessage = "Ignoring existing fastq files in: %s" % (path)

    return file_list_dict


class FastqHandler(FileSystemEventHandler):
    def __init__(self, args, header, rundict):
        """
        Collect information about files already in the folders
        """

        self.file_descriptor = dict()
        self.args = args
        self.header = header
        # adding files to the file_descriptor is really slow - therefore lets skip that and only update the files when we want to basecall thread_number
        self.MinotourConnection = MinotourAPI(
            self.args.host_name, self.args.port_number, self.header
        )
        self.rundict = rundict
        self.fastqdict = dict()
        # self.unblocked_read_ids_dict = {}
        # self.unblocked_line_start = 1
        self.toml_dict = {}

        self.creates = dict()
        self.processing = dict()
        self.running = True

        self.t = threading.Thread(target=self.processfiles)
        try:
            self.t.start()
        except Exception as e:
            self.running = False
            self.args.errored = True
            self.args.error_message = "Flowcell name is required. This may be old FASTQ data, please provide a name with -n."
            log.error("Flowcell name is required. This may be old FASTQ data, please provide a name with -n.")
            # raise BaseException()
        self.grouprun = None



    def addfolder(self, folder):
        self.creates.update(
            file_dict_of_folder_simple(
                folder, self.args, self.MinotourConnection, self.fastqdict,
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
        return len(self.creates)

    def lenprocessed(self):
        return len(self.processed)

    def processfiles(self):
        """
        Process fastq files in a threaded manner |
        :return:
        """
        while self.running:
            currenttime = time.time()

            for fastqfile, createtime in sorted(
                self.creates.items(), key=lambda x: x[1]
            ):
                delaytime = 10
                # file created 5 sec ago, so should be complete. For simulations we make the time longer.
                if int(createtime) + delaytime < time.time():
                    del self.creates[fastqfile]
                    c = parse_fastq_file(
                        fastqfile,
                        self.rundict,
                        self.fastqdict,
                        self.args,
                        self.header,
                        self.MinotourConnection,
                        # self.unblocked_read_ids_dict,
                        # self.unblocked_line_start
                    )
                    self.args.files_processed += 1
                    self.args.elapsed = time.time() - self.args.read_up_time
                    hours, remainder = divmod(self.args.elapsed, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    self.args.elapsed = '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))

                    self.args.read_up_time = time.time()

                if not self.running:
                    break

            if currenttime + 5 > time.time():
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
            self.args.files_seen += 1
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
