"""
A class to handle the collection of run statistics and information 
from fastq files and upload to minotour.
"""
import datetime
import json
import logging
import os
import sys, time

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from minFQ.minotourapi import MinotourAPI

from urllib.parse import urlparse
from threading import Thread
import toml as toml_manager

log = logging.getLogger(__name__)

# https://www.peterbe.com/plog/best-practice-with-retries-with-requests
def requests_retry_session(
    retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None,
):

    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


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
        self.base_url = args.host_name
        self.port_number = args.port_number
        self.check_url()
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
        # If there is a target set
        if args.targets is not None:
            self.minotour_api.create_job(
                flowcell["id"], int(args.job_id), None, args.targets
            )
        # If there is a reference and not a target set
        elif args.reference and not args.targets:
            self.minotour_api.create_job(
                flowcell["id"], int(args.job_id), args.reference, None
            )
        # If there is neither
        else:
            self.minotour_api.create_job(
                flowcell["id"], int(args.job_id), None, None
            )

    def check_url(self):
        if self.base_url.startswith("http://"):
            self.base_url = self.base_url[7:]
        if self.base_url.startswith(("https://")):
            self.base_url = self.base_url[8:]
        if int(self.port_number) != 80:
            r = requests.get("http://{}:{}/".format(self.base_url, self.port_number))
        else:
            r = requests.get("http://{}/".format(self.base_url))
        # print (r.url)
        if r.url.startswith("https"):
            self.base_url = "https://{}/".format(self.base_url)
        else:
            self.base_url = "http://{}:{}/".format(self.base_url, self.port_number)

    def get_readtype_list(self):
        """
        Get a list of possible read types from minotour server
        Returns
        -------
        """
        # fix me manual get
        read_type_list = self.minotour_api.get_read_type_list()
        read_type_dict = {}
        for read_type in read_type_list:
            read_type_dict[read_type["name"]] = read_type["id"]
        self.read_type_dict = read_type_dict

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
            # TODO move this function to MinotourAPI class.

            # url = "{}api/v1/runs/{}/readnames/".format(self.base_url, self.run['id'])
            url = "{}api/v1/runs/{}/readnames/".format(self.base_url, fastq_file_id)
            req = requests.get(url, headers=self.header)
            read_name_list = json.loads(req.text)
            number_pages = read_name_list["number_pages"]

            log.debug("Fetching reads to check if we've uploaded these before.")
            log.debug("Wiping previous reads seen.")
            self.read_names = []
            for page in range(number_pages):
                self.sequencing_statistics.fastq_message = "Fetching {} of {} pages.".format(
                    page, number_pages
                )
                new_url = url + "?page={}".format(page)
                content = requests.get(new_url, headers=self.header)
                log.debug("Requesting {}".format(new_url))
                # We have to recover the data component and loop through that to get the read names.
                for read in json.loads(content.text)["data"]:
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
        run = self.minotour_api.get_run_by_runid(run_id)
        if "flow_cell_id" in description_dict:
            flowcell_name = description_dict["flow_cell_id"]
        elif "sample_id" in description_dict:
            flowcell_name = description_dict["sample_id"]
        elif "sampleid" in description_dict:
            flowcell_name = description_dict["sampleid"]
        else:
            flowcell_name = self.args.run_name
        if args.force_unique:
            if "flow_cell_id" in description_dict and "sample_id" in description_dict:
                flowcell_name = "{}_{}".format(
                    description_dict["flow_cell_id"], description_dict["sample_id"]
                )
        if not flowcell_name:
            self.sequencing_statistics.errored = True
            self.sequencing_statistics.error_message = "Flowcell name is required. This may be old FASTQ data, please provide a name with -n."
            sys.exit("Flowcell name is required. This may be old FASTQ data, please provide a name with -n.")
        # fixme manual get
        flowcell = self.minotour_api.get_flowcell_by_name(flowcell_name)["data"]

        if not run:
            # get or create a flowcell
            log.info("Looking for flowcell {}".format(flowcell_name))
            log.debug(flowcell)
            if not flowcell:
                log.debug("Trying to create flowcell {}".format(flowcell_name))
                # fixme manual post
                flowcell = self.minotour_api.create_flowcell(flowcell_name)
                # If we have a job as an option
                log.debug("Created flowcell {}".format(flowcell_name))
            is_barcoded = True if "barcode" in description_dict.keys() else False
            has_fastq = False if self.args.skip_sequence else True
            key = "sample_id" if "sample_id" in description_dict else "sampleid"
            run_name = description_dict[key] if key in description_dict  else self.args.run_name
            # fixme manual post
            created_run = self.minotour_api.create_run(
                run_name, run_id, is_barcoded, has_fastq, flowcell
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
        # print(self.read_list)
        self.minotour_api.create_reads(self.read_list)
        # Throttle to limit rate of upload.
        time.sleep(0.5)
        self.sequencing_statistics.reads_uploaded += len(self.read_list)
        # Refresh the read list
        self.read_list = []

    def update_read_type(self, read_id, type):
        payload = {"type": type}
        updateread = requests.patch(
            self.args.full_host
            + "api/v1/runs/"
            + str(self.runid)
            + "/reads/"
            + str(read_id)
            + "/",
            headers=self.header,
            json=payload,
        )

    def check_1d2(self, readid):
        if len(readid) > 64:
            return True

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
        run_id = fastq_read_payload["runid"]
        read_id = fastq_read_payload["read_id"]
        fastq_read_payload["run"] = self.run["id"]
        # Here we are going to create the sequenced/unblocked barcodes and read barcode
        for barcode_name in [barcode_name, rejected_barcode_name]:
            if barcode_name not in self.barcode_dict:
                barcode = self.minotour_api.create_barcode(barcode_name, self.run["url"])
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
