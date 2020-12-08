import logging
import os
import time
import datetime
from collections import Counter
from google.protobuf.json_format import MessageToJson
import pytz
from grpc import RpcError
from urllib.parse import urlparse

from minknow_api.protocol_pb2 import ProtocolRunUserInfo

from minFQ.endpoints import EndPoint

log = logging.getLogger("minknow_connection")


def check_warnings(device_type, minknow_version):
    """
    Check to see if there any compatability warnings for minknow monitorng
    Parameters
    ----------
    device_type: str
        The device name for the sequencer connected to minKNOW. May be one of PROMETHION, GRIDION, MINION
    minknow_version: str
        The version of minknow that we are using.

    Returns
    -------

    """
    if device_type == "PROMETHION":
        log.warning("This version of minFQ may not be compatible with PromethION.")
    if minknow_version.startswith("3.3"):
        log.warning(
            "This version of minFQ may not be compatible with the MinKNOW version you are running."
        )
        log.warning("As a consequence, live monitoring MAY NOT WORK. We recommend using minknow 4.0.X")
        log.warning("If you experience problems, let us know.")


class RpcSafeConnection:
    """
    Get values from the RPC and except RPC errors correctly
    """
    def __init__(self, api_connection):
        """

        Parameters
        ----------
        api_connection: minknow_api.Connection
            Connection to the flowcell position
        """
        self.api_connection = api_connection

    def get_run_info(self):
        """
        Get the protocol service run info or None if error
        Returns
        -------
        minknow_api._support.MessageWrapper or None
            Message wrapper for the run information or None if error
        """
        try:
            return self.api_connection.protocol.get_run_info()
        except RpcError:
            log.debug("Failed to get protocol run info")
            return None

    def get_current_protocol_run(self):
        """
        Get thr protocol run from the RPC or return None upon error
        Returns
        -------
        minknow_api._support.MessageWrapper or None
            Message wrapper for the run information or None if error

        """
        try:
            return self.api_connection.protocol.get_current_protocol_run()
        except RpcError:
            log.debug("Failed to get current run info from protocol service")
            return None

    def get_acquisition_data(self):
        """
        Set the acquisition data on the device monitor class
        Parameters
        ----------
        Returns
        -------
        minknow_api._support.MessageWrapper
            The acquisition information for this position
        """
        try:
            return self.api_connection.acquisition.get_acquisition_info()
        except RpcError as e:
            log.debug(e)
            return None

    def get_current_acquisition_run(self):
        """
        get the current acquisition run
        Returns
        -------
        minknow_api._support.MessageWrapper
            The acquisition run information for this position
        """
        try:
            return self.api_connection.acquisition.get_current_acquisition_run()
        except RpcError as e:
            log.debug(e)
            return None

    def get_run_info_sample_name(self):
        """
        Get the run info sample name. or set it to Mux_scan or platform qc
        Returns
        -------

        """
        try:
            sample_id = self.api_connection.protocol.get_run_info().user_info
        except RpcError:
            c = ProtocolRunUserInfo()
            # TODO watch out here as this is fixing any unknown run as Platform QC
            c.sample_id.value = "Mux_scan"
            c.protocol_group_id.value = "Platform_QC"
            sample_id = c
            log.debug("Sample ID not yet known.")
        return sample_id


class LiveMonitoringActions(RpcSafeConnection):
    """
    Actions that we need to take when certain events are triggered in the course of sequencing. Also communicates with
    minoTpur
    """
    def __init__(self, api_connection, minotour_api, sequencing_statistics, header):
        """
        Initialise this
        Parameters
        ----------
        api_connection: minknow_api.Connection
            Connection to the flowcell position
        minotour_api: minFQ.minotourapi.MinotourAPI
            Class for convenience request to minoTOur
        sequencing_statistics: SequencingStatistics
            Track the fastq monitoring metrics and folders with this class
        header: dict
            The dict for request headers
        """
        self.api_connection = api_connection
        self.minotour_api = minotour_api
        self.sequencing_statistics = sequencing_statistics
        self.header = header
        self.long_interval = 30
        super().__init__(self.api_connection)

    def run_stop(self):
        """
        Stop a run - send a post request to minoTour, remove the folder from the sequencing statistics clsas
        Parameters
        ----------
        Returns
        -------

        """
        self.update_minion_event()
        folder_path = str(
            os.path.normpath(
                self.api_connection.protocol.get_current_protocol_run().output_path
            )
        )
        file_path = os.path.normpath(folder_path)
        if not self.args.no_fastq:
            if file_path in self.sequencing_statistics.directory_watch_list:
                time.sleep(self.long_interval)
                self.sequencing_statistics.directory_watch_list.remove(file_path)
                self.sequencing_statistics.update = True
        log.debug("run stop observed")

    def run_start(self):
        """
        This function will fire when a run first begins.
        Creates the run in the class and update the minion run info in minotour

        Returns
        -------
        None
        """
        self.update_minion_event()
        # We wait for 10 seconds to allow the run to start
        time.sleep(10)
        try:
            self.run_information = self.get_current_acquisition_run()
            # we need this information
            while not self.run_information:
                self.run_information = self.get_current_acquisition_run()
                time.sleep(1)
            self.create_run()
            log.debug("RUn created")
            # Grab the folder and if we are allowed, add it to the watchlist
            FolderPath = (
                self.api_connection.protocol.get_current_protocol_run().output_path
            )
            if not self.args.no_fastq:
                if str(os.path.normpath(FolderPath)) not in self.sequencing_statistics.directory_watch_list:
                    self.sequencing_statistics.directory_watch_list.append(str(os.path.normpath(FolderPath)))
            self.update_minion_run_info()
        except Exception as err:
            log.error("Problem starting run {}", err)

    def create_run(self):
        """
        Fired to create a run in Minotour, and return a hyperlinked URL to the database entry, and the run primary key.
        Parameters
        ----------
        Returns
        -------
        None

        """
        run_id = self.run_information.run_id
        run = self.minotour_api.get_json(EndPoint.RUNS, base_id=run_id, params="search_criteria=runid")
        if run:
            self.minotour_run_url = run["url"]
            self.run_primary_key = run["id"]
        else:
            # get or create a flowcell
            self.sample_id = self.get_run_info_sample_name()
            flowcell_name = "{}_{}".format(
                self.get_flowcell_id(), self.sample_id.sample_id.value
            ) if self.args.force_unique else self.get_flowcell_id()
            flowcell = self.minotour_api.get_json(EndPoint.FLOWCELL, base_id=flowcell_name,
                                                  params="search_criteria=name")["data"]
            log.debug(flowcell)
            if not flowcell:
                log.debug("Manually creating flowcell")
                flowcell = self.minotour_api.post(EndPoint.FLOWCELL, no_id=True, json={"name": flowcell_name})
            payload = {
                "name": self.sample_id.sample_id.value,
                "sample_name": self.sample_id.sample_id.value,
                "runid": run_id,
                "is_barcoded": False,
                "has_fastq": True,
                "flowcell": flowcell["url"],
                "minion": self.minion["url"],
                "start_time": str(self.run_information.start_time.ToDatetime().replace(tzinfo=pytz.UTC))
            }

            created_run = self.minotour_api.post(EndPoint.RUNS, json=payload, no_id=True)
            if not created_run:
                log.error("Run not created!")
            else:
                self.minotour_run_url = created_run["url"]
                self.run_primary_key = created_run["id"]  # I

        log.debug("***** self.run_primary_key: {}".format(self.run_primary_key))
        log.debug("**** run stats updated")

    def first_connect(self):
        """
        This function will run when we first connect to the MinION device.
        It will provide the information to minotour necessary to remotely control the minION device.
        Returns
        -------
        bool
            Device activity state.
        """
        log.debug("First connection observed")
        log.debug("Current acquistion status: {}".format(self.acquisition_status))
        self.update_minion_event()
        # set the device to active as it is currently sequencing
        if str(self.acquisition_status) in {"ACQUISITION_RUNNING", "ACQUISITION_STARTING"}:
            self.device_active = True
            return self.device_active

    def disconnect_nicely(self):
        """
        User has ^C to quit minFQ. This function fires to let minoTour know.
        Returns
        -------

        """
        log.debug("Trying to disconnect nicely")
        self.run_bool = False
        self.acquisition_status = "unplugged"
        self.update_minion_event()
        # todo we need to look at this to handle manual unplugged
        self.minion_status["minKNOW_status"] = "unplugged"
        self.minion_status = self.update_minion_info()

    def minknow_command(self):
        """
        This function will recieve commands for a specific minION and handle the interaction.
        :return:
        """
        pass

    def send_message(self, severity_level, message):
        """
        Send a message to be displayed in the minKnow log.
        Parameters
        ----------
        severity_level: int
            The severity level of the message. 0 - low, 1 - medium, 2- high
        message: str
            The message to be sent to the display

        Returns
        -------

        """
        self.api_connection.log.send_user_message(
            severity=severity_level, user_message=message
        )

    def get_flowcell_id(self):
        """
        Get the user specified flowcell ID if there is one, else get the flowcell ID that minKNOW reads from the actual
         flowcell
        Returns
        -------
        str
            Flowcell id
        """
        if self.flowcell_data.user_specified_flow_cell_id:
            flowcell_id = self.flowcell_data.user_specified_flow_cell_id
        else:
            flowcell_id = self.flowcell_data.flow_cell_id
        return flowcell_id

    def get_seq_device_settings(self):
        """
        Get the minion settings for the device based on the device type
        Parameters
        ----------

        Returns
        -------
        minknow_api._support.MessageWrapper
            The device settings for this minion
        """
        if str(self.device_type) == ("PROMETHION"):
            device_settings = (
                self.api_connection.promethion_device.get_device_settings()
            )
        else:
            device_settings = self.api_connection.minion_device.get_settings()
        return device_settings

    def update_minion_info(self):
        """
        Update the minion info concept in MinoTour server. This stores information for this position
         about the connected version of minknow and the computer it is running on.
        Parameters
        ----------

        Returns
        -------

        """
        current_script = self.api_connection.protocol.get_run_info().protocol_id if self.acquisition_data else "No Run"
        try:
            self.file_system_disk_space = self.api_connection.instance.get_disk_space_info().filesystem_disk_space_info[0]
        except RpcError as e:
            log.debug(e)
        file_system_disk_space = self.file_system_disk_space
        payload = {"minion": self.minion["url"], "minKNOW_status": self.acquisition_status,
                   "minKNOW_current_script": current_script,
                   "minKNOW_exp_script_purpose": self.api_connection.protocol.get_protocol_purpose().purpose,
                   "minKNOW_flow_cell_id": self.get_flowcell_id(),
                   "minKNOW_real_sample_rate": self.api_connection.device.get_sample_rate().sample_rate,
                   "minKNOW_asic_id": self.flowcell_data.asic_id_str,
                   "minKNOW_total_drive_space": file_system_disk_space.bytes_capacity,
                   "minKNOW_disk_space_till_shutdown": file_system_disk_space.bytes_when_alert_issued,
                   "minKNOW_disk_available": file_system_disk_space.bytes_available,
                   "minKNOW_warnings": file_system_disk_space.recommend_stop, "minknow_version": self.minknow_version,
                   "wells_per_channel": self.flowcell_data.wells_per_channel
                   }

        current_protocol_run = self.get_current_protocol_run()
        if current_protocol_run:
            if current_protocol_run.acquisition_run_ids:
                payload["minKNOW_script_run_id"] = current_protocol_run.acquisition_run_ids[0]

        if self.sample_id:
            payload["minKNOW_sample_name"] = self.sample_id.sample_id.value
            payload["minKNOW_run_name"] = self.sample_id.protocol_group_id.value

        if self.acquisition_data:
            payload[
                "read_length_type"
            ] = "BASECALLED BASES" if self.acquisition_data.config_summary.basecalling_enabled else "ESTIMATED BASES"

        if self.run_information:
            if hasattr(self.run_information, "run_id"):
                payload["minKNOW_hash_run_id"] = str(self.run_information.run_id)

        method_handle = self.minotour_api.put if self.minion_status else self.minotour_api.post
        self.minion_status = method_handle(EndPoint.MINION_STATUS, base_id=self.minion["id"], json=payload)

    def update_minion_event(self):
        """
        Update the event that minoTour has for this minion to match the currecnt acquistion status
        Returns
        -------
        None
        """
        if not self.acquisition_status:
            time.sleep(1)
        for info in self.minotour_api.minion_event_types:
            if info.get("name", "") == self.acquisition_status:
                minknow_status_url = info["url"]
        payload = {
            "computer_name": self.computer_name,
            "datetime": str(datetime.datetime.now()),
            "event": str(urlparse(minknow_status_url).path),
            "minION": str(self.minion["url"]),
        }
        self.minotour_api.post(EndPoint.MINION_EVENT, base_id=self.minion["id"], json=payload)

    def update_minion_run_info(self):
        """
        Update minion_run_info for this position in Minotour, sent once at the start of the run.
        Returns
        -------

        """
        payload = {
            "minion": self.minion["url"],
            "minKNOW_current_script": self.api_connection.protocol.get_run_info().protocol_id,
            "minKNOW_sample_name": self.sample_id.sample_id.value,
            "minKNOW_exp_script_purpose": self.api_connection.protocol.get_protocol_purpose().purpose,
            "minKNOW_flow_cell_id": self.get_flowcell_id(),
            "minKNOW_run_name": self.sample_id.sample_id.value,
            "run": self.minotour_run_url,
            "minKNOW_version": self.api_connection.instance.get_version_info().minknow.full,
            "minKNOW_hash_run_id": self.run_information.run_id,
            "minKNOW_script_run_id": self.api_connection.protocol.get_current_protocol_run().acquisition_run_ids[0],
            "minKNOW_real_sample_rate": self.api_connection.device.get_sample_rate().sample_rate,
            "minKNOW_asic_id": self.flowcell_data.asic_id_str,
            "minKNOW_start_time": self.run_information.start_time.ToDatetime().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "minKNOW_colours_string": MessageToJson(self.api_connection.analysis_configuration.get_channel_states_desc(),
                                                    preserving_proto_field_name=True,
                                                    including_default_value_fields=True,
                                                    ),
            "minKNOW_computer": self.computer_name,
            "target_temp": self.temperature_data.target_temperature,
            "flowcell_type": self.flowcell_data.user_specified_product_code,
        }

        payload.update(self.api_connection.protocol.get_context_info().context_info)
        run_info = self.get_run_info()
        if run_info.user_info.HasField("protocol_group_id"):
            payload["experiment_id"] = run_info.user_info.protocol_group_id.value
        else:
            payload["experiment_id"] = "Not Known"
        update_run_info = self.minotour_api.post(
            EndPoint.MINION_RUN_INFO,
            json=payload, base_id=self.run_primary_key
        )
        log.debug(update_run_info)

    def update_minion_stats(self):
        """
        Update the statistics about a run that we have recorded from minKnow.
        Sent to Minotour and stored in minIon run stats table.
        Contains information about the run, not just minKNOW/minION.
        Returns
        -------
        None
        """
        counted = Counter(self.channel_states_dict.values())
        payload = {
            "minion": str(self.minion["url"]),
            "run": self.minotour_run_url,
            "sample_time": str(datetime.datetime.now()),
            "event_yield": self.acquisition_data.yield_summary.selected_events,
            "asic_temp": self.temperature_data.minion.asic_temperature.value,
            "heat_sink_temp": self.temperature_data.minion.heatsink_temperature.value,
            "voltage_value": int(self.bias_voltage),
            "minKNOW_read_count":  self.acquisition_data.yield_summary.read_count,
            "estimated_selected_bases": self.acquisition_data.yield_summary.estimated_selected_bases,
        }
        payload.update(counted)
        if self.histogram_data:
            try:
                payload.update(
                    {
                        "minKNOW_histogram_values": str(
                            self.histogram_data.histogram_data[0].bucket_values
                        ),
                        "minKNOW_histogram_bin_width": self.histogram_data.bucket_ranges[
                            0
                        ].end,
                        # ToDo Determine if this actually exsits!
                        "actual_max_val": self.histogram_data.source_data_end,
                        "n50_data": self.histogram_data.histogram_data[0].n50,
                    }
                )
            except IndexError as e:
                log.error(e)
        if self.acquisition_data:
            payload.update(
                {"basecalled_bases": int(self.acquisition_data.yield_summary.basecalled_pass_bases) + int(self.acquisition_data.yield_summary.basecalled_fail_bases),
                 "basecalled_fail_read_count": self.acquisition_data.yield_summary.basecalled_fail_read_count,
                 "basecalled_pass_read_count": self.acquisition_data.yield_summary.basecalled_pass_read_count}
            )

        result = self.minotour_api.post(
            EndPoint.MINION_RUN_STATS,
            json=payload, base_id=self.run_primary_key
        )
        log.debug("This is our result: {}".format(result))
