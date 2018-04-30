import json

import requests


class MinotourAPI:

    def __init__(self, base_url, request_headers):

        self.base_url = base_url
        self.request_headers = request_headers

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

    def get_run_by_runid(self, runid):

        url = '/runs/{}/'.format(runid)

        req = self.get(url, 'search_criteria=runid')

        if req.status_code != 200:

            return None

        else:

            run = json.loads(req.text)
            return run

    def get_grouprun_by_name(self, name):

        req = self.get('/grouprun/{}/'.format(name))

        if req.status_code != 200:

            print('Did not fing grouprun {}.'.format(name))
            print('Status-code {}'.format(req.status_code))
            print('Text {}'.format(req.text))
            return None

        else:

            grouprun = json.loads(req.text)
            return grouprun

    def create_run(self, name, runid, is_barcoded, has_fastq):

        payload = {
            "name": name,
            "runid": runid,
            "is_barcoded": is_barcoded,
            "has_fastq": has_fastq
        }

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

