"""
A class to handle the collection of run statistics and information 
from fastq files and upload to minotour.
"""
import datetime
import json
import logging
import sys

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib.parse import urlparse
from threading import Thread


log = logging.getLogger(__name__)

# https://www.peterbe.com/plog/best-practice-with-retries-with-requests
def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
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
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

from minFQ.minotourapi import MinotourAPI


class Runcollection():

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
        self.read_type_list = dict()
        #self.batchsize = 2000
        self.batchsize = 100
        self.run = None
        self.grouprun = None
        self.barcode_dict = {}
        self.read_list = []
        self.filemonitor = dict()
        self.fastqfileid = None
        self.minotourapi = MinotourAPI(self.args.host_name, self.args.port_number, self.header)
        self.get_readtype_list()


    def check_url(self):
        if self.base_url.startswith("http://"):
            self.base_url = self.base_url[7:]
        if self.base_url.startswith(("https://")):
            self.base_url = self.base_url[8:]
        if int(self.port_number) != 80:
            r = requests.get("http://{}:{}/".format(self.base_url, self.port_number))
        else:
            r = requests.get("http://{}/".format(self.base_url))
        #print (r.url)
        if r.url.startswith("https"):
            self.base_url="https://{}/".format(self.base_url)
        else:
            self.base_url="http://{}:{}/".format(self.base_url,self.port_number)

    def get_readtype_list(self):

        read_type_list = self.minotourapi.get_read_type_list()

        read_type_dict = {}

        for read_type in read_type_list:

            read_type_dict[read_type["name"]] = read_type["id"]

        self.read_type_list = read_type_dict


    def get_readnames_by_run(self,fastqfileid):

        if fastqfileid != self.fastqfileid:
            self.fastqfileid = fastqfileid
            # TODO move this function to MinotourAPI class.

            #url = "{}api/v1/runs/{}/readnames/".format(self.base_url, self.run['id'])
            url = "{}api/v1/runs/{}/readnames/".format(self.base_url, fastqfileid)

            req = requests.get(
                url,
                headers=self.header
            )

            readname_list = json.loads(req.text)

            number_pages = readname_list['number_pages']

            log.debug("Fetching reads to check if we've uploaded these before.")
            log.debug("Wiping previous reads seen.")
            self.readnames = list()
            #for page in tqdm(range(number_pages)):
            for page in range(number_pages):

                self.args.fastqmessage = "Fetching {} of {} pages.".format(page,number_pages)

                new_url = url + '?page={}'.format(page)

                content = requests.get(new_url,  headers=self.header)

                log.debug("Requesting {}".format(new_url))

                # We have to recover the data component and loop through that to get the read names.
                for read in json.loads(content.text)["data"]:

                    self.readnames.append(read)

            log.debug("{} reads already processed and included into readnames list for run {}".format(len(self.readnames), self.run['id']))

    def add_run(self, descriptiondict, args):

        self.args.fastqmessage = "Adding run."

        runid = descriptiondict["runid"]

        run = self.minotourapi.get_run_by_runid(runid)

        if not run:

            #print (descriptiondict)

            if 'flow_cell_id' in descriptiondict:
                flowcellname = descriptiondict['flow_cell_id']
            elif 'sampleid' in descriptiondict:
                flowcellname = descriptiondict['sampleid']
            else:
                flowcellname = self.args.run_name


            #
            # get or create a flowcell
            #

            log.debug("Looking for flowcell {}".format(flowcellname))

            flowcell = self.minotourapi.get_flowcell_by_name(flowcellname)['data']

            log.debug("found {}".format(flowcell))

            if not flowcell:

                log.debug("Trying to create flowcell {}".format(flowcellname))

                flowcell = self.minotourapi.\
                    create_flowcell(flowcellname)
                # print(dir(args))
                # If we have a job as an option
                if args.job:
                    # If there is a target set
                    if args.targets is not None:
                        self.minotourapi.create_job(flowcell['id'], int(args.job_id), None, args.targets)
                    # If there is a reference and not a target set
                    elif args.reference and not args.targets:
                        self.minotourapi.create_job(flowcell['id'], int(args.job_id), args.reference, None)
                    # If there is neither
                    else:
                        self.minotourapi.create_job(flowcell['id'], int(args.job_id), None, None)
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

            if 'sample_id' in descriptiondict:
                runname = descriptiondict['sample_id']
            else:
                runname = self.args.run_name

            createrun = self.minotourapi.create_run(runname, runid, is_barcoded, has_fastq, flowcell)

            if not createrun:

                log.critical('There is a problem creating run')
                sys.exit()

            else:
                log.debug("run created")

            run = createrun

        if not self.run:

            self.run = run

        for item in run['barcodes']:

            self.barcode_dict.update({
                item['name']: item['id']
            })

        #self.get_readnames_by_run()

    def commit_reads(self):

        #Thread(target=self.minotourapi.create_reads(self.read_list)).start()
        self.minotourapi.create_reads(self.read_list)
        self.args.reads_uploaded += len(self.read_list)

        self.read_list = list()

    def update_read_type(self, read_id, type):
        payload = {'type': type}
        updateread = requests.patch(self.args.full_host + 'api/v1/runs/' + str(self.runid) + "/reads/" + str(read_id) + '/',
                                    headers=self.header, json=payload)

    def check_1d2(self, readid):
        if len(readid) > 64:
            return True

    def add_read(self, fastq_read_payload):

        barcode_name = fastq_read_payload['barcode_name']
        runid = fastq_read_payload['runid']
        read_id = fastq_read_payload['read_id']

        fastq_read_payload['run'] = self.run['id']

        if barcode_name not in self.barcode_dict:

            # print(">>> Found new barcode {} for run {}.".format(barcode_name, runid))

            barcode = self.minotourapi.create_barcode(barcode_name, self.run['url'])

            if barcode:

                self.barcode_dict.update({
                    barcode['name']: barcode['id']
                })

            else:
                log.critical("Problem finding barcodes.")
                sys.exit()

        fastq_read_payload['barcode'] = self.barcode_dict[fastq_read_payload['barcode_name']]

        if read_id not in self.readnames:

            if self.check_1d2(read_id):

                firstread, secondread = read_id[:len(read_id) // 2], read_id[len(read_id) // 2:]

                self.update_read_type(secondread, self.read_type_list["Complement"])

                fastq_read_payload['type'] = self.read_type_list["1D^2"]

            else:

                fastq_read_payload['type'] = self.read_type_list["Template"]

            self.readnames.append(read_id)

            if self.args.GUI:
                self.args.readcount += 1

            if self.args.GUI:
                self.args.basecount += fastq_read_payload['sequence_length']
            self.basecount += fastq_read_payload['sequence_length']

            if self.args.GUI:
                self.args.qualitysum += fastq_read_payload['quality_average']

            self.read_list.append(fastq_read_payload)

            log.debug('Checking read_list size {} - {}'.format(len(self.read_list), self.batchsize))

            if len(self.read_list) >= self.batchsize:
                self.batchsize = int(5000000/(int(self.basecount)/self.readcount))
                self.commit_reads()

            self.readcount += 1

        else:
            print ("Skipping read")
            self.args.reads_skipped += 1