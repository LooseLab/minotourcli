"""
A class to handle the collection of run statistics and information from fastq files and upload to minotour.
"""
import datetime
import json
import os
import sys

import dateutil.parser
import numpy as np
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

#session = FuturesSession(executor=ThreadPoolExecutor(max_workers=10))
from minFQ.minotourapi import MinotourAPI


class Runcollection():

    def __init__(self, args, header):

        self.base_url = args.full_host
        self.run = {}

        self.args = args
        self.header = header
        self.readid = dict()
        self.readnames = list()
        self.cumulength = 0
        self.readcount = 0
        self.readlengths = list()
        self.timeid = dict()
        self.chandict = list()
        self.runidlink = ""
        self.readtypes = dict()
        self.statsrecord = dict()
        self.barcodes = dict()
        self.runid = 0
        self.readstore = list()
        self.flowcelllink = ""
        self.batchsize = 2000
        self.minotourapi = MinotourAPI(self.args.full_host, self.header)
        self.get_readtype_list()
        self.grouprun = None


    def get_readtype_list(self):

        url = "{}api/v1/readtypes/".format(self.base_url)

        req = requests.get(
            url,
            headers=self.header
        )

        if req.status_code == 200:

            content = json.loads(req.text)

            readtype_dict = {}

            for readtype in content:

                readtype_dict[readtype["name"]] = readtype["url"]

            self.readtypes = readtype_dict

            print('>>>> readtypes')
            print(readtype_dict)
            print('<<<< readtypes')

    def get_or_create_run(self, runid, name, is_barcoded, has_fastq):

        url = "{}api/v1/runs/".format(self.base_url)

        r = requests.get(
            url,
            headers=self.header
        )

        if runid not in r.text:

            payload = {
                "name": name,
                "runid": runid,
                "is_barcoded": is_barcoded,
                "has_fastq": has_fastq
            }

            createrun = requests.post(

                url,
                headers=self.header,
                json=payload
            )

            if createrun.status_code != 201:

                print ("Error - we have been unable to create a run.")
                print (createrun.status_code)
                print (createrun.text)

                sys.exit()

            else:

                run = json.loads(createrun.text)
                created = True

                #if self.args.noMinKNOW:
                #    if self.args.is_flowcell:
                #        self.create_flowcell(self.args.run_name)
                #        self.create_flowcell_run()

        else:

            runs = json.loads(r.text)
            for item in runs:

                if item["runid"] == runid:

                    run = item
                    created = False

        return (run, created)


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

    def create_flowcell(self, name):
        # Test to see if the flowcell exists.
        r = requests.get(self.args.full_host + 'api/v1/flowcells', headers=self.header)
        print (r.text)
        print (name)
        flowcellname = name
        flowcelllist = json.loads(r.text)
        if flowcellname not in [x["name"] for x in flowcelllist]:
            if self.args.GUI:
                self.args.flowcellcount += 1
            createflowcell = requests.post(self.args.full_host + 'api/v1/flowcells/', headers=self.header,
                                           json={"name": flowcellname})
            self.flowcelllink = json.loads(createflowcell.text)["url"]
        else:
            for flowcell in json.loads(r.text):
                if flowcell["name"] == flowcellname:
                    self.flowcelllink = flowcell["url"]
                    break

    def create_flowcell_run(self):
        print ("Adding run to flowcell")
        print (self.flowcelllink)
        if self.args.GUI:
            self.args.flowcellruncount+=1
        createflowcellrun = requests.post(self.flowcelllink, headers=self.header,
                                          json={"flowcell": self.flowcelllink, "run": self.runidlink})

    def add_run(self, descriptiondict):

        self.args.fastqmessage = "Adding run."

        runid = descriptiondict["runid"]

        run = self.minotourapi.get_run_by_runid(runid)

        print('>>> >>> run {}'.format(run))
        print('>>> >>> runid {}'.format(runid))

        sys.exit()

        if not run:

            runname = self.args.run_name

            if "barcode" in descriptiondict.keys():
                is_barcoded = True
                barcoded = "barcoded"
            else:
                is_barcoded = False
                barcoded = "unclassified"
            if self.args.skip_sequence:
                has_fastq = False
            else:
                has_fastq = True

            createrun = self.minotourapi.create_run(runname, runid, is_barcoded, has_fastq)

            if not createrun:

                print('There is a problem creating run')
                sys.exit()

            if not self.grouprun:

                grouprun = self.minotourapi.create_grouprun(runname)
                self.grouprun = grouprun

                self.minotourapi.create_grouprun_membership(
                    grouprun['id'],
                    createrun['id']
                )

        for item in createrun['barcodes']:
            print('>>> {}'.format(item['url']))

            self.barcodes.update({
                item['name']: item['url']
            })

        sys.exit()

    def commit_reads(self):
        runlinkaddread = self.runidlink + "reads/"
        #createread = session.post(runlinkaddread, headers=self.header, json=self.readstore)
        createread = requests.post(runlinkaddread, headers=self.header, json=self.readstore)
        self.readstore = list()

    def add_read_db(self, runid, readid, read, channel, barcode, sequence, quality, ispass, type, starttime):
        runlink = self.runidlink
        typelink = type
        if readid not in self.readnames:
            self.readnames.append(readid)
            if self.args.GUI:
                self.args.readcount += 1
            sequence_length = len(sequence)
            if self.args.GUI:
                self.args.basecount += sequence_length
            quality_average = np.around([np.mean(np.array(list((ord(val) - 33) for val in quality)))], decimals=2)[0]
            if self.args.GUI:
                self.args.qualitysum += quality_average
            if self.args.skip_sequence:
                payload = {
                    'run_id': runlink,
                    'read_id': readid,
                    'read': read,
                    "channel": channel,
                    'barcode': barcode,
                    'sequence': '',
                    'quality': '',
                    'sequence_length': sequence_length,
                    'quality_average': quality_average,
                    'is_pass': ispass,
                    'start_time': starttime,
                    'type': typelink
                }
            else:
                payload = {
                    'run_id': runlink,
                    'read_id': readid,
                    'read': read,
                    "channel": channel,
                    'barcode': barcode,
                    'sequence': sequence,
                    'quality': quality,
                    'sequence_length': sequence_length,
                    'quality_average': quality_average,
                    'is_pass': ispass,
                    'start_time': starttime,
                    'type': typelink
                }
            self.readstore.append(payload)
            if len(self.readstore) >= self.batchsize:
                self.commit_reads()
        else:
            pass

    def add_or_update_stats(self, sample_time, total_length, max_length, min_length, average_length, number_of_reads,
                            number_of_channels, type):
        runlink = self.args.full_host + 'api/v1/runs/' + str(self.runidlink) + "/"
        typelink = self.args.full_host + 'api/v1/readtypes/' + str(type) + "/"
        payload = {'run_id': runlink, 'sample_time': sample_time, 'total_length': total_length,
                   'max_length': max_length, 'min_length': min_length, 'average_length': average_length,
                   'number_of_reads': number_of_reads, 'number_of_channels': number_of_channels, 'type': typelink}
        if sample_time not in self.statsrecord.keys():
            createstats = requests.post(self.args.full_host + 'api/v1/statistics/', headers=self.header, json=payload)
            self.statsrecord[sample_time] = dict()
            self.statsrecord[sample_time]["id"] = json.loads(createstats.text)["id"]
            self.statsrecord[sample_time]['payload'] = payload
        else:
            if self.statsrecord[sample_time]['payload'] != payload:
                deletestats = requests.delete(
                    self.args.full_host + 'api/v1/statistics/' + str(self.statsrecord[sample_time]['id']) + '/',
                    headers=self.header)
                createstats = requests.post(self.args.full_host + 'api/v1/statistics/', headers=self.header, json=payload)
                self.statsrecord[sample_time]["id"] = json.loads(createstats.text)["id"]
                self.statsrecord[sample_time]['payload'] = payload
            else:
                print ("Record not changed.")

    def update_read_type(self, read_id, type):
        payload = {'type': type}
        updateread = requests.patch(self.args.full_host + 'api/v1/runs/' + str(self.runid) + "/reads/" + str(read_id) + '/',
                                    headers=self.header, json=payload)

    def check_1d2(self, readid):
        if len(readid) > 64:
            return True

    def check_pass(self, path):
        folders = os.path.split(path)
        # print folders[0]
        if 'pass' in folders[0]:
            return True
        elif 'fail' in folders[0]:
            return False
        else:
            return True  # This assumes we have been unable to find either pass or fail and thus we assume the run is a pass run.

    def add_read(self, record, descriptiondict, fastq):
        passstatus = (self.check_pass(fastq))
        self.readid[record.id] = dict()
        for item in descriptiondict:
            self.readid[record.id][item] = descriptiondict[item]
        tm = dateutil.parser.parse(self.readid[record.id]["start_time"])
        tm = tm - datetime.timedelta(minutes=(tm.minute % 1) - 1,
                                     seconds=tm.second,
                                     microseconds=tm.microsecond)
        if tm not in self.timeid.keys():
            self.timeid[tm] = dict()
            self.timeid[tm]["cumulength"] = 0
            self.timeid[tm]["count"] = 0
            self.timeid[tm]["readlengths"] = list()
            self.timeid[tm]["chandict"] = list()
        if self.readid[record.id]["ch"] not in self.chandict:
            self.chandict.append(self.readid[record.id]["ch"])
        if self.readid[record.id]["ch"] not in self.timeid[tm]["chandict"]:
            self.timeid[tm]["chandict"].append(self.readid[record.id]["ch"])
        if "barcode" in self.readid[record.id].keys() or self.args.cust_barc == 'oddeven':
            if "barcode" in self.readid[record.id]:
                barcode_local = self.readid[record.id]["barcode"]
            else:
                barcode_local = ""
            if self.args.cust_barc == 'oddeven':
                if int(self.readid[record.id]["ch"]) % 4 == 0:
                    barcode_local = barcode_local + 'even'
                else:
                    barcode_local = barcode_local + 'odd'
            if barcode_local not in self.barcodes.keys():
                print(">> Found new barcode {} for run {}.".format(barcode_local, self.runidlink))
                request_body = {
                    'name': barcode_local,
                    'run': str(self.runidlink)
                }
                print ("Request body formed.")
                print (request_body)
                response = requests.post(
                    str(self.runidlink) + "barcodes/",
                    headers=self.header,
                    json=request_body
                )
                print ("response posted {}".format(response.text))
                if response.status_code == 201:
                    item = json.loads(response.text)
                    self.barcodes.update({
                        item['name']: item['url']
                    })
                    print(">> Barcode {} for run {} created with success.".format(item['url'], self.runidlink))
                else:
                    print (response.status_code)
                    sys.exit()
            barcode_url = self.barcodes[barcode_local]
        else:
            #print ("self.barcodes is:")
            #print (self.barcodes)
            barcode_url = self.barcodes["No barcode"]
        if record.id not in self.readnames:
            if self.check_1d2(record.id):
                firstread, secondread = record.id[:len(record.id) // 2], record.id[len(record.id) // 2:]
                self.update_read_type(secondread, self.readtypes["Complement"])
                self.add_read_db(
                    self.runidlink,
                    record.id,
                    self.readid[record.id]["read"],
                    self.readid[record.id]["ch"],
                    barcode_url,
                    str(record.seq),
                    record.format('fastq').split('\n')[3],
                    passstatus,
                    self.readtypes["1D^2"],
                    self.readid[record.id]["start_time"]
                )
            else:
                self.add_read_db(
                    self.runidlink,
                    record.id,
                    self.readid[record.id]["read"],
                    self.readid[record.id]["ch"],
                    barcode_url,
                    str(record.seq),
                    record.format('fastq').split('\n')[3],
                    passstatus,
                    self.readtypes["Template"],
                    self.readid[record.id]["start_time"]
                )
            self.readid[record.id]["len"] = len(record.seq)
            self.cumulength += len(record.seq)
            self.timeid[tm]["cumulength"] += len(record.seq)
            self.readcount += 1
            self.timeid[tm]["count"] += 1
            self.readlengths.append(len(record.seq))
            self.timeid[tm]["readlengths"].append(len(record.seq))

    def read_count(self):
        return len(self.readid)

    def mean_median_std_max_min(self):
        return np.average(self.readlengths), np.median(self.readlengths), np.std(self.readlengths), np.max(
            self.readlengths), np.min(self.readlengths)

    def parse1minwin(self):
        for time in sorted(self.timeid):
            self.add_or_update_stats(str(time), self.timeid[time]["cumulength"],
                                     np.max(self.timeid[time]["readlengths"]),
                                     np.min(self.timeid[time]["readlengths"]),
                                     np.around(np.average(self.timeid[time]["readlengths"]), decimals=2),
                                     self.timeid[time]["count"], len(self.timeid[time]["chandict"]),
                                     self.readtypes["Template"])
