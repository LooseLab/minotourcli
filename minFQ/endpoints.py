from enum import Enum


class EndPoint(Enum):
    """
    An Enum to store all the endpoints in a single place, so we can track them easily.
    Import to the files you need endpoints in and add them to minotourapi requests.

    """
    # Get
    REFERENCES = "/reference/"
    VERSION = "/minknow/version/"
    GET_MINION = "/minknow/minions/{}/"
    TASK_TYPES = "/reads/task-types/"
    TARGET_SETS = "/metagenomics/target-sets"
    # todo if we get the api right, we can just combine the base minion with the status or events etc.
    MINION_STATUS = "/minknow/minions/{}/status/"
    TEST = "/minknow/test-connect/"
    READ_TYPES = "/reads/read-types/"
    READ_NAMES = "/reads/runs/{}/read-names/"

    MINION_CONTROL = "/minknow/minions/{}/control/"

    # Post or Put
    MINION_EVENT_TYPES = "/minknow/minions/event-types/"
    MINION_EVENT = "/minknow/minions/{}/events/"
    MINION_MESSAGES = "/minknow/minions/{}/messages/"
    MINION_RUN_INFO = "/minknow/minions/runs/{}/"
    MINION_RUN_STATS = "/minknow/minions/runs/{}/run-stats/"
    RUNS = "/reads/runs/{}/"
    FLOWCELL = "/reads/flowcells/{}/"
    FASTQ_FILE = "/reads/runs/{}/files/"
    BARCODE = "/reads/barcode/"
    JOBS = "/reads/tasks/"
    READS = "/reads/read/"

    def __str__(self):
        return "{}".format(self.value)

    def add_id(self, id):
        """
        Return the partial URL, with id formatted into it if necessary
        Parameters
        ----------
        id: str
            The primary key of the minion that we want to use

        Returns
        -------

        """
        return self.value.format(id)

    def append_id(self, base_id, append_id):
        """
        Append ID to the end of a URL
        Parameters
        ----------
        base_id: str
            base id
        append_id: str
            Appended ID

        Returns
        -------

        """
        return self.add_id(base_id) + str(append_id) + "/"

    def strip_id(self):
        """
        Strip the id format space from the URL, so we can use it for posts
        Returns
        -------

        """
        return self.value.split("{}")[0]

    def resolve_url(self, base_id="", append_id="", no_id=False):
        """
        Resolve the url in regards to id in the str
        Parameters
        ----------
        base_id: str
            The base id for the url ex. /minion/*1*/
        append_id: str
            The appended id after the base id ex. /minion/1/jobs/*2*
        no_id: bool
            If True Strip the id space from the url

        Returns
        -------
        str
            The Url to append to the request
        """
        if base_id and not append_id:
            return self.add_id(base_id)
        elif base_id and append_id:
            return self.append_id(base_id, append_id)
        elif no_id:
            return self.strip_id()
        else:
            return str(self)
