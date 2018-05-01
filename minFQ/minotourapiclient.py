"""
A class to handle the collection of run statistics and information from fastq files and upload to minotour.
"""
import datetime
import json
import os
import sys

import dateutil.parser

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


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

        self.base_url = args.full_host

        self.args = args
        self.header = header
        self.readnames = list()
        self.readcount = 0
        self.read_type_list = dict()
        self.batchsize = 2000
        self.run = None
        self.grouprun = None
        self.barcode_dict = {}
        self.read_list = []

        self.minotourapi = MinotourAPI(self.args.full_host, self.header)
        self.get_readtype_list()


    def get_readtype_list(self):

        read_type_list = self.minotourapi.get_read_type_list()

        read_type_dict = {}

        for read_type in read_type_list:

            read_type_dict[read_type["name"]] = read_type["url"]

        self.read_type_list = read_type_dict

    def get_readnames_by_run(self):

        url = "{}api/v1/runs/{}/readnames/".format(self.base_url, self.run['id'])
        print(url)

        req = requests.get(
            url,
            headers=self.header
        )

        readname_list = json.loads(req.text)

        print(readname_list)

        number_pages = readname_list['number_pages']

        self.args.fastqmessage = "Fetching reads to check if we've uploaded these before."

        #for page in tqdm(range(number_pages)):
        for page in range(number_pages):

            self.args.fastqmessage = "Fetching {} of {} pages.".format(page,number_pages)

            url += '?page={}'.format(page)

            content = requests.get(url, headers=self.header)

            # We have to recover the data component and loop through that to get the read names.
            for read in json.loads(content.text)["data"]:

                self.readnames.append(read)

    def add_run(self, descriptiondict):

        self.args.fastqmessage = "Adding run."

        runid = descriptiondict["runid"]

        run = self.minotourapi.get_run_by_runid(runid)

        if not run:

            runname = self.args.run_name

            if "barcode" in descriptiondict.keys():

                is_barcoded = True

            else:

                is_barcoded = False

            if self.args.skip_sequence:

                has_fastq = False

            else:

                has_fastq = True

            createrun = self.minotourapi.create_run(runname, runid, is_barcoded, has_fastq)

            if not createrun:

                print('There is a problem creating run')
                sys.exit()

            if not self.grouprun:

                print('>>> does grouprun {} exist?'.format(runname))

                grouprun = self.minotourapi.get_grouprun_by_name(runname)

                if grouprun:

                    print('>>> Yes! {}'.format(grouprun))

                else:

                    print('>>> No! Lets create one.')

                if not grouprun:

                    grouprun = self.minotourapi.create_grouprun(runname)

                    print('>>> Created! {}'.format(grouprun))

                self.grouprun = grouprun

                self.minotourapi.create_grouprun_membership(
                    grouprun['id'],
                    createrun['id']
                )

            run = createrun

        if not self.run:

            self.run = run

        for item in run['barcodes']:

            print('>>> {}'.format(item['url']))

            self.barcode_dict.update({
                item['name']: item['url']
            })

    def commit_reads(self):

        self.minotourapi.create_reads(self.read_list)

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

        fastq_read_payload['run'] = self.run['url']

        if barcode_name not in self.barcode_dict:

            print(">>> Found new barcode {} for run {}.".format(barcode_name, runid))

            barcode = self.minotourapi.create_barcode(barcode_name, self.run['url'])

            if barcode:

                self.barcode_dict.update({
                    barcode['name']: barcode['url']
                })

            else:

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

            if self.args.GUI:
                self.args.qualitysum += fastq_read_payload['quality_average']

            self.read_list.append(fastq_read_payload)

            if len(self.read_list) >= self.batchsize:
                self.commit_reads()

            self.readcount += 1
