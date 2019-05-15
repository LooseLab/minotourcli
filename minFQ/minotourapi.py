import datetime
import json as jsonlibrary
import logging
import requests
import gzip
import time

from urllib.parse import urlparse


log = logging.getLogger(__name__)




class MinotourAPI:

    def __init__(self, base_url, port_number, request_headers):

        self.base_url = base_url
        self.port_number = port_number
        self.check_url()
        self.request_headers = request_headers
        self.minion_event_types = self.get_minion_event_types()

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


    def test(self):

        return "OK"

    def get(self, partial_url, parameters=None):

        if not parameters:

            url = '{}api/v1{}'.format(self.base_url, partial_url)

        else:

            url = '{}api/v1{}'.format(self.base_url, partial_url)

        return requests.get(url, headers=self.request_headers, params=parameters)

    def post(self, partial_url, json, parameters=None):

        if not parameters:

            url = '{}api/v1{}'.format(self.base_url, partial_url)

        else:

            url = '{}api/v1{}?{}'.format(self.base_url, partial_url, parameters)

        #print (url)

        return requests.post(url, headers=self.request_headers, json=json)

    def put(self, partial_url, json, parameters=None):

        if not parameters:

            url = '{}api/v1{}'.format(self.base_url, partial_url)

        else:

            url = '{}api/v1{}?{}'.format(self.base_url, partial_url, parameters)

        return requests.put(url, headers=self.request_headers, json=json)

    def delete(self, partial_url, json, parameters=None):

        if not parameters:

            url = '{}api/v1{}'.format(self.base_url, partial_url)

        else:

            url = '{}api/v1{}?{}'.format(self.base_url, partial_url, parameters)

        return requests.delete(url, headers=self.request_headers, json=json)

    def get_target_sets(self, api_key=""):
        """
        Get a list of the target sets, to show during the listing
        :return:
        """
        url = '/metagenomics/targetsets'
        if api_key == "":
            payload = {}
        else:
            payload = {"api_key": api_key, "cli": True}

        req = self.get(url, parameters=payload)

        if req.status_code != 200:
            log.error("Couldn't find target sets to run.")
            log.error("Status-code {}".format(req.status_code))
            log.error("Text {}".format(req.text))
            return None

        else:
            return jsonlibrary.loads(req.text)

    def get_job_options(self):

        url = '/tasktypes/'

        payload = {"cli": True}

        req = self.get(url, parameters=payload)

        if req.status_code != 200:
            log.error("Couldn't find tasks to run.")
            log.error("Status-code {}".format(req.status_code))
            log.error("Text {}".format(req.text))
            return None

        else:
            return jsonlibrary.loads(req.text)

    def get_references(self):

        url = '/reference/'

        req = self.get(url)

        if req.status_code != 200:
            log.error("Couldn't find references.")
            log.error("Status-code {}".format(req.status_code))
            log.error("Text {}".format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)


    def get_file_info_by_runid(self, runid):

        url = '/runs/{}/files/'.format(runid)

        req =self.get(url)

        if req.status_code != 200:
            log.error('Did not find files for {}.'.format(runid))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

    def create_file_info(self, filename, runid, md5check, run):

        payload = {
            'name': filename,
            'runid': runid,
            'md5' : md5check,
            'run' : run
        }

        url = '/runs/{}/files/'.format(runid)

        req = self.post(url, json=payload)

        if req.status_code != 201:

            log.error('File info {} could not be created.')
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:
            fileinfo = jsonlibrary.loads(req.text)
            return fileinfo

    def get_run_by_runid(self, runid):

        url = '/runs/{}/'.format(runid)

        req = self.get(url, 'search_criteria=runid')

        if req.status_code != 200:

            log.info('Did not find run {}.'.format(runid))
            log.info('Creating run {}.'.format(runid))
            log.debug('Status-code {}'.format(req.status_code))
            log.debug('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

    def get_grouprun_by_name(self, name):

        url = '/grouprun/{}/'.format(name)

        req = self.get(url, 'search_criteria=name')

        if req.status_code != 200:

            log.error('Did not find grouprun {}.'.format(name))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            grouprun = jsonlibrary.loads(req.text)
            return grouprun

    def create_run(self, name, runid, is_barcoded, has_fastq, flowcell, minion = None, start_time = None):
        
        payload = {
            "name": name,
            "sample_name": name,
            "runid": runid,
            "is_barcoded": is_barcoded,
            "has_fastq": has_fastq,
            "flowcell": flowcell['url'],
        }

        if minion:
            payload["minion"]=minion['url']

        if start_time:
            payload["start_time"]=start_time

        req = self.post('/runs/', json=payload)

        if req.status_code != 201:

            log.error('Run {} could not be created.'.format(name))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            run = jsonlibrary.loads(req.text)
            return run

    def create_grouprun(self, name):

        payload = {
            'name': name
        }

        req = self.post('/grouprun/', json=payload)

        if req.status_code != 201:

            log.error('GroupRun {} could not be created.'.format(name))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            grouprun = jsonlibrary.loads(req.text)
            return grouprun

    def create_grouprun_membership(self, grouprun, run):

        payload = {
            'grouprun_id': grouprun,
            'run_id': run
        }

        req = self.post('/grouprun-membership/', json=payload)

        if req.status_code != 201:

            log.error('GroupRun membership {} could not be created.')
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            grouprun = jsonlibrary.loads(req.text)
            return grouprun

    def create_reads(self, reads):

        #log.debug('Creating reads')
        #time.sleep(1)
        payload = reads

        req = self.post('/read/', json=payload)

        if req.status_code != 201:

            log.error('Reads batch {} could not be created.')
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            grouprun = jsonlibrary.loads(req.text)
            return grouprun

    def get_read_type_list(self):

        url = '/readtypes/'

        req = self.get(url)

        if req.status_code != 200:

            log.error('FastqReadType list could not be retrieved.')
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            read_type_list = jsonlibrary.loads(req.text)
            return read_type_list

    def create_barcode(self, barcode_name, run_url):

        payload = {
            'name': barcode_name,
            'run': run_url
        }

        req = self.post('/barcode/', json=payload)

        if req.status_code != 201:

            log.error('Barcode {} could not be created.'.format(barcode_name))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            barcode = jsonlibrary.loads(req.text)
            return barcode

    def get_flowcell_by_name(self, name):

        url = '/flowcells/{}/'.format(name)

        req = self.get(url, 'search_criteria=name')

        if req.status_code != 200:

            log.error('Did not find flowcell {}.'.format(name))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

    def create_flowcell(self, name):

        payload = {

            'name': name,
        }

        req = self.post('/flowcells/', json=payload)

        if req.status_code != 201:

            log.error('Flowcell {} could not be created.'.format(name))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

    def create_job(self, flowcell, job, reference=None, targets=None):

        payload = {
            'flowcell': flowcell,
            'job_type': job
        }

        if reference is not None:
            payload['reference'] = reference

        if targets is not None:
            payload["target_set"] = targets

        req = self.post('/tasks/', json=payload)

        if req.status_code != 200:
            log.info(req.status_code)
            log.info(req.text)

    def get_minion_by_name(self, name):

        url = '/minions/{}/'.format(name)

        req = self.get(url, 'search_criteria=name')

        if req.status_code != 200:

            log.debug('Did not find minion {}.'.format(name))
            log.debug('Status-code {}'.format(req.status_code))
            log.debug('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

    def create_minion(self, name):

        payload = {

            'minION_name': name,
            'name': name,
        }

        req = self.post('/minions/', json=payload)

        if req.status_code != 201:

            log.error('Minion {} could not be created.'.format(name))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

    def get_server_version(self):

        url = '/version'

        req = self.get(url)

        if req.status_code != 200:

            log.error('Did not find version for server {}.'.format(self.base_url))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

    ### New functions being added for minknowconnection use.
    def identify_minion(self,minION):
        #print ("args full host {}".format(self.args.full_host))
        r = requests.get(self.args.full_host + 'api/v1/minions', headers=self.header)
        minionidlink = ""
        for minion in jsonlibrary.loads(r.text):
            if minion["minION_name"] == minION:
                minionidlink = minion["url"]
        return(minionidlink)

    def update_minion(self,minION):
        """
        Receives a MinION object from minknowconnection and passes it to the api to
        update any values within it.
        :param minION:
        :return:
        """

        url = '/minions/{}/'.format(minion.id)

        req = self.post(url, json=minion)

        if req.status_code != 201:

            log.debug('Minion {} could not be updated.'.format(name))
            log.debug('Status-code {}'.format(req.status_code))
            log.debug('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

        pass

    def get_minion_event_types(self):

        url = '/minioneventtypes/'

        req = self.get(url)

        if req.status_code != 200:

            log.error('Did not find version for server {}.'.format(self.base_url))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)


    def fetch_minion_scripts(self,minion):

        url = '/minions/{}/scripts/'.format(minion['id'])

        req = self.get(url)

        if req.status_code != 200:
            log.error('Did not find scripts for minion {}.'.format(minion['id']))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            self.minIONscripts = None  # TODO we should move this code to minknowconnection
            return None

        else:
            minIONscripts = jsonlibrary.loads(req.text)
            scriptidlist = list()
            for script in minIONscripts:
                scriptidlist.append(script["identifier"])
            self.minIONscripts = scriptidlist  # TODO we should move this code to minknowconnection
            return jsonlibrary.loads(req.text)


    def update_minion_script(self,minion,scriptdictionary):
        """

        :param minion:
        :param scriptdictionary:
        :return:
        """

        url = '/minions/{}/scripts/'.format(minion['id'])

        if scriptdictionary["identifier"] not in self.minIONscripts:  # TODO we should move this logic to minknowconnection

            payload = dict()

            for item in scriptdictionary:
                payload[item.replace(" ", "_")]=scriptdictionary[item]

            payload["minION"]=str(minion["url"])

            req = self.post(url, json=payload)

            if req.status_code != 201:

                log.debug('script {} could not be updated.'.format(payload))
                log.debug('Status-code {}'.format(req.status_code))
                log.debug('Text {}'.format(req.text))
                return None

            else:

                return jsonlibrary.loads(req.text)

            pass


    def update_minion_event(self,minion,computer,status):
        """

        :param minION: minION
        :param computer: computer_name
        :param status: event
        :return:
        """

        url = '/minions/{}/events/'.format(minion['id'])
        for info in self.minion_event_types:
            for item in info:

                if item == "name":
                    if info[item]==status:
                        statusidlink= info["url"]

        payload = {
            "computer_name": computer, 
            "datetime": str(datetime.datetime.now()), 
            "event": str(urlparse(statusidlink).path),
            "minION": str(minion["url"])
        }

        req = self.post(url, json=payload)

        if req.status_code != 201:

            log.debug('event {} could not be updated.'.format(status))
            log.debug('Status-code {}'.format(req.status_code))
            log.debug('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

        pass

    def update_minion_run_info(self,payload,runid):

        payload = payload

        url = '/runs/{}/rundetails/'.format(runid)

        req = self.post(url, json=payload)

        if req.status_code != 201:
            #print (req.text)
            log.debug('runid {} could not be updated.'.format(runid))
            log.debug('Status-code {}'.format(req.status_code))
            log.debug('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

        pass

    def get_minion_status(self,minion):

        url = '/minions/{}/status/'.format(minion['id'])

        req = self.get(url)

        if req.status_code != 200:

            log.error('minion ID {} could not be checked.'.format(minion['id']))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

        pass


    def create_minion_status(self, payload, minion):

        payload = payload

        url = '/minions/{}/status/'.format(minion['id'])

        req = self.post(url, json=payload)

        if req.status_code != 201:

            log.error('minion status {} could not be created.'.format(minion['id']))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

        pass

    def update_minion_status(self,payload,minion):

        payload = payload

        url = '/minions/{}/status/'.format(minion['id'])

        req = self.put(url, json=payload)

        if req.status_code != 200:

            log.error('minion status {} could not be updated.'.format(minion['id']))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

        pass

    def create_minion_statistic(self,payload,runid):

        url = '/runs/{}/runstats/'.format(runid)

        req = self.post(url, json=payload)

        if req.status_code != 201:

            log.error('minion statistic {} could not be updated.'.format(runid))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

        pass

    def create_message(self, payload, minion):

        payload = payload

        url = '/minions/{}/messages/'.format(minion['id'])

        req = self.post(url, json=payload)

        if req.status_code not in  (200,201):

            log.debug('minion message {} could not be updated.'.format(minion['id']))
            log.debug('Status-code {}'.format(req.status_code))
            log.debug('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

        pass

    def get_minion_jobs(self, minion):

        url = '/minions/{}/control/'.format(minion['id'])

        req = self.get(url)

        if req.status_code != 200:

            log.error('Did not find jobs for minion {}.'.format(self.minion['id']))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            return jsonlibrary.loads(req.text)

    def complete_minion_job(self,minion,job):

        url = '/minions/{}/control/{}/'.format(minion['id'],job['id'])

        req = self.post(url,json=None)

        if req.status_code != 204:

            log.error('Could not complete job for minion {}.'.format(minion['id']))
            log.error('Status-code {}'.format(req.status_code))
            log.error('Text {}'.format(req.text))
            return None

        else:

            pass
