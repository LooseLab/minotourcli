import datetime
import json as json_library
import logging
import sys

import requests

from urllib.parse import urlparse

from minFQ.Errors import MTConnectionError
from minFQ.endpoints import EndPoint

log = logging.getLogger(__name__)


class MinotourAPI:
    def __init__(self, base_url, port_number, request_headers):
        self.base_url = base_url
        self.port_number = port_number
        self.request_headers = request_headers
        self.check_url()
        self.test()
        self.minion_event_types = self.get_json(EndPoint.MINION_EVENT_TYPES)

    def check_url(self):
        """
        Check URL to see if we have a https connection or a http connection.
        Returns
        -------
        None
        """
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

    def test(self):
        """
        Connect to the server and check everything is cool
        Returns
        -------

        """
        data = self.get(EndPoint.TEST)
        log.debug("Successfully tested connection -> {}".format(data))

    def _get(self, endpoint, params=None, **kwargs):
        """
        Get the response to a request to the minoTour server
        Parameters
        ----------
        endpoint:  <enum 'EndPoint'>
            The Enum for the endpoint we wish to get from
        params: dict
            The get request params to include
        base_id: str
            The base id for the url ex. /minion/*1*/
        append_id: str
            The appended id after the base id ex. /minion/1/jobs/*2*
        no_id: bool
            Strip the id space from the url

        Returns
        -------
        requests.models.Response
            The requests object from the request

        """

        url = "{}api/v1{}".format(self.base_url, endpoint.resolve_url(**kwargs))
        resp = requests.get(url, headers=self.request_headers, params=params)
        # handle resp fail ...
        self.handle_response(resp)
        return resp

    def get(self, *args, **kwargs):
        """
        Perform get AJAX requests to minoTour server
        Parameters
        ----------
        args
            Expanded function arguments
        kwargs
            Expanded keyword arguments
        Returns
        -------
        str
            The string data response to the request

        """
        return self._get(*args, **kwargs).text

    def get_json(self, *args, **kwargs):
        """
        Get Json from minoTour
        Parameters
        ----------
        args
        kwargs

        Returns
        -------
        dict or list
            Json parsed data string

        """
        # TODO careful as this may not tells us we have errors
        try:
            return json_library.loads(self.get(*args, **kwargs))
        except json_library.JSONDecodeError:
            return ""

    def _post(self, endpoint, json, params=None, **kwargs):
        """
        Perform post AJAX requests to minoTour server
        Parameters
        ----------
        endpoint: str or  <enum 'EndPoint'>
            The partial Url to append the the server address.
        json: dict
            Json str to send containing any data to post.
        params: dict
            Post request parameters
        base_id: str
            The base id for the url ex. /minion/*1*/
        append_id: str
            The appended id after the base id ex. /minion/1/jobs/*2*
        no_id: bool
            If the url has no slug id in it
        Returns
        -------
        requests.models.Response

        """
        url = "{}api/v1{}".format(self.base_url, endpoint.resolve_url(**kwargs))
        resp = requests.post(url, headers=self.request_headers, json=json, params=params)
        self.handle_response(resp)
        return resp

    def post(self, *args, **kwargs):
        """

        Parameters
        ----------
        args
            Expanded arguments
        kwargs
            Expanded Keyword args
        Returns
        -------
        dict or list or str
            Parsed JSON str response, or string response if returned text is not JSON
        """
        resp = self._post(*args, **kwargs)
        try:
            return resp.json()
        except json_library.JSONDecodeError:
            return resp.text

    def _put(self, endpoint, json, params=None, **kwargs):
        """
        perform a put AJAX request to the server.
        Parameters
        ----------
        endpoint: minFQ.endpoints.EndPoint
            Enum containing the url ending
        json: dict
            Dictionary of data to put
        params: str or dict
            Request query string parameters and body parameters
        base_id: str
            The base id for the url ex. /minion/*1*/
        append_id: str
            The appended id after the base id ex. /minion/1/jobs/*2*
        no_id: bool
            Strip the slug format from the enum value string

        Returns
        -------
        requests.models.Response
        """
        url = "{}api/v1{}".format(self.base_url, endpoint.resolve_url(**kwargs))
        resp = requests.put(url, headers=self.request_headers, json=json, params=params)
        self.handle_response(resp)
        return resp

    def put(self, *args, **kwargs):
        """
        Perform put AJAX requests to minoTour server
        Parameters
        ----------
        args
        kwargs
        Returns
        -------
        str or dict
            Dict if response is JSON parseable else empty string
        """
        try:
            return self._put(*args, **kwargs).json()
        except json_library.JSONDecodeError:
            return ""

    def delete(self, partial_url, json, parameters=None):
        """
        Perform delete AJAX requests to minoTour server
        Parameters
        ----------
        partial_url: str
            The partial Url to append the the server address.
        json: dict
            The JSON string to send to the server
        parameters: dict
            Put request parameters
        Returns
        -------
        requests.models.Response

        """
        url = "{}api/v1{}?{}".format(self.base_url, partial_url, parameters)
        return requests.delete(url, headers=self.request_headers, json=json, params=parameters)

    def handle_response(self, response):
        """
        Handle responses as provided by the minFQ client
        Returns
        -------
        None
        """
        if response.status_code not in {200, 201, 204, 400, 404, 502}:
            log.debug("{} responded with status {}".format(response.url, response.status_code))
            log.debug("Text {}".format(response.text))
            log.error(MTConnectionError(response))
            raise MTConnectionError(response)
        if response.status_code == 502:
            log.info("Received bad gateway 502 on request {}. Trying to continue....".format(response.url))
        return None

    def get_or_create(self, *args, **kwargs):
        """
        Get an object from the minoTour server or create it if we receive a 404
        Parameters
        ----------
        args
        kwargs

        Returns
        -------

        """
        payload = kwargs.pop("json")
        resp = self._get(*args, **kwargs)
        if not resp:
            kwargs["params"] = None
            kwargs["json"] = payload
            return self.post(*args, **kwargs)
        else:
            return resp.json()
