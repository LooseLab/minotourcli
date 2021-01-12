"""
A class to handle the collection of run statistics and information 
from fastq files and upload to minotour.
"""
import logging
import os
import sys

from minFQ.endpoints import EndPoint
from minFQ.minotourapi import MinotourAPI

import toml as toml_manager

log = logging.getLogger(__name__)


def get_flowcell_name_from_desc(description_dict, user_run_name):
    """
    Get the flowcell name from the description
    Parameters
    ----------
    description_dict: dict
        A parsed dictionary created from the description from the fastq record
    user_run_name: str
        The user run name that we have been given on the command line

    Returns
    -------
    flowcell_name: str
        The flowcell name that we are gonna be using
    """
    if "flow_cell_id" in description_dict:
        flowcell_name = description_dict["flow_cell_id"]
    elif "sample_id" in description_dict:
        flowcell_name = description_dict["sample_id"]
    elif "sampleid" in description_dict:
        flowcell_name = description_dict["sampleid"]
    else:
        flowcell_name = user_run_name
    return flowcell_name


def get_unique_name(description_dict, user_run_name):
    """

    Parameters
    ----------
    description_dict: dict
        A parsed dictionary created from the description from the fastq record
    user_run_name: str
        The user run name that we have been given on the command line
    Returns
    -------

    """
    flowcell_name = user_run_name
    if "flow_cell_id" in description_dict and "sample_id" in description_dict:
        flowcell_name = "{}_{}".format(
            description_dict["flow_cell_id"], description_dict["sample_id"]
        )
    elif "flow_cell_id" in description_dict and "sampleid" in description_dict:
        flowcell_name = "{}_{}".format(
            description_dict["flow_cell_id"], description_dict["sampleid"]
        )
    return flowcell_name


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


class RunDataTracker:
    def __init__(self, args, header, sequencing_statistics):
        log.debug("Initialising Runcollection")
        self.args = args
        self.header = header
        self.read_names = []
        self.read_count = 0
        self.base_count = 0
        self.tracked_base_count = 0
        self.read_type_dict = {}
        if self.args.skip_sequence:
            self.batchsize = 5000
        else:
            self.batchsize = 4000
        self.run = None
        self.flowcell = None
        self.barcode_dict = {}
        self.read_list = []
        self.file_monitor = {}
        self.fastq_file_id = None
        self.minotour_api = MinotourAPI(
            self.args.host_name, self.args.port_number, self.header
        )
        self.get_readtype_list()
        self.unblocked_dict = {}
        self.unblocked_file = None
        self.unblocked_line_start = 0
        self.run_folder = None
        self.toml = None
        self.sequencing_statistics = sequencing_statistics

    def add_toml_file(self, toml_file):
        self.toml = toml_file

    def add_run_folder(self, folder):
        """
        Adds the folder directory for this run.
        Parameters
        ----------
        folder: str
            Path to folder that run is being written into

        Returns
        -------

        """
        self.run_folder = folder
        self.check_for_read_until_files()

    def add_unblocked_reads_file(self, unblocked_file_path):
        self.unblocked_file = unblocked_file_path

    def create_jobs(self, flowcell, args):
        """
        Create jobs when runCollection is initialised
        Returns
        -------

        """
        payload = {
            "flowcell": flowcell["id"],
            "job_type": args.job,
            "reference": args.reference,
            "target_set": args.targets,
            "cli": True,
            "api_key": args.api_key
        }
        self.minotour_api.post(
            EndPoint.JOBS,
            json=payload
        )

    def get_readtype_list(self):
        """
        Get a list of possible read types from minotour server
        Returns
        -------
        None
        """
        # fix me manual get
        read_type_list = self.minotour_api.get_json(EndPoint.READ_TYPES)
        self.read_type_dict = {read_type["name"]: read_type["id"] for read_type in read_type_list}

    def get_readnames_by_run(self, fastq_file_id):
        """
        Get read ids for the last uncomplete file we have in a run
        Parameters
        ----------
        fastq_file_id: int
            The id of the fastq file

        Returns
        -------

        """
        if fastq_file_id != self.fastq_file_id:
            self.fastq_file_id = fastq_file_id
            read_name_list = self.minotour_api.get_json(EndPoint.READ_NAMES, base_id=fastq_file_id)
            number_pages = read_name_list["number_pages"]
            log.debug("Fetching reads to check if we've uploaded these before.")
            log.debug("Wiping previous reads seen.")
            self.read_names = []
            for page in range(number_pages):
                self.sequencing_statistics.fastq_message = "Fetching {} of {} pages.".format(
                    page, number_pages
                )
                page_query = "?page={}".format(page)
                partial_file_content = self.minotour_api.get_json(EndPoint.READ_NAMES, base_id=fastq_file_id, params=page_query)
                # We have to recover the data component and loop through that to get the read names.
                for read in partial_file_content["data"]:
                    self.read_names.append(read)
            log.debug(
                "{} reads already processed and included into readnames list for run {}".format(
                    len(self.read_names), self.run["id"]
                )
            )

    def add_run(self, description_dict, args):
        """
        Add run to the minoTOur server
        Parameters
        ----------
        description_dict: dict
            Dictionary of a fastq read description
        args: argparse.NameSpace
            The namespace of the arguments on the CLI

        Returns
        -------

        """
        self.sequencing_statistics.fastq_message = "Adding run."
        run_id = description_dict["runid"]
        run = self.minotour_api.get_json(EndPoint.RUNS, base_id=run_id, params="search_criteria=runid")
        flowcell_name = get_flowcell_name_from_desc(description_dict, self.args.run_name_manual)
        if args.force_unique:
            flowcell_name = get_unique_name(description_dict, self.args.run_name_manual)
        if not flowcell_name:
            self.sequencing_statistics.errored = True
            self.sequencing_statistics.error_message = "Flowcell name is required. This may be old FASTQ data, please provide a name with -n."
            sys.exit("Flowcell name is required. This may be old FASTQ data, please provide a name with -n.")
        flowcell = self.minotour_api.get_json(EndPoint.FLOWCELL, base_id=flowcell_name,
                                              params="search_criteria=name")["data"]
        if not flowcell:
            flowcell = self.minotour_api.post(EndPoint.FLOWCELL, no_id=True, json={"name": flowcell_name})
        self.flowcell = flowcell

        if not run:
            # get or create a flowcell
            log.info("Looking for flowcell {}".format(flowcell_name))
            log.debug(flowcell)
            is_barcoded = True if "barcode" in description_dict.keys() else False
            has_fastq = False if self.args.skip_sequence else True
            key = "sample_id" if "sample_id" in description_dict else "sampleid"
            run_name = description_dict[key] if key in description_dict else self.args.run_name_manual
            payload = {
                "name": run_name,
                "sample_name": run_name,
                "runid": run_id,
                # TODO is this okay??
                "is_barcoded": is_barcoded,
                "has_fastq": has_fastq,
                "flowcell": flowcell["url"],
            }
            created_run = self.minotour_api.post(
                EndPoint.RUNS, no_id=True, json=payload
            )
            if not created_run:
                log.critical("There is a problem creating run")
                sys.exit()
            else:
                log.debug("run created")
            run = created_run

        if args.job:
            self.create_jobs(flowcell, args)
        if not self.run:
            self.run = run
        for item in run["barcodes"]:
            self.barcode_dict.update({item["name"]: item["id"]})

    def commit_reads(self):
        """
        Call create reads - which posts a batch of reads to the server.
        Returns
        -------
        None
        """
        if self.read_list:
            self.minotour_api.post(EndPoint.READS, json=self.read_list)
        self.sequencing_statistics.reads_uploaded += len(self.read_list)
        # Refresh the read list
        self.read_list = []

    def update_read_type(self, read_id, type):
        """
        Update read type for complement read from default of template if we have a 1d^2 run
        Parameters
        ----------
        read_id: str
            UUid read id for this complement read
        type: str
            Complement read type (default "C")

        Returns
        -------

        """
        # payload = {"type": type}
        # # TODO check request usage
        # updateread = requests.patch(
        #     self.args.full_host
        #     + "api/v1/runs/"
        #     + str(self.runid)
        #     + "/reads/"
        #     + str(read_id)
        #     + "/",
        #     headers=self.header,
        #     json=payload,
        # )
        for _ in range(3):
            log.error("HELP - 1D^2 not supported, contact @mattloose on twitter")

    def check_1d2(self, read_id):
        """
        Check if the read is 1d&2 by checking the length of the read_id uuid
        Parameters
        ----------
        read_id: str
            The read id to update
        Returns
        -------
        bool
            True if read is 1d^2
        """
        if len(read_id) > 64:
            return True
        return False

    def add_read(self, fastq_read_payload):
        """
        Add a read to to the readnames list that we will commit to the minoTour server
        Create any non present barcodes on the minoTour server
        Parameters
        ----------
        fastq_read_payload: dict
            The fastq read dictionary that will be added to the upload list

        Returns
        -------
        None
        """
        barcode_name = fastq_read_payload["barcode_name"]
        rejected_barcode_name = fastq_read_payload["rejected_barcode_name"]
        run_id = fastq_read_payload["run_id"]
        read_id = fastq_read_payload["read_id"]
        fastq_read_payload["run"] = self.run["id"]
        # Here we are going to create the sequenced/unblocked barcodes and read barcode
        for barcode_name in [barcode_name, rejected_barcode_name]:
            if barcode_name not in self.barcode_dict:
                barcode = self.minotour_api.post(EndPoint.BARCODE, json={"name": barcode_name, "run": self.run["url"]})
                if barcode:
                    self.barcode_dict.update({barcode["name"]: barcode["id"]})
                else:
                    log.critical("Problem finding barcodes.")
                    sys.exit()

        fastq_read_payload["barcode"] = self.barcode_dict[
            fastq_read_payload["barcode_name"]
        ]
        fastq_read_payload["rejected_barcode"] = self.barcode_dict[
            fastq_read_payload["rejected_barcode_name"]
        ]
        if read_id not in self.read_names:
            if self.check_1d2(read_id):
                firstread, secondread = (
                    read_id[: len(read_id) // 2],
                    read_id[len(read_id) // 2 :],
                )
                self.update_read_type(secondread, self.read_type_dict["C"])
                fastq_read_payload["type"] = self.read_type_dict["1D^2"]
            else:
                fastq_read_payload["type"] = self.read_type_dict["T"]
            self.read_names.append(read_id)
            self.base_count += fastq_read_payload["sequence_length"]
            self.tracked_base_count += fastq_read_payload["sequence_length"]
            self.read_list.append(fastq_read_payload)
            log.debug(
                "Checking read_list size {} - {}".format(
                    len(self.read_list), self.batchsize
                )
            )
            # if we have a number of reads more than our batch size
            if len(self.read_list) >= self.batchsize:
                # aiming for yield of 100 Mb in number of reads
                log.debug("Commit reads")
                if not self.args.skip_sequence:
                    self.batchsize = int(
                        1000000 / (int(self.base_count) / self.read_count)
                    )
                self.commit_reads()
            elif self.tracked_base_count >= 1000000:
                self.commit_reads()
                self.tracked_base_count = 0
            self.read_count += 1
        else:
            print("Skipping read")
            self.args.reads_skipped += 1

    def check_for_read_until_files(self):
        """
        Check run folder for a channels.toml and an unblocked read_ids file when a run folder is set in the run collection
        Returns
        -------

        """
        log.debug("Checking for Toml")
        if self.toml is None or self.unblocked_file:
            for path, dirs, files in os.walk(self.run_folder):
                for file in files:
                    if file.endswith("channels.toml"):
                        if self.toml is None:
                            toml_dict = toml_manager.load(os.path.join(path, file))
                            self.toml = _prepare_toml(toml_dict)
                    if file == "unblocked_read_ids.txt":
                        if self.unblocked_file is None:
                            self.add_unblocked_reads_file(os.path.join(path, file))
