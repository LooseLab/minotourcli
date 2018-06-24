import json
import datetime

import requests

from urllib.parse import urlparse


class MinotourAPI:

    def __init__(self, base_url, request_headers):

        self.base_url = base_url
        self.request_headers = request_headers
        self.minion_event_types = self.get_minion_event_types()


    def test(self):

        return "OK"

    def get(self, partial_url, parameters=None):

        if not parameters:

            url = '{}api/v1{}'.format(self.base_url, partial_url)

        else:

            url = '{}api/v1{}?{}'.format(self.base_url, partial_url, parameters)

        return requests.get(url, headers=self.request_headers)

    def post(self, partial_url, json, parameters=None):

        if not parameters:

            url = '{}api/v1{}'.format(self.base_url, partial_url)

        else:

            url = '{}api/v1{}?{}'.format(self.base_url, partial_url, parameters)

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


    def get_run_by_runid(self, runid):

        url = '/runs/{}/'.format(runid)

        req = self.get(url, 'search_criteria=runid')

        if req.status_code != 200:

            print('Did not find run {}.'.format(runid))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

    def get_grouprun_by_name(self, name):

        url = '/grouprun/{}/'.format(name)

        req = self.get(url, 'search_criteria=name')

        if req.status_code != 200:

            print('Did not find grouprun {}.'.format(name))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            grouprun = json.loads(req.text)
            return grouprun

    def create_run(self, name, runid, is_barcoded, has_fastq, flowcell, minion = None, start_time = None):
        print (minion)
        payload = {
            "name": name,
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

            print('Run {} could not be created.'.format(name))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            run = json.loads(req.text)
            return run

    def create_grouprun(self, name):

        payload = {
            'name': name
        }

        req = self.post('/grouprun/', json=payload)

        if req.status_code != 201:

            print('GroupRun {} could not be created.'.format(name))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            grouprun = json.loads(req.text)
            return grouprun

    def create_grouprun_membership(self, grouprun, run):

        payload = {
            'grouprun_id': grouprun,
            'run_id': run
        }

        req = self.post('/grouprun-membership/', json=payload)

        if req.status_code != 201:

            print('GroupRun membership {} could not be created.')
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            grouprun = json.loads(req.text)
            return grouprun

    def create_reads(self, reads):

        payload = reads

        req = self.post('/read/', json=payload)

        if req.status_code != 201:

            print('Reads batch {} could not be created.')
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            grouprun = json.loads(req.text)
            return grouprun

    def get_read_type_list(self):

        url = '/readtypes/'

        req = self.get(url)

        if req.status_code != 200:

            print('FastqReadType list could not be retrieved.')
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            read_type_list = json.loads(req.text)
            return read_type_list

    def create_barcode(self, barcode_name, run_url):

        payload = {
            'name': barcode_name,
            'run': run_url
        }

        req = self.post('/barcode/', json=payload)

        if req.status_code != 201:

            print('Barcode {} could not be created.'.format(barcode_name))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            barcode = json.loads(req.text)
            return barcode

    def get_flowcell_by_name(self, name):

        url = '/flowcells/{}/'.format(name)

        req = self.get(url, 'search_criteria=name')

        if req.status_code != 200:

            print('Did not find flowcell {}.'.format(name))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

    def create_flowcell(self, name):

        payload = {

            'name': name,
        }

        req = self.post('/flowcells/', json=payload)

        if req.status_code != 201:

            print('Flowcell {} could not be created.'.format(name))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

    def get_minion_by_name(self, name):

        url = '/minions/{}/'.format(name)

        req = self.get(url, 'search_criteria=name')

        if req.status_code != 200:

            print('Did not find minion {}.'.format(name))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

    def create_minion(self, name):

        payload = {

            'minION_name': name,
            'name': name,
        }

        req = self.post('/minions/', json=payload)

        if req.status_code != 201:

            print('Minion {} could not be created.'.format(name))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

    def get_server_version(self):

        url = '/version'

        req = self.get(url)

        if req.status_code != 200:

            print('Did not find version for server {}.'.format(self.base_url))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

    ### New functions being added for minknowconnection use.
    def identify_minion(self,minION):
        #print ("args full host {}".format(self.args.full_host))
        r = requests.get(self.args.full_host + 'api/v1/minions', headers=self.header)
        minionidlink = ""
        for minion in json.loads(r.text):
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

            print('Minion {} could not be updated.'.format(name))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

        pass

    def get_minion_event_types(self):

        url = '/minioneventtypes/'

        req = self.get(url)

        if req.status_code != 200:

            print('Did not find version for server {}.'.format(self.base_url))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)


    def fetch_minion_scripts(self,minion):

        url = '/minions/{}/scripts/'.format(minion['id'])

        req = self.get(url)

        if req.status_code != 200:
            print('Did not find scripts for minion {}.'.format(minion['id']))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            self.minIONscripts = None
            return None

        else:
            minIONscripts = json.loads(req.text)
            scriptidlist = list()
            for script in minIONscripts:
                scriptidlist.append(script["identifier"])
            self.minIONscripts = scriptidlist
            return json.loads(req.text)


    def update_minion_script(self,minion,scriptdictionary):
        """

        :param minion:
        :param scriptdictionary:
        :return:
        """

        #print (type(self.minIONscripts))

        url = '/minions/{}/scripts/'.format(minion['id'])

        if scriptdictionary["identifier"] not in self.minIONscripts:

            payload = dict()

            for item in scriptdictionary:
                payload[item.replace(" ", "_")]=scriptdictionary[item]

            payload["minION"]=str(minion["url"])

            req = self.post(url, json=payload)

            if req.status_code != 201:

                print('script {} could not be updated.'.format(payload))
                print('Status-code {}'.format(req.status_code))
                print('Text {}'.format(req.text))
                return None

            else:

                return json.loads(req.text)

            pass

        else:
            pass
            #print ("Script already present")

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

        payload = {"computer_name": computer, "datetime": str(datetime.datetime.now()), "event": str(urlparse(statusidlink).path),"minION": str(minion["url"])}

        req = self.post(url, json=payload)

        if req.status_code != 201:

            print('event {} could not be updated.'.format(status))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

        pass

    def update_minion_run_info(self,payload,runid):

        payload = payload

        url = '/runs/{}/rundetails/'.format(runid)

        req = self.post(url, json=payload)

        if req.status_code != 201:

            print('runid {} could not be updated.'.format(runid))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

        pass

    def get_minion_status(self,minion):

        url = '/minions/{}/status/'.format(minion['id'])

        req = self.get(url)

        if req.status_code != 200:

            print('minion ID {} could not be checked.'.format(minion['id']))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

        pass


    def create_minion_status(self,payload,minion):

        payload = payload

        url = '/minions/{}/status/'.format(minion['id'])

        req = self.post(url, json=payload)

        if req.status_code != 201:

            print('minion status {} could not be created.'.format(minion['id']))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

        pass

    def update_minion_status(self,payload,minion):

        payload = payload

        url = '/minions/{}/status/'.format(minion['id'])

        req = self.put(url, json=payload)

        if req.status_code != 200:

            print('minion status {} could not be updated.'.format(minion['id']))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

        pass

    def create_minion_statistic(self,payload,runid):

        payload = payload

        url = '/runs/{}/runstats/'.format(runid)

        req = self.post(url, json=payload)

        if req.status_code != 201:

            print('minion statistic {} could not be updated.'.format(runid))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

        pass

    def create_message(self, payload, minion):
        payload = payload

        url = '/minions/{}/messages/'.format(minion['id'])

        req = self.post(url, json=payload)

        if req.status_code not in  (200,201):

            print('minion message {} could not be updated.'.format(minion['id']))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

        pass

    def get_minion_jobs(self, minion):

        url = '/minions/{}/control/'.format(minion['id'])

        req = self.get(url)

        if req.status_code != 200:

            print('Did not find jobs for minion {}.'.format(self.minion['id']))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            return json.loads(req.text)

    def complete_minion_job(self,minion,job):

        url = '/minions/{}/control/{}/'.format(minion['id'],job['id'])

        req = self.post(url,json=None)

        if req.status_code != 204:
            print('Could not complete job for minion {}.'.format(minion['id']))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            pass