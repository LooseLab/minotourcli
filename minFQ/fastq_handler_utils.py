import gzip
import logging
import os
from pathlib import Path

import numpy as np

from minFQ.endpoints import EndPoint
from minFQ.run_data_tracker import RunDataTracker

log = logging.getLogger("fastq_handler")
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


def get_file_size(file_path):
    """
    Returns the size of the filepath in bytes.
    :param filePath: The path to file in the watch directory
    :return:
    """
    return os.path.getsize(file_path)


def split_all(path):
    """
    Split the path into it's relative parts so we can check all the way down the tree
    :param path: Path provided by the user to the watch directory
    :return: A list of paths created from the base path, so we can use relative and absolute paths
    """
    all_parts = []
    while 1:
        parts = os.path.split(path)

        if parts[0] == path:  # sentinel for absolute paths
            all_parts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            all_parts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            all_parts.insert(0, parts[1])
    return all_parts


def check_fastq_path(path):
    """
    Check if the files we are looking at are directly inside pass or fail folders, or one or two removed.
    :param path:
    :return:
    """
    folders_in_path = split_all(path)
    try:
        if folders_in_path[-2] in ("pass", "fail"):
            return "{}_{}".format(folders_in_path[-2], folders_in_path[-1])
        elif folders_in_path[-3] in ("pass", "fail"):
            return "{}_{}_{}".format(folders_in_path[-3], folders_in_path[-2], folders_in_path[-1])
        else:
            return "{}".format(folders_in_path[-1])
    except Exception as e:
        return "{}".format(folders_in_path[-1])


def check_is_pass(path, avg_quality):
    """
    Check that the fastq file is contains pass or fail reads
    Parameters
    ----------
    path
    avg_quality

    Returns
    -------

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
    for item in descriptors:
        if "=" in item:
            bits = item.split("=")
            description_dict[bits[0]] = bits[1]
    return description_dict


def _prepare_toml(toml_dict):
    """
    Prepares the dictionary of the toml, places the channel number as key and conditon name as value
    Returns
    -------
    dict
    """
    _d = {}
    # Reverse the dict so we can lookup name by channel
    for key in toml_dict["conditions"].keys():
        channels = toml_dict["conditions"][key]["channels"]
        name = toml_dict["conditions"][key]["name"]
        _d.update({channel: name for channel in channels})
    return _d


def average_quality(quality):
    """
    Return the average quality of a read from it's quality string
    Parameters
    ----------
    quality: str

    Returns
    -------
    float
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
            for _ in range(1):
                line = file.readline()
    else:
        with open(fastq, "r") as file:
            for _ in range(1):
                line = file.readline()
    for _ in line.split():
        if _.startswith("runid"):
            runid = _.split("=")[1]
    return runid


def unseen_files_in_watch_folder_dict(path, ignore_existing, minotour_api, fastq_dict, sequencing_statistics):
    """
    Iterate fastq files in watch directory and see if we have seen them before by checking against server.
    Parameters
    ----------
    path: str
        File path to watch directory
    ignore_existing: bool
        Ignore existing fastq folders in the direcotur
    minotour_api: minFQ.minotourapi.MinotourAPI
        The minotour api
    fastq_dict: dict
        Dictionary containing all the fastq files that we have seen.
    sequencing_statistics: minFQ.utils.SequencingStatistics
        Tracker for files in watch list and uplaod metrics

    Returns
    -------
    dict
        Dictionary of fastq files that we haven't seen before. Key filepath, value created time for fastq file

    """
    # Dictionary for tracking files
    new_fastq_file_dict = {}
    if not ignore_existing:
        counter = 0
        # if directory
        if os.path.isdir(path):
            log.info("caching existing fastq files in: {}".format(path))
            sequencing_statistics.fastq_message = "caching existing fastq files in: {}".format(path)
            ## ToDo Consider moving these to top level
            novel_run_set = set()
            seen_file_tracker = {}
            file_endings = {".fq", ".fastq", ".fq.gz", ".fastq.gz"}
            # have s rummage around the watch directory
            for path, dirs, files in os.walk(path):
                # iterate fastq files in the watchdir
                for f in files:
                    if "".join(Path(f).suffixes) in file_endings:
                        log.debug("Processing File {}\r".format(f))
                        counter += 1
                        sequencing_statistics.files_seen += 1
                        #### Here is where we want to check if the files have been created and what the checksums are
                        #### If the file checksums do not match, we pass the file to the rest of the script.
                        #### When we finish analysing a file, we will need to update this information n the server.
                        #### Currently just using size.
                        file_byte_size = get_file_size(os.path.join(path, f))
                        run_id = get_runid(os.path.join(path, f))
                        if (
                            run_id not in novel_run_set
                            and run_id not in seen_file_tracker.keys()
                        ):
                            # get all files for this run
                            result = minotour_api.get_json(EndPoint.FASTQ_FILE, base_id=run_id)
                            #### Here we want to parse through the results and store them in some kind of dictionary in order that we can check what is happening
                            # We are parsing through the fastq files we have seen for this run so we don't reprocess them
                            if result is not None:
                                for entry in result:
                                    if entry["runid"] not in seen_file_tracker.keys():
                                        seen_file_tracker[entry["runid"]] = {}
                                    seen_file_tracker[entry["runid"]][
                                        entry["name"]
                                    ] = entry["md5"]
                        # add the file path
                        filepath = os.path.join(path, f)
                        check_file_path = check_fastq_path(filepath)
                        if check_file_path not in fastq_dict.keys():
                            fastq_dict[check_file_path] = {}
                        fastq_dict[check_file_path]["runid"] = run_id
                        fastq_dict[check_file_path]["md5"] = file_byte_size
                        """Here we are going to check if the files match or not. """
                        seen_file = False
                        if (
                            run_id in seen_file_tracker.keys()
                            and check_file_path in seen_file_tracker[run_id]
                        ):
                            seen_file = True
                            ## if the file hasn't changed size, we can skip it
                            if int(file_byte_size) == int(
                                seen_file_tracker[run_id][check_file_path]
                            ):
                                sequencing_statistics.files_skipped += 1
                            else:
                                new_fastq_file_dict[filepath] = os.stat(filepath).st_mtime
                                novel_run_set.add(run_id)

                        if not seen_file:
                            # never seen this file before
                            new_fastq_file_dict[filepath] = os.stat(filepath).st_mtime
                            novel_run_set.add(run_id)
        log.info("processed {} files".format(counter))
        sequencing_statistics.fastq_message = "processed {} files".format(counter)
        log.info(
            "found {} existing fastq files to process first.".format(
                len(new_fastq_file_dict)
            )
        )
    else:
        sequencing_statistics.fastq_message = "Ignoring existing fastq files in: {}".format(path)
    return new_fastq_file_dict


def create_run_collection(run_id, run_dict, args, header, description_dict, sequencing_statistics):
    """
    Create run collection for this run id if we don't already have one, store in run_dict
    Parameters
    ----------
    run_id: str
        The uuid of this run
    run_dict: dict
        The dictionary containing run collections
    args: argparse.NameSpace
        The command line arguments
    header: dict
        Authenticator for request
    description_dict: dict
        The description dict
    sequencing_statistics: SequencingStatistics
        Class to communicate sequencing statistics
    Returns
    -------

    """
    run_dict[run_id] = RunDataTracker(args, header, sequencing_statistics)
    run_dict[run_id].add_run(description_dict, args)

