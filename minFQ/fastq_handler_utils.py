import gzip
import logging
import os
import sys

import numpy as np
from minFQ.fastq_handler import OpenLine
import toml as toml_manager
from minFQ.run_collection import Runcollection

log = logging.getLogger("fastq_handler")

###Function modified from https://raw.githubusercontent.com/lh3/readfq/master/readfq.py


# todo switch with pyfastx
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
    """
    Check if a folder contains pass or fail reads
    Parameters
    ----------
    path: str
        Path to folder to check
    avg_quality: int
        Avergae quality of reads in the folder
    Returns
    -------
    bool
    """
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
    description_dict = {}
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


def unblocked_reads_functions():
    pass


# def add_channels_dict_to_run_collection(run_dict, run_id):
#     """
#     Take the path to a toml file, parse it and add it to our run collection
#     Returns
#     -------
#     None
#     """
#     if run_dict[run_id].toml is None:
#         toml_file_path = os.path.join(run_dict[run_id].run_folder, "channels.toml")
#         ## Look and see if a toml file exists in the run folder.
#         if os.path.exists(
#             toml_file_path
#         ):
#             try:
#                 toml_dict = toml_manager.load(
#                     toml_file_path
#                 )
#                 toml_dict = _prepare_toml(toml_dict)
#             except FileNotFoundError as e:
#                 log.error(
#                     "Error, toml file not found. Please check that it hasn't been moved."
#                 )
#                 sys.exit(2)
#             run_dict[run_id].add_toml_file(toml_dict)


def get_channel_toml_as_dict(toml_path, run_dict, run_id):
    """
    Get a toml dictionary
    Parameters
    ----------
    toml_path: str
        The string path to the toml file that contains channel conditions
    run_dict: dict of minFQ.run_collection.RunCollection
        A dictionary of run_id to minFQ.
    run_id: str
        The uuid assigned to this run
    Returns
    -------

    """
    try:
        toml_dict = toml_manager.load(toml_path)
        toml_dict = _prepare_toml(toml_dict)
    except FileNotFoundError as e:
        sys.exit("Error, toml file not found at {}. Please check that it hasn't been moved.".format(toml_path))
    run_dict[run_id].add_toml_file(toml_dict)


def add_read_to_run_dict(fastq_read, quality, run_tracker_dict, sequence, args, description_dict, fastq_file_path):
    """
    Add a read to the RunCollection class
    Parameters
    ----------
    fastq_read: dict
        A dictionary representing a Fastq read, to be added to the RunCOllection class
    quality: str
        The quality of the fastq read
    run_tracker_dict: dict
        Dict of RunCollections keyed to runId
    sequence: str
        The sequence of the read itself
    args: argparse.Namespace
        Parsed command line arguments
    description_dict: dict

    fastq_file_path

    Returns
    -------

    """
    if quality is not None:
        fastq_read["quality_average"] = round(average_quality(quality), 2, )
    fastq_read["is_pass"] = check_is_pass(fastq_file_path, fastq_read["quality_average"])
    # use 'No barcode' for non-barcoded reads
    barcode_name = description_dict.get("barcode", None)
    fastq_read["barcode_name"] = barcode_name if barcode_name else "No barcode"
    # todo here is some toml stuff
    if run_tracker_dict[fastq_read["runid"]].toml is not None:
        fastq_read["barcode_name"] = run_tracker_dict[fastq_read["runid"]].toml[
            int(fastq_read["channel"])
        ]
    if (
            run_tracker_dict[fastq_read["runid"]].unblocked_dict
            and fastq_read["read_id"] in run_tracker_dict[fastq_read["runid"]].unblocked_dict
    ):
        fastq_read["rejected_barcode_name"] = "Unblocked"
    else:
        fastq_read["rejected_barcode_name"] = "Sequenced"

    # add control-treatment if passed as argument
    if args.treatment_control:
        suffix = " - control" if int(fastq_read["channel"]) % args.treatment_control == 0 else " - treatment"
        fastq_read["barcode_name"] = fastq_read["barcode_name"] + suffix
        # check if sequence is sent or not
    fastq_read["sequence"] = "" if args.skip_sequence else str(sequence)
    fastq_read["quality"] = "" if args.skip_sequence else quality
    run_tracker_dict[fastq_read["runid"]].add_read(fastq_read)


def parse_fastq_record(
    desc, name, seq, qual, fastq_file_path, run_tracker_dict, args, header, fastq_file, counter, upload_data
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
    :param fastq_file_path: File path to the fastq file
    :type fastq_file_path: str
    :param run_tracker_dict: A dictionary storing runIDs
    :type run_tracker_dict: dict
    :param args: The command line arguments passed to minFQ
    :param header: The security header for minoTour
    :type header: dict
    :param fastq_file: The information on the fastq file that we have placed into minoTour
    :param counter: Tells us which read in the file this is
    :type counter: int
    :return:
    """
    log.debug("Parsing reads from file {}".format(fastq_file_path))
    description_dict = parse_fastq_description(desc)
    fastq_read = {
        "read": description_dict.get("read", None),
        "runid": description_dict.get("runid", None),
        "channel": description_dict.get("ch", None),
        "start_time": description_dict.get("start_time", None),
        "read_id": name,
        "sequence_length": len(str(seq)),
        "fastqfile": fastq_file["id"]
    }
    # get or create fastfile if not in dictionary?
    # We want to add the toml file to the rundict in some way.
    if fastq_read["runid"] not in run_tracker_dict:
        ### We haven't seen this run before - so we need to check stuff.
        run_tracker_dict[fastq_read["runid"]] = Runcollection(args, header)
        run_tracker_dict[fastq_read["runid"]].add_run(description_dict, args)
        run_tracker_dict[fastq_read["runid"]].get_read_names_by_run(fastq_file["id"])

        # We need to get the toml dict here.
        ## This is going to need refactoring...


        ### Check the overlap between the current file path and the folders being watched:
        for folder in args.WATCHLIST:
            if folder is not None:
                if fastq_file_path.startswith(folder):
                    ## We have found the folder that this fastq file comes from.
                    run_tracker_dict[fastq_read["runid"]].add_run_folder(folder)

        ### Check for unblocked read files

        if args.unblocks is not None:
            run_tracker_dict[fastq_read["runid"]].unblocked_file = args.unblocks

    if run_tracker_dict[fastq_read["runid"]].unblocked_file is None:
        path_to_unblocks_txt = os.path.join(
                run_tracker_dict[fastq_read["runid"]].run_folder, "unblocked_read_ids.txt"
            )
        if os.path.exists(path_to_unblocks_txt):
            run_tracker_dict[fastq_read["runid"]].unblocked_file = path_to_unblocks_txt



    if counter <= 1:
        ## This is the first read we have seen from this file - so we are going to check for updates in the unblocked read file.
        if run_tracker_dict[fastq_read["runid"]].unblocked_file is not None:
            # print ("reading in the unblocks")
            with OpenLine(
                run_tracker_dict[fastq_read["runid"]].unblocked_file,
                run_tracker_dict[fastq_read["runid"]].unblocked_line_start,
            ) as fh:
                _d = {line: 1 for line in fh}
                lines_returned = len(_d)
                run_tracker_dict[fastq_read["runid"]].unblocked_dict.update(_d)
            run_tracker_dict[fastq_read["runid"]].unblocked_line_start += lines_returned
    # todo seperate function here
    if fastq_read["read_id"] not in run_tracker_dict[fastq_read["runid"]].readnames:
        return fastq_read
    else:
        upload_data.reads_skipped += 1


def average_quality(quality):
    """
    Get average quality of read
    Parameters
    ----------
    quality: str
        The quality string of a fast q read
    Returns
    -------

    """
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
            line = file.readline()

    else:
        with open(fastq, "r") as file:
            line = file.readline()

    for _ in line.split():
        if _.startswith("runid"):
            # print (_.split("=")[1])
            runid = _.split("=")[1]
    return runid


def parse_fastq_file(fastq, rundict, args, header, MinotourConnection, upload_data):
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
    payload = {
        "name": str(check_fastq_path(fastq)),
        "runid": runid,
        "md5": "0",
        "run": None,
    }
    response, fastqfile = MinotourConnection.post(
        "/runs/{}/files/".format(runid), json=payload
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
    handler = (gzip.open, "rt") if fastq.endswith(".gz") else (open, "r")
    with handler[0](fastq, handler[1]) as fp:
        try:
            for desc, name, seq, qual in readfq(fp):
                counter += 1
                upload_data.reads_seen += 1
                upload_data.fastq_message = "processing read {}".format(counter)
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
                    upload_data
                )
        except Exception as e:
            upload_data.reads_corrupt += 1
            log.error(e)
            log.error("This gzipped file failed to upload - {}.".format(fastq))
    for runs in rundict:
        rundict[runs].readnames = []
        rundict[runs].commit_reads()
    try:
        payload = {
            "name": str(check_fastq_path(fastq)),
            "runid": runid,
            "md5": md5Checksum(fastq),
            "run": rundict[runid].run,
        }
        response, fastqfile = MinotourConnection.post(
            "/runs/{}/files/".format(runid), json=payload
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

            args.fastq_message = "caching existing fastq files in: %s" % (path)

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

                            req, result = MinotourConnection.get(
                                "/runs/{}/files/".format(runid)
                            )
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

        args.fastq_message = "processed %s files" % (counter)

        log.info(
            "found %d existing fastq files to process first." % (len(file_list_dict))
        )

    else:
        args.fastq_message = "Ignoring existing fastq files in: %s" % (path)

    return file_list_dict