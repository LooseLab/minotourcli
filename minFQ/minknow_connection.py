import logging
import threading
import time


from grpc import RpcError
import minknow_api
from minknow_api.manager import Manager
from minknow_api.acquisition_pb2 import AcquisitionState, MinknowStatus
from minknow_api.protocol_pb2 import ProtocolState, ProtocolRunUserInfo
from minknow_api.device import get_device_type

from minFQ.endpoints import EndPoint
from minFQ.minotourapi import MinotourAPI
from minFQ.minknow_connection_utils import (
    check_warnings,
    LiveMonitoringActions,
)

log = logging.getLogger(__name__)


class DeviceMonitor(LiveMonitoringActions):
    """
    Monitor a flowcell position, for sequencing metrics
    """

    def __init__(
        self, args, api_connection, header, position_id, sequencing_statistics
    ):
        """

        Parameters
        ----------
        args: argparse.NameSpace
            The argument name space
        api_connection: minknow_api.Connection
            Connection to the flowcell position
        header: dict
            The header to set on the request to the server
        position_id: str
            The name of the position, like MS0000 or X1
        sequencing_statistics: minFQ.utils.SequencingStatistics
            The metrics for the fastq uploading
        """
        self.args = args
        self.minotour_api = MinotourAPI(
            self.args.host_name, self.args.port_number, header
        )
        # Set a status to hold what we are currently doing for this device.
        self.device_active = False
        self.api_connection = api_connection
        self.minknow_version = (
            self.api_connection.instance.get_version_info().minknow.full
        )
        self.device_type = get_device_type(self.api_connection).name
        # Here we need to check if we are good to run against this version.
        check_warnings(self.device_type, self.minknow_version)
        self.header = header
        self.channel_count = (
            self.api_connection.device.get_flow_cell_info().channel_count
        )  # this is ok
        self.channel_states_dict = {i: None for i in range(1, self.channel_count + 1)}
        # self.status = AcquisitionState.ACQUISITION_COMPLETED
        self.acquisition_status = ""
        self.interval = 30  # we will poll for updates every 30 seconds.
        self.long_interval = 30  # we have a short loop and a long loop
        self.position_id = position_id  # This has been renamed from self.minIONid
        self.computer_name = (
            self.api_connection.instance.get_machine_id().machine_id
        )  # This isn't what we want - it reports Macbook-Pro for my computer but should report "DestroyerofWorlds" or similar.

        self.minotour_api.test()
        # TODO 4.0 brings in streaming so we can stream a lot of these in threads instead
        # Updated in Flowcell monitor thread
        self.flowcell_data = self.api_connection.device.get_flow_cell_info()
        # Get minotour minion record or create it if we don't have one
        self.minion = self.minotour_api.get_or_create(EndPoint.GET_MINION, params="search_criteria=name",
                                                      base_id=self.position_id,
                                                      json={"minION_name": self.position_id,
                                                            "name": self.position_id}, no_id=True)
        self.minion_status = self.minotour_api.get_json(EndPoint.MINION_STATUS, base_id=self.minion["id"])
        self.minotour_run_url = ""
        self.run_primary_key = ""
        self.run_bool = True
        self.acquisition_data = self.get_acquisition_data()
        # initialise histogram data
        self.histogram_data = None
        # initialise run information
        self.run_information = None
        self.base_calling_enabled = None
        # Set in the run_info
        self.temperature_data = None
        self.sample_id = None
        self.minion_settings = None
        self.bias_voltage = None
        self.run_info_api = None
        super().__init__(
            api_connection, self.minotour_api, sequencing_statistics, header
        )

        thread_targets = [
            self.run_monitor_thread,
            self.flowcell_monitor_thread,
            self.run_information_monitor_thread,
            self.get_messages_thread,
            self.channel_state_monitor_thread,
            self.histogram_monitor_thread,
            self.jobs_monitor_thread,
        ]
        for thread_target in thread_targets:
            threading.Thread(target=thread_target, args=(), daemon=True).start()
        self.first_connect()

    def jobs_monitor_thread(self):
        """
        Check the minoTour server for jobs to be sent to minKnow and perform them.
        Returns
        -------

        """
        while self.run_bool:
            data = self.minotour_api.get_json(EndPoint.MINION_CONTROL, base_id=self.minion["id"])
            log.debug(data)
            time.sleep(self.interval)
            for job in data:
                if job["job"] == "test_message":
                    self.send_message(
                        1,
                        "minoTour is checking communication status with "
                        + str(self.minion["name"])
                        + ".",
                    )
                elif job["job"] == "custom_message":
                    self.send_message(1, "minoTour: {}".format(job["custom"]))
                elif job["job"] == "stop_minion":
                    if self.args.enable_remote:
                        self.api_connection.protocol.stop_protocol()
                        self.send_message(
                            3, "minoTour was used to remotely stop your run."
                        )
                elif job["job"] == "rename":
                    if self.args.enable_remote:
                        self.api_connection.protocol.set_sample_id(
                            sample_id=job["custom"]
                        )
                        self.send_message(
                            1, "minoTour renamed your run to {}".format(job["custom"])
                        )
                elif job["job"] == "name_flowcell":
                    if self.args.enable_remote:
                        self.api_connection.device.set_user_specified_flow_cell_id(
                            id=job["custom"]
                        )
                        self.send_message(
                            1,
                            "minoTour renamed your flowcell to {}".format(
                                job["custom"]
                            ),
                        )
                elif job["job"] == "start_minion":
                    if self.args.enable_remote:
                        self.api_connection.protocol.start_protocol(
                            identifier=job["custom"]
                        )
                        self.send_message(
                            2, "minoTour attempted to start a run on your device."
                        )
                else:
                    continue
                self.minotour_api.post(EndPoint.MINION_CONTROL, base_id=self.minion["id"], append_id=job["id"], json={})

    def flowcell_monitor_thread(self):
        """
        Monitor flowcell information for this position, and update the class value stored for it.
        Returns
        -------

        """
        while self.run_bool:
            flowcell_info_response = self.api_connection.device.stream_flow_cell_info()
            for flowcell_info in flowcell_info_response:
                self.flowcell_data = flowcell_info
                self.update_minion_info()

    def histogram_monitor_thread(self):
        """
        Monitor the histogram stream output from minKnow. Set the data on the class. If a run is ongoing, we stay in the
        stream for loop. If a run is not, we check for one every 30 seconds until we go back in the stream loop
        Returns
        -------
        None

        """
        while self.run_bool:
            if str(self.acquisition_status) in {
                "ACQUISITION_STARTING",
                "ACQUISITION_RUNNING",
            }:
                # get the purpose of this sequencing
                purpose = self.api_connection.protocol.get_protocol_purpose().purpose
                if purpose == "sequencing_run":
                    # We need to test if we are doing basecalling or not.
                    self.run_information = (
                        self.get_current_acquisition_run()
                    )
                    self.base_calling_enabled = False
                    if self.run_information:
                        self.base_calling_enabled = (
                            self.run_information.config_summary.basecalling_enabled
                        )
                    rltype = 2 if self.base_calling_enabled else 1
                    try:
                        histogram_stream = self.api_connection.statistics.stream_read_length_histogram(
                            read_length_type=rltype,
                            bucket_value_type=1,
                            acquisition_run_id=self.run_information.run_id,
                        )
                        for histogram_event in histogram_stream:
                            self.histogram_data = histogram_event
                            if self.acquisition_status not in {
                                "ACQUISITION_RUNNING", "ACQUISITION_STARTING"
                            }:
                                break
                    except Exception as e:
                        log.error("histogram problem: {}".format(e))
                        continue
            time.sleep(self.interval)

    def channel_state_monitor_thread(self):
        """
        Thread to monitor the channel states as put out by minknow. Sets them on the class where they are uploaded
        by a call to update_minion_run_stats somewhere else.
        Returns
        -------
        None

        """
        while self.run_bool:
            if str(self.acquisition_status) in {
                "ACQUISITION_RUNNING",
                "ACQUISITION_STARTING"
            }:
                purpose = self.api_connection.protocol.get_protocol_purpose().purpose
                if purpose == "sequencing_run":
                    last_channel = self.flowcell_data.channel_count
                    channel_states = self.api_connection.data.get_channel_states(
                        wait_for_processing=True,
                        first_channel=1,
                        last_channel=last_channel,
                    )
                    try:
                        for state in channel_states:
                            for channel in state.channel_states:
                                self.channel_states_dict[
                                    int(channel.channel)
                                ] = channel.state_name
                        if str(self.acquisition_status) not in {
                            "ACQUISITION_RUNNING",
                            "ACQUISITION_STARTING"
                        }:
                            break
                    except Exception as e:
                        log.error("Chan state error: {}".format(e))
            time.sleep(self.interval)

    def run_monitor_thread(self):
        """
        Monitor whether or not a run has just started or stopped. Alerts Minotour in the event of run start/stop.
        Returns
        -------
        None
        """
        while self.run_bool:
            for (
                acquisition_status
            ) in self.api_connection.acquisition.watch_current_acquisition_run():
                self.acquisition_status = AcquisitionState.Name(
                    acquisition_status.state
                )
                if not self.device_active and str(self.acquisition_status) in {
                    "ACQUISITION_RUNNING",
                    "ACQUISITION_STARTING",
                    "ACQUISITION_FINISHING",
                }:
                    self.device_active = True
                    self.run_start()
                if (
                    self.device_active
                    and str(self.acquisition_status) == "ACQUISITION_COMPLETED"
                ):
                    self.device_active = False
                    self.run_stop()
                log.debug(self.acquisition_status)

    def run_information_monitor_thread(self):
        """
        Get information on the run via the minKnow RPC. Basically just sets class values for any data we can get.
        Returns
        -------
        None

        """
        while self.run_bool:
            log.debug("Checking run info")
            self.acquisition_data = self.get_acquisition_data()
            self.temperature_data = self.api_connection.device.get_temperature()
            # ToDo: Check this code on a promethION.
            self.bias_voltage = (
                self.api_connection.device.get_bias_voltage().bias_voltage
            )
            self.run_info_api = self.get_run_info()
            self.sample_id = self.get_run_info_sample_name()
            self.update_minion_info()
            if str(self.acquisition_status) in {"ACQUISITION_RUNNING", "ACQUISITION_STARTING"}:
                self.run_information = (
                    self.api_connection.acquisition.get_current_acquisition_run()
                )
                log.debug("running update minion stats")
                if self.run_primary_key:
                    self.update_minion_stats()
            time.sleep(self.interval)

    def get_messages_thread(self):
        """
        Get messages from the minKnow client for this flow cell. Include message seen from this flowcell but in older runs.
        Returns
        -------

        """
        while self.run_bool:
            if not self.minotour_run_url:
                time.sleep(5)
                continue
            messages = self.api_connection.log.get_user_messages(
                include_old_messages=True
            )
            for message in messages:
                payload = {
                    "minion": self.minion["url"],
                    "message": message.user_message,
                    "identifier": message.identifier,
                    "severity": message.severity,
                    "timestamp": message.time.ToDatetime().strftime(
                        "%Y-%m-%d %H:%M:%S.%f"
                    )[:-3],
                    "run": self.minotour_run_url
                }
                self.minotour_api.post(EndPoint.MINION_MESSAGES, base_id=self.minion["id"], json=payload)


class MinionManager(Manager):
    """
    manager for flowcell positions listed by minKNOW
    """

    def __init__(
        self,
        host="localhost",
        port=None,
        use_tls=False,
        args=None,
        header=None,
        sequencing_statistics=None,
    ):
        """

        Parameters
        ----------
        host: str
            The host that minknow server is being served on
        port: int or None
            Default None. IF None, will be defaulted to 9501, the GRPC port for minKNow
        use_tls: bool
            Default False. Use TLS connection
        args: argparse.NameSpace
            The command line arguments after parsing
        header: dict
            The header for the requests to minoTour server - for authorisation
        sequencing_statistics: minFQ.utils.SequencingStatistics
            The metrics for tracking fastq sequencing
        """
        super().__init__(host, port, use_tls)
        self.monitor = True
        self.connected_positions = {}
        self.device_monitor_thread = threading.Thread(
            target=self.monitor_devices, args=()
        )
        self.device_monitor_thread.daemon = True
        self.device_monitor_thread.start()
        self.args = args
        self.header = header
        self.sequencing_statistics = sequencing_statistics

    @property
    def count(self):
        """Count of connected sequencing flowcells listed in the manager"""
        return len(self.connected_positions)

    def monitor_devices(self):
        """
        Monitor devices to see if they are active. If active initialise device monitor class for each flow cell position.
        Returns
        -------

        """
        while self.monitor:
            for position in self.flow_cell_positions():
                # print (position)
                device_id = position.name
                if device_id not in self.connected_positions and position.running:
                    # TODO note that we cannot connect to a remote instance without an ip websocket
                    self.connected_positions[device_id] = DeviceMonitor(
                        self.args,
                        position.connect(),
                        self.header,
                        device_id,
                        self.sequencing_statistics,
                    )
            time.sleep(5)
        print("Stopped successfully.")

    def stop_monitoring(self):
        """
        Inform minoTour that we have interrupted monitoring, and disconnect from minoTour
        Stops device monitor for each position.
        Returns
        -------
        None
        """
        for flowcell_name, connection in self.connected_positions.items():
            log.info("Disconnecting {} from the server.".format(flowcell_name))
            connection.disconnect_nicely()
        self.monitor = False
