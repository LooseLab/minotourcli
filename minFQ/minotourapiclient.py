"""
A class to handle the collection of run statistics and information 
from fastq files and upload to minotour.
"""
import datetime
import json
import logging
import sys, time

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib.parse import urlparse
from threading import Thread


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


from minFQ.minotourapi import MinotourAPI


class Runcollection:
    def __init__(self, args, header):

        log.debug("Initialising Runcollection")

        self.base_url = args.host_name
        self.port_number = args.port_number
        self.check_url()
        self.args = args
        self.header = header
        self.readnames = list()
        self.readcount = 0
        self.basecount = 0
        self.trackedbasecount = 0
        self.read_type_list = dict()
        if self.args.skip_sequence:
            self.batchsize = 5000
        else:
            self.batchsize = 4000
        self.run = None
        self.grouprun = None
        self.barcode_dict = {}
        self.read_list = []
        self.filemonitor = dict()
        self.fastqfileid = None
        self.minotourapi = MinotourAPI(
            self.args.host_name, self.args.port_number, self.header
        )
        self.get_readtype_list()
        self.unblocked_dict = dict()
        self.unblocked_file = None
        self.unblocked_line_start = 0
        self.runfolder = None
        self.toml = None

    def add_toml_file(self, toml_file):
        self.toml = toml_file

    def add_run_folder(self, folder):
        self.runfolder = folder

    def add_unblocked_reads_file(self):
        pass

    def create_jobs(self, flowcell, args):
        """
        Create jobs when runCollection is initialised
        Returns
        -------

        """
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

    def get_readnames_by_run(self, fastqfileid):

        if fastqfileid != self.fastqfileid:
            self.fastqfileid = fastqfileid
            # TODO move this function to MinotourAPI class.

            # url = "{}api/v1/runs/{}/readnames/".format(self.base_url, self.run['id'])
            url = "{}api/v1/runs/{}/readnames/".format(self.base_url, fastqfileid)

            req = requests.get(url, headers=self.header)

            readname_list = json.loads(req.text)

            number_pages = readname_list["number_pages"]

            log.debug("Fetching reads to check if we've uploaded these before.")
            log.debug("Wiping previous reads seen.")
            self.readnames = list()
            # for page in tqdm(range(number_pages)):
            for page in range(number_pages):

                self.args.fastqmessage = "Fetching {} of {} pages.".format(
                    page, number_pages
                )

                new_url = url + "?page={}".format(page)

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

    def add_run(self, descriptiondict, args):

        self.args.fastqmessage = "Adding run."
        runid = descriptiondict["runid"]
        run = self.minotourapi.get_run_by_runid(runid)
        if "flow_cell_id" in descriptiondict:
            flowcellname = descriptiondict["flow_cell_id"]
        elif "sample_id" in descriptiondict:
            flowcellname = descriptiondict["sample_id"]
        elif "sampleid" in descriptiondict:
            flowcellname = descriptiondict["sampleid"]
        else:
            flowcellname = self.args.run_name

        if args.force_unique:
            if "flow_cell_id" in descriptiondict and "sample_id" in descriptiondict:
                flowcellname = "{}_{}".format(
                    descriptiondict["flow_cell_id"], descriptiondict["sample_id"]
                )

        if not flowcellname:
            self.args.errored = True
            self.args.error_message = "Flowcell name is required. This may be old FASTQ data, please provide a name with -n."
            sys.exit("Flowcell name is required. This may be old FASTQ data, please provide a name with -n.")
        flowcell = self.minotourapi.get_flowcell_by_name(flowcellname)["data"]

        if not run:
            ## We want to add a force unique name - therefore we are going to use an extra argument in minFQ - forceunique?
            #
            # get or create a flowcell
            #
            log.info("Looking for flowcell {}".format(flowcellname))
            log.debug(flowcell)
            if not flowcell:

                log.debug("Trying to create flowcell {}".format(flowcellname))

                flowcell = self.minotourapi.create_flowcell(flowcellname)
                # print(dir(args))
                # If we have a job as an option

                log.debug("Created flowcell {}".format(flowcellname))

            #
            # create a run
            #
            if "barcode" in descriptiondict.keys():

                is_barcoded = True

            else:

                is_barcoded = False

            if self.args.skip_sequence:

                has_fastq = False

            else:

                has_fastq = True

            if "sample_id" in descriptiondict:
                runname = descriptiondict["sample_id"]
            else:
                runname = self.args.run_name

            createrun = self.minotourapi.create_run(
                runname, runid, is_barcoded, has_fastq, flowcell
            )

            if not createrun:

                log.critical("There is a problem creating run")
                sys.exit()

            else:
                log.debug("run created")

            run = createrun
        if args.job:
            self.create_jobs(flowcell, args)

        if not self.run:

            self.run = run

        for item in run["barcodes"]:

            self.barcode_dict.update({item["name"]: item["id"]})

        # self.get_readnames_by_run()

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
        self.args.reads_uploaded += len(self.read_list)
        # Refresh the read list
        self.read_list = list()

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
                    len(self.read_list), self.batchsize
                )
            )

            if len(self.read_list) >= self.batchsize:
                if not self.args.skip_sequence:
                    self.batchsize = int(
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
            self.args.reads_skipped += 1
