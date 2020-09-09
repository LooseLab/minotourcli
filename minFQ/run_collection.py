"""
A class to handle the collection of run statistics and information 
from fastq files and upload to minotour.
"""
import datetime
import json
import logging
import sys, time

import requests

from minFQ.minotourapi import MinotourAPI


log = logging.getLogger(__name__)


class Runcollection:
    def __init__(self, args, header, upload_data):
        log.debug("Initialising Runcollection")
        self.upload_data = upload_data
        self.base_url = args.host_name
        self.port_number = args.port_number
        self.check_url()
        self.args = args
        self.header = header
        self.readnames = []
        self.readcount = 0
        self.basecount = 0
        self.trackedbasecount = 0
        self.read_type_list = {}
        self.batch_size = 5000 if self.args.skip_sequence else 4000
        self.run = None
        self.grouprun = None
        self.barcode_dict = {}
        self.read_list = []
        self.filemonitor = {}
        self.fastq_file_id = None
        self.minotourapi = MinotourAPI(
            self.args.host_name, self.args.port_number, self.header
        )
        self.get_readtype_list()
        self.unblocked_dict = {}
        self.unblocked_file = None
        self.unblocked_line_start = 0
        self.run_folder = None
        self.toml = None

    def add_toml_file(self, toml_file):
        self.toml = toml_file

    def add_run_folder(self, folder):
        self.run_folder = folder

    def add_unblocked_reads_file(self, unblock_file):
        self.unblocked_file = unblock_file

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
        read_type_list = self.minotourapi.get_read_type_list()
        read_type_dict = {}
        for read_type in read_type_list:
            read_type_dict[read_type["name"]] = read_type["id"]
        self.read_type_list = read_type_dict

    def get_read_names_by_run(self, fastq_file_id):
        """
        # TODO check if this returns read names or fastq file names
        Parameters
        ----------
        fastq_file_id

        Returns
        -------

        """
        if fastq_file_id != self.fastq_file_id:
            self.fastq_file_id = fastq_file_id
            url = "{}api/v1/runs/{}/readnames/".format(self.base_url, fastq_file_id)
            # TODO use post request from minotourAPI class
            req = requests.get(url, headers=self.header)
            read_name_list = json.loads(req.text)
            number_pages = read_name_list["number_pages"]
            log.debug("Fetching reads to check if we've uploaded these before.")
            log.debug("Wiping previous reads seen.")
            self.readnames = []
            for page in range(number_pages):
                self.upload_data.fastq_message = "Fetching {} of {} pages.".format(
                    page, number_pages
                )
                new_url = url + "?page={}".format(page)
                # TODO use GET request from minotourAPI class
                content = requests.get(new_url, headers=self.header)
                log.debug("Requesting {}".format(new_url))
                # We have to recover the data component and loop through that to get the read names.
                for read in json.loads(content.text)["data"]:
                    self.readnames.append(read)
            log.debug(
                "{} reads already processed and included into readnames list for run {}".format(
                    len(self.readnames), self.run["id"]
                )
            )

    def add_run(self, description_dict, args):
        """
        
        Parameters
        ----------
        description_dict
        args

        Returns
        -------

        """
        self.upload_data.fastq_message = "Adding run."
        run_id = description_dict["runid"]
        run = self.minotourapi.get_run_by_runid(run_id)
        if not run:
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

            #
            # get or create a flowcell
            #
            log.info("Looking for flowcell {}".format(flowcell_name))
            # flowcell = self.minotourapi.get_flowcell_by_name(flowcellname)
            flowcell = self.minotourapi.get_flowcell_by_name(flowcell_name)["data"]
            # TODO get_or_create function
            log.debug(flowcell)
            if not flowcell:
                log.debug("Trying to create flowcell {}".format(flowcell_name))
                flowcell = self.minotourapi.create_flowcell(flowcell_name)
                # print(dir(args))
                # If we have a job as an option
                # TODO move to own function
                if args.job:
                    # If there is a target set
                    if args.targets is not None:
                        self.minotourapi.create_job(
                            flowcell["id"], int(args.job_id), None, args.targets
                        )
                    # If there is a reference and not a target set
                    elif args.reference and not args.targets:
                        self.minotourapi.create_job(
                            flowcell["id"], int(args.job_id), args.reference, None
                        )
                    # If there is neither
                    else:
                        self.minotourapi.create_job(
                            flowcell["id"], int(args.job_id), None, None
                        )
                log.debug("Created flowcell {}".format(flowcell_name))

            #
            # create a run
            #
            is_barcoded = True if "barcode" in description_dict.keys() else False
            has_fastq = False if self.args.skip_sequence else True
            run_name = (
                description_dict["sample_id"]
                if "sample_id" in description_dict
                else self.args.run_name
            )
            createrun = self.minotourapi.create_run(
                run_name, run_id, is_barcoded, has_fastq, flowcell
            )
            if not createrun:
                log.critical("There is a problem creating run")
                sys.exit()
            else:
                log.debug("run created")
            run = createrun

        if not self.run:
            self.run = run
        for item in run["barcodes"]:
            self.barcode_dict.update({item["name"]: item["id"]})

        # self.get_read_names_by_run()

    def commit_reads(self):
        """
        Call create reads - which posts a batch of reads to the server.
        Returns
        -------
        None
        """

        self.minotourapi.create_reads(self.read_list)
        # Throttle to limit rate of upload.
        time.sleep(0.5)
        self.upload_data.reads_uploaded += len(self.read_list)
        # Refresh the read list
        self.read_list = []

    def update_read_type(self, read_id, type):
        payload = {"type": type}
        requests.patch(
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
        runid = fastq_read_payload["runid"]
        read_id = fastq_read_payload["read_id"]
        fastq_read_payload["run"] = self.run["id"]

        # Here we are going to create the sequenced/unblocked barcodes and read barcode
        for barcode_name in [barcode_name, rejected_barcode_name]:
            if barcode_name not in self.barcode_dict:
                # print(">>> Found new barcode {} for run {}.".format(barcode_name, runid))
                barcode = self.minotourapi.create_barcode(barcode_name, self.run["url"])
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
        if read_id not in self.readnames:
            if self.check_1d2(read_id):
                firstread, secondread = (
                    read_id[: len(read_id) // 2],
                    read_id[len(read_id) // 2 :],
                )
                self.update_read_type(secondread, self.read_type_list["C"])
                fastq_read_payload["type"] = self.read_type_list["1D^2"]
            else:
                fastq_read_payload["type"] = self.read_type_list["T"]

            self.readnames.append(read_id)
            if self.args.GUI:
                self.args.readcount += 1
                self.args.basecount += fastq_read_payload["sequence_length"]
            self.basecount += fastq_read_payload["sequence_length"]
            self.trackedbasecount += fastq_read_payload["sequence_length"]
            if self.args.GUI:
                self.args.qualitysum += fastq_read_payload["quality_average"]
            self.read_list.append(fastq_read_payload)
            log.debug(
                "Checking read_list size {} - {}".format(
                    len(self.read_list), self.batch_size
                )
            )
            if len(self.read_list) >= self.batch_size:
                # TODO do we commit reads here, or above??!
                if not self.args.skip_sequence:
                    self.batch_size = int(
                        1000000 / (int(self.basecount) / self.readcount)
                    )
                    # self.batchsize = self.batchsize
                    # log.info("Batchsize is now {}".format(self.batchsize))
                self.commit_reads()
            elif self.trackedbasecount >= 1000000:
                self.commit_reads()
                self.trackedbasecount = 0
            self.readcount += 1
        else:
            print("Skipping read")
            self.upload_data.reads_skipped += 1
