import json

import requests

class MinotourAPI:

    def __init__(self, base_url, request_headers):

        self.base_url = base_url
        self.request_headers = request_headers

    def get(self, partial_url, parameters=None):

        url = '{}api/v1{}?{}'.format(self.base_url, partial_url, parameters)
        return requests.get(url, headers=self.request_headers)

    def post(self, partial_url, json, parameters=None):

        url = '{}api/v1{}?{}'.format(self.base_url, partial_url, parameters)
        return requests.post(url, headers=self.request_headers, json=json)

    def get_run_by_runid(self, runid):

        req = self.get('/runs/{}/'.format(runid))

        if req.status_code != 200:

            return None

        else:

            run = json.loads(req.text)
            return run

    def get_grouprun_by_name(self, name):

        print('search for grouprun name = {}'.format(name))
        print('url {}'.format('/grouprun/{}/'.format(name)))

        req = self.get('/grouprun/{}/'.format(name))

        if req.status_code != 200:

            print('status code: {}'.format(req.status_code))
            return None

        else:

            print('text: {}'.format(req.text))
            grouprun = json.loads(req.text)
            return grouprun

    def create_run(self, name, runid, is_barcoded, has_fastq):

        print('>>> creating new run')

        payload = {
            "name": name,
            "runid": runid,
            "is_barcoded": is_barcoded,
            "has_fastq": has_fastq
        }

        req = self.post('/runs/', json=payload)

        if req.status_code != 201:

            print('nao criou grouprun')
            print(req.status_code)
            print(req.text)
            print('>>> new run not created - returning None')
            return None

        else:

            run = json.loads(req.text)
            print('>>> new run created - returning {}'.format(run))
            return run

    def create_grouprun(self, name):

        print('creating new grouprun')
        payload = {
            'name': name
        }

        req = self.post('/grouprun/', json=payload)

        if req.status_code != 201:

            print('nao criou grouprun')
            print(req.status_code)
            print(req.text)
            return None

        else:

            grouprun = json.loads(req.text)
            return grouprun

    def create_grouprun_membership(self, grouprun, run):

        print('creating new grouprun-membership')
        payload = {
            'grouprun_id': grouprun,
            'run_id': run
        }

        req = self.post('/grouprun-membership/', json=payload)

        if req.status_code != 201:

            print('nao criou grouprun-membership')
            print(req.status_code)
            print(req.text)
            return None

        else:

            grouprun = json.loads(req.text)
            return grouprun
