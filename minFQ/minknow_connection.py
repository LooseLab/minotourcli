import datetime
import json
import logging
import os,sys
import threading
import time

import pandas as pd
from google.protobuf.json_format import MessageToJson

import minknow_api
from minFQ.utils import first_connect
from minknow_api.manager import Manager
from minknow_api.acquisition_pb2 import AcquisitionState, MinknowStatus
from minknow_api.protocol_pb2 import ProtocolState,ProtocolRunUserInfo
from minknow_api.device import get_device_type

from minFQ.minotourapi import MinotourAPI as MinotourAPINew

log = logging.getLogger(__name__)



class DeviceMonitor:
    """
    Monitor a flowcell position, for sequencing metrics
    """

    def __init__(self, args, api_connection, header, position_id, upload_data):
        """

        Parameters
        ----------
        args: argparse.Namespace
            Namespace for chosen arguments after parsing
        api_connection: minknow_api.Connection
            Connection to the flowcell position
        header: dict
            The header to set on the request
        position_id: str
            The name of the position, like MS0000 or X1
        upload_data: minFQ.utils.SequencingStatistics
            Statistics about files uploaded, and what files are watching
        """
        self.args = args
        # Set a status to hold what we are currently doing.
        self.device_active = False
        self.minknow_api_connection = api_connection
        # Here we need to check if we are good to run against this version.
        self.version = self.minknow_api_connection.instance.get_version_info().minknow.full
        self.device_type = get_device_type(self.minknow_api_connection).name
        # log.error(self.device_type)
        if get_device_type(self.minknow_api_connection).is_promethion_like():
            log.warning("This version of minFQ may not be compatible with PromethION.")
        self.acceptable_versions = []
        # if str(self.version) != "3.3.13":
        if not str(self.version) in ["3.3.35", "4.0.4"]:
            log.warning(
                "This version of minFQ {} may not be compatible with the MinKNOW version you are running.".format(self.version)
            )
            log.warning("As a consequence, live monitoring MAY NOT WORK.")
            log.warning("If you experience problems, let us know.")
        self.header = header
        self.upload_data = upload_data
        self.channels = self.minknow_api_connection.device.get_flow_cell_info().channel_count #this is ok
        self.channel_states = {i: None for i in range(1, self.channels + 1)}
        self.acquisition_status = ""
        self.interval = 30  # we will poll for updates every 30 seconds.
        self.long_interval = 30  # we have a short loop and a long loop
        self.position_id = position_id  # This has been remanme from self.minIONid

        self.computer_name = self.minknow_api_connection.instance.get_machine_id().machine_id #This isn't what we want - it reports Macbook-Pro for my computer but should report "DestroyerofWorlds" or similar.
        self.minknow_version = (
            self.minknow_api_connection.instance.get_version_info().minknow.full
        )
        self.minknow_status = self.minknow_api_connection.instance.get_version_info().protocols
        self.minotour_api = MinotourAPINew(
            self.args.host_name, self.args.port_number, self.header
        )
        self.minotour_api.test()
        # TODO 4.0 brings in streaming so we can stream a lot of these in threads instead
        self.disk_space_info = self.minknow_api_connection.instance.get_disk_space_info()
        self.flowcell_data = self.minknow_api_connection.device.get_flow_cell_info()
        # TODO just get or create
        minion = self.minotour_api.get_minion_by_name(self.position_id)
        if not minion:
            minion = self.minotour_api.create_minion(self.position_id)
        self.minotour_minion = minion
        self.minion_status = self.minotour_api.get_minion_status(self.minotour_minion)
        self.minotour_run_url = ""

        if self.minknow_api_connection.acquisition.current_status().acquisition_status != MinknowStatus.READY:
            self.acquisition_data = (
                    self.minknow_api_connection.acquisition.get_acquisition_info()
            )
        else:
            # if self.args.verbose:
            log.debug("No active run")
            self.acquisition_data = None

        thread_targets = [
            self.run_monitor,
            self.flowcell_monitor,
            self.run_information_monitor,
            self.get_messages,
            self.new_channel_state_monitor,
            self.new_histogram_monitor,
            self.jobs_monitor,
        ]
        for thread_target in thread_targets:
            threading.Thread(target=thread_target, args=(), daemon=True).start()
        first_connect()

    def disconnect_nicely(self):
        """
        User has ^C to quit minFQ. This function fires to let minoTour know.
        Returns
        -------

        """
        log.debug("Trying to disconnect nicely")
        self.minotour_api.update_minion_event(
            self.minotour_minion, self.computer_name, "unplugged"
        )
        try:
            self.minion_status["minKNOW_status"] = "unplugged"
        except:
            log.debug("Couldn't unplug MinION from website.")
        self.minion_status = self.minotour_api.update_minion_info_mt(
            self.minion_status, self.minotour_minion
        )

    def jobs_monitor(self):
        """
        This function will check the remote server for new jobs to be done.
        :return:
        """
        while True:
            log.debug("!!!!!!checking for jobs!!!!!!")
            jobs = self.minotour_api.get_minion_jobs(self.minotour_minion)
            log.debug(jobs)
            time.sleep(self.interval)
            for job in jobs:
                if job["job"] == "testmessage":
                    self.send_message(
                        1,
                        "minoTour is checking communication status with "
                        + str(self.minotour_minion["name"])
                        + ".",
                    )
                    self.minotour_api.complete_minion_job(self.minotour_minion, job)
                if job["job"] == "custommessage":
                    self.send_message(1, "minoTour: {}".format(job["custom"]))
                    self.minotour_api.complete_minion_job(self.minotour_minion, job)
                if job["job"] == "stopminion":
                    if self.args.enable_remote:
                        self.minknow_api_connection.protocol.stop_protocol()
                        self.send_message(
                            3, "minoTour was used to remotely stop your run."
                        )
                    self.minotour_api.complete_minion_job(self.minotour_minion, job)
                if job["job"] == "rename":
                    if self.args.enable_remote:
                        self.minknow_api_connection.protocol.set_sample_id(
                            sample_id=job["custom"]
                        )
                        self.send_message(
                            1, "minoTour renamed your run to {}".format(job["custom"])
                        )
                    self.minotour_api.complete_minion_job(self.minotour_minion, job)
                if job["job"] == "nameflowcell":
                    if self.args.enable_remote:
                        self.minknow_api_connection.device.set_user_specified_flow_cell_id(
                            id=job["custom"]
                        )
                        self.send_message(
                            1,
                            "minoTour renamed your flowcell to {}".format(
                                job["custom"]
                            ),
                        )
                    self.minotour_api.complete_minion_job(self.minotour_minion, job)
                if job["job"] == "startminion":
                    if self.args.enable_remote:

                        self.minknow_api_connection.protocol.start_protocol(
                            identifier=job["custom"]
                        )
                        self.send_message(
                            2, "minoTour attempted to start a run on your device."
                        )
                    self.minotour_api.complete_minion_job(self.minotour_minion, job)

    def flowcell_monitor(self):
        """

        Returns
        -------

        """
        while True:
            flowcellinfo = self.minknow_api_connection.device.stream_flow_cell_info()
            for event in flowcellinfo:
                log.debug(event)
                self.flowcell_data = event
                log.debug(self.get_flowcell_id())
                self.update_minion_info()

    def new_histogram_monitor(self):
        """
        Monitor the histogram output from minKnow. It is the best.
        Returns
        -------
        None

        """
        while True:
            if str(self.acquisition_status).startswith("ACQUISITION_RUNNING") or str(self.acquisition_status).startswith("ACQUISITION_STARTING"):
                ###We need to test if we are doing basecalling or not.
                self.run_information = self.minknow_api_connection.acquisition.get_current_acquisition_run()
                self.basecalling = self.run_information.config_summary.basecalling_enabled
                if self.basecalling:
                    rltype = 2
                else:
                    rltype = 1
                histogram_stream = self.minknow_api_connection.statistics.stream_read_length_histogram(
                    #poll_time=60,
                    #wait_for_processing=True,
                    read_length_type=rltype,
                    bucket_value_type=1,
                    acquisition_run_id=self.run_information.run_id,
                )
                try:
                    for histogram_event in histogram_stream:
                        # print (parsemessage(histogram_event))
                        log.debug(histogram_event)
                        self.histogram_data = histogram_event
                        if not str(self.acquisition_status).startswith("ACQUISITION_RUNNING") or not str(self.acquisition_status).startswith("ACQUISITION_STARTING"):
                            break
                except Exception as e:
                    # print ("Histogram Problem: {}".format(e))
                    log.error("histogram problem: {}".format(e))
                    break
            time.sleep(self.interval)
            pass

    def new_channel_state_monitor(self):
        while True:
            channel_states = self.minknow_api_connection.data.get_channel_states(
                wait_for_processing=True, first_channel=1, last_channel=512
            )
            try:
                for state in channel_states:
                    for channel in state.channel_states:  # print (state)
                        self.channel_states[int(channel.channel)] = channel.state_name
                if not str(self.acquisition_status).startswith("ACQUISITION_RUNNING") or not str(self.acquisition_status).startswith("ACQUISITION_STARTING"):
                    break
            except:
                #print ("error")
                pass
            time.sleep(self.interval)
            pass

    def duty_time_monitor(self):
        while True:
            log.debug("Duty Time Monitor Running: {}".format(self.acquisition_status))
            log.debug(str(self.acquisition_status))
            while str(self.acquisition_status).startswith("ACQUISITION_RUNNING") or str(self.acquisition_status).startswith("ACQUISITION_STARTING"):
                log.debug("fetching duty time")
                dutytime = self.minknow_api_connection.statistics.stream_duty_time(
                    wait_for_processing=True, step=60
                )
                if self.args.verbose:
                    for duty in dutytime:
                        log.debug(duty)
            time.sleep(1)

    def run_monitor(self):
        """
        Monitor whether or not a run has just started or stopped. Alerts Minotour in the event of run start/stop.
        Returns
        -------
        None
        """
        # TODO fixme Watcher is not used
        while True:
            for (
                acquisition_status
            ) in self.minknow_api_connection.acquisition.watch_current_acquisition_run():
                self.acquisition_status = AcquisitionState.Name(acquisition_status.state)
                if str(self.acquisition_status).startswith("ACQUISITION_RUNNING") or str(self.acquisition_status).startswith("ACQUISITION_STARTING"):
                    self.device_active = True
                    self.run_start()

                if not self.device_active and str(self.acquisition_status).startswith(
                    "ACQUISITION_FINISHING"
                ):
                    self.device_active = True
                    self.run_start()
                ###So - a run which is still basecalling will report as finishing - so we may need to spot this...
                if self.device_active and str(self.acquisition_status).startswith("ACQUISITION_COMPLETED"):
                    self.device_active = False
                    self.run_stop()
                log.debug(self.acquisition_status)

    def run_information_monitor(self):
        """
        Get information on the run via the minKnow RPC. Basically just sets class values for any data we can get.
        Returns
        -------
        None

        """
        while True:
            log.debug("Checking run info")
            try:
                self.acquisition_data = (
                    self.minknow_api_connection.acquisition.get_acquisition_info()
                )
            except:
                log.debug("No active run")
                self.acquisition_data = None
            self.temperature_data = self.minknow_api_connection.device.get_temperature()
            #ToDo: Check this code on a promethION.
            if str(self.device_type).startswith("PROMETHION"):
                self.minion_settings = (
                    self.minknow_api_connection.promethion_device.get_device_settings()
                )
            else:
                self.minion_settings = self.minknow_api_connection.minion_device.get_settings()
            self.bias_voltage = (
                self.minknow_api_connection.device.get_bias_voltage().bias_voltage
            )

            try:
                self.runinfo_api = self.minknow_api_connection.protocol.get_run_info()
            except:
                log.debug("Run Info not yet known.")
            try:
                self.sampleid = self.minknow_api_connection.protocol.get_run_info().user_info
            except:
                c = ProtocolRunUserInfo()
                c.sample_id.value = "Mux Scan"
                c.protocol_group_id.value = "Platform QC"
                self.sampleid = c
                log.debug("Sample ID not yet known.")
            log.debug("running update minion status")
            self.update_minion_info()

            if str(self.acquisition_status).startswith("ACQUISITION_RUNNING") or str(self.acquisition_status).startswith("ACQUISITION_STARTING"):
                self.run_information = self.minknow_api_connection.acquisition.get_current_acquisition_run()
                try:
                    #print ("Running Update MinION Stats")
                    log.debug("running update minion stats")
                    #print (self.run_primary_key)
                    if hasattr(self, "run_primary_key"):
                        self.update_minion_stats()

                except Exception as err:
                    log.error("Problem updating stats to device.", err)
                    pass

            time.sleep(self.interval)



class MinionManager(Manager):
    """
    manager for flowcell positions listed by minKNOW
    """

    def __init__(
        self, host="localhost", port=None, use_tls=False, args=None, header=None, upload_data=None
    ):
        print(port)
        super().__init__(host, port, use_tls)
        self.connected_positions = {}
        self.device_monitor_thread = threading.Thread(
            target=self.monitor_devices, args=()
        )
        self.device_monitor_thread.daemon = True
        self.device_monitor_thread.start()
        self.args = args
        self.header = header
        self.upload_data = upload_data

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
        while True:
            for position in self.flow_cell_positions():
                device_id = position.name
                if device_id not in self.connected_positions and position.running:
                    # TODO note that we cannot connect to a remote instance without an ip websocket
                    self.connected_positions[device_id] = DeviceMonitor(
                        self.args, position.connect(), self.header, device_id, self.upload_data
                    )
            time.sleep(5)

    def stop_monitoring(self):
        """
        Inform minoTour that we have interrupted monitoring, and disconnect from minoTour
        Stops device monitor for each posiiion.
        Returns
        -------
        None
        """
        for flowcell_name, connection in self.connected_positions.items():
            log.info("Disconnecting {} from the server.".format(flowcell_name))
            connection.disconnect_nicely()
        log.info("Stopped successfully.")
