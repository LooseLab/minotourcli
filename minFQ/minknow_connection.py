import datetime
import json
import logging
import os, sys
import threading
import time

import pandas as pd
from google.protobuf.json_format import MessageToJson

import minknow_api
from minknow_api.manager import Manager
from minknow_api.acquisition_pb2 import AcquisitionState, MinknowStatus
from minknow_api.protocol_pb2 import ProtocolState, ProtocolRunUserInfo
from minknow_api.device import get_device_type

from minFQ.minotourapi import MinotourAPI as MinotourAPINew

log = logging.getLogger(__name__)


class DeviceMonitor:
    """
    Monitor a flowcell position, for sequencing metrics
    """

    def __init__(self, args, api_connection, header, position_id):
        """

        Parameters
        ----------
        args: argparse.NameSpace
            The argument name space
        api_connection: minknow_api.Connection
            Connection to the flowcell position
        header: dict
            The header to set on the request
        position_id: str
            The name of the position, like MS0000 or X1
        """
        self.args = args
        # Set a status to hold what we are currently doing.
        self.device_active = False
        self.api_connection = api_connection
        # Here we need to check if we are good to run against this version.

        self.version = self.api_connection.instance.get_version_info().minknow.full

        self.device_type = get_device_type(self.api_connection).name
        # log.error(self.device_type)
        if str(self.device_type).startswith("PROMETHION"):
            log.warning(self.device_type)
            log.warning("This version of minFQ may not be compatible with PromethION.")
            # sys.exit()
        # if str(self.version) != "3.3.13":
        if not str(self.version).startswith("3.3"):
            log.warning(self.version)
            log.warning(
                "This version of minFQ may not be compatible with the MinKNOW version you are running."
            )
            log.warning("As a consequence, live monitoring MAY NOT WORK.")
            log.warning("If you experience problems, let us know.")
            # sys.exit()
        self.header = header
        self.channels = (
            self.api_connection.device.get_flow_cell_info().channel_count
        )  # this is ok
        self.channel_states = {i: None for i in range(1, self.channels + 1)}
        # self.status = AcquisitionState.ACQUISITION_COMPLETED
        self.status = ""
        self.interval = 30  # we will poll for updates every 30 seconds.
        self.long_interval = 30  # we have a short loop and a long loop
        self.position_id = position_id  # This has been remanme from self.minIONid

        self.computer_name = (
            self.api_connection.instance.get_machine_id().machine_id
        )  # This isn't what we want - it reports Macbook-Pro for my computer but should report "DestroyerofWorlds" or similar.
        self.minknow_version = (
            self.api_connection.instance.get_version_info().minknow.full
        )
        self.minknow_status = self.api_connection.instance.get_version_info().protocols
        self.minotour_api = MinotourAPINew(
            self.args.host_name, self.args.port_number, self.header
        )
        self.minotour_api.test()
        # TODO 4.0 brings in streaming so we can stream a lot of these in threads instead
        self.disk_space_info = self.api_connection.instance.get_disk_space_info()
        self.flowcell_data = self.api_connection.device.get_flow_cell_info()
        minion = self.minotour_api.get_minion_by_name(self.position_id)
        if not minion:
            minion = self.minotour_api.create_minion(self.position_id)
        self.minion = minion
        self.minIONstatus = self.minotour_api.get_minion_status(self.minion)
        self.minotour_run_url = ""
        self.run_bool = True
        if (
            self.api_connection.acquisition.current_status().status
            != MinknowStatus.READY
        ):
            self.acquisition_data = (
                # self.api_connection.acquisition.current_status().status
                self.api_connection.acquisition.get_acquisition_info()
            )
        else:
            # if self.args.verbose:
            log.debug("No active run")
            self.acquisition_data = None
        # initialise histogram dataw
        self.histogram_data = None

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
        self.first_connect()

    def disconnect_nicely(self):
        """
        User has ^C to quit minFQ. This function fires to let minoTour know.
        Returns
        -------

        """
        log.debug("Trying to disconnect nicely")
        self.run_bool = False
        self.minotour_api.update_minion_event(
            self.minion, self.computer_name, "unplugged"
        )
        try:
            self.minIONstatus["minKNOW_status"] = "unplugged"
        except:
            log.debug("Couldn't unplug MinION from website.")
        self.minIONstatus = self.minotour_api.update_minion_info_mt(
            self.minIONstatus, self.minion
        )

    def first_connect(self):
        """
        This function will run when we first connect to the MinION device.
        It will provide the information to minotour necessary to remotely control the minION device.
        :return:
        """
        log.debug("First connection observed")
        log.debug("All is well with connection. {}".format(self.minion))
        # TODO change to use the minknow status/state
        self.minotour_api.update_minion_event(self.minion, self.computer_name, "active")
        # if self.status==AcquisitionState.ACQUISITION_RUNNING:

        if str(self.status).startswith("ACQUISITION_RUNNING") or str(
            self.status
        ).startswith("ACQUISITION_STARTING"):
            self.device_active = True
            # self.run_start()

    def run_start(self):
        """
        This function will fire when a run first begins.
        It will drive the creation of a run.
        :return:
        """
        self.minotour_api.update_minion_event(
            self.minion, self.computer_name, "sequencing"
        )

        log.debug("run start observed")
        log.debug("MINION:", self.minion)
        # We wait for 10 seconds to allow the run to start
        time.sleep(self.interval)
        try:
            self.run_information = (
                self.api_connection.acquisition.get_current_acquisition_run()
            )
            self.create_run(self.run_information.run_id)
            log.debug("run created!!!!!!!")
            #### Grab the folder and if we are allowed, add it to the watchlist?
            FolderPath = (
                self.api_connection.protocol.get_current_protocol_run().output_path
            )
            # print ("New Run Seen {}".format(FolderPath))
            if not self.args.noFastQ:
                if FolderPath not in self.args.WATCHLIST:
                    # print (FolderPath)
                    self.args.WATCHLIST.append(str(os.path.normpath(FolderPath)))
                    # self.args.WATCHLIST.append(str(os.path.normpath("/Library/MinKNOW/data/./TestingRunDetection/Testing/20200227_1334_MS00000_FAG12345_73228e51")))

            self.update_minion_run_info()
            log.debug("update minion run info complete")

        except Exception as err:
            log.error("Problem:", err)

    def update_minion_run_info(self):
        """
        Update the minion_run_info table in Minotour, sent once at the start of the run.
        Returns
        -------

        """
        payload = {
            "minion": str(self.minion["url"]),
            "minKNOW_current_script": str(
                self.api_connection.protocol.get_run_info().protocol_id
            ),
            "minKNOW_sample_name": str(self.sampleid.sample_id.value),
            "minKNOW_exp_script_purpose": str(
                self.api_connection.protocol.get_protocol_purpose()
            ),
            "minKNOW_flow_cell_id": self.get_flowcell_id(),
            "minKNOW_run_name": str(self.sampleid.sample_id.value),
            "run": self.minotour_run_url,
            "minKNOW_version": str(
                self.api_connection.instance.get_version_info().minknow.full
            ),
            "minKNOW_hash_run_id": str(self.run_information.run_id),
            "minKNOW_script_run_id": str(
                self.api_connection.protocol.get_current_protocol_run().acquisition_run_ids[
                    0
                ]
            ),
            "minKNOW_real_sample_rate": int(
                str(self.api_connection.device.get_sample_rate().sample_rate)
            ),
            "minKNOW_asic_id": self.flowcell_data.asic_id_str,
            "minKNOW_start_time": self.run_information.start_time.ToDatetime().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "minKNOW_colours_string": MessageToJson(
                self.api_connection.analysis_configuration.get_channel_states_desc(),
                preserving_proto_field_name=True,
                including_default_value_fields=True,
            ),
            "minKNOW_computer": str(self.computer_name),
            "target_temp": self.temperature_data.target_temperature,
            "flowcell_type": self.flowcell_data.user_specified_product_code,
        }

        context_info = self.api_connection.protocol.get_context_info().context_info
        for key in context_info:
            payload[key] = context_info[key]
        run_info = self.api_connection.protocol.get_run_info()
        if run_info.user_info.HasField("protocol_group_id"):
            payload["experiment_id"] = run_info.user_info.protocol_group_id.value
        else:
            payload["experiment_id"] = "Not Known"

        update_run_info = self.minotour_api.update_minion_run_info(
            payload, self.run_primary_key
        )
        log.debug(update_run_info)

    def create_run(self, runid):
        """
        Fired to create a run in Minotour, and return a hyperlinked URL to the database entry, and the run primary key.
        Parameters
        ----------
        runid: str
            The string of the run ID hash as provided by minknow

        Returns
        -------
        None

        """
        log.debug(self.minotour_api)
        self.minotour_api.test()
        run = self.minotour_api.get_run_by_runid(runid)
        log.debug(run)
        if not run:
            log.debug(">>> no run {}".format(runid))
            #
            # get or create a flowcell
            #
            if self.args.force_unique:
                flowcell_name = "{}_{}".format(
                    self.get_flowcell_id(), self.sampleid.sample_id.value
                )
            else:
                flowcell_name = self.get_flowcell_id()
            flowcell = self.minotour_api.get_flowcell_by_name(flowcell_name)["data"]
            log.debug(flowcell)
            if not flowcell:
                log.debug(">>> no flowcell")

                flowcell = self.minotour_api.create_flowcell(flowcell_name)
            is_barcoded = False  # TODO do we known this info at this moment? This can be determined from run info.
            has_fastq = True  # TODO do we known this info at this moment? This can be determined from run info
            create_run = self.minotour_api.create_run(
                self.sampleid.sample_id.value,
                runid,
                is_barcoded,
                has_fastq,
                flowcell,
                self.minion,
                self.run_information.start_time.ToDatetime().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            )
            log.debug(">>> after self.minotourapi.create_run")
            if not create_run:
                log.error("Run not created!")
            else:
                log.info(create_run)
                self.minotour_run_url = create_run["url"]
                self.run_primary_key = create_run["id"]  # I
        else:
            self.minotour_run_url = run["url"]
            self.run_primary_key = run["id"]
        log.debug("***** self.run_primary_key: {}".format(self.run_primary_key))
        log.debug("**** run stats updated")

    def run_stop(self):
        """
        This function will clean up when a run finishes.
        :return:
        """
        ## ToDo We need to remove the run from the rundict when we stop a run to prevent massive memory problems.
        self.minotour_api.update_minion_event(self.minion, self.computer_name, "active")
        FolderPath = str(
            os.path.normpath(
                self.api_connection.protocol.get_current_protocol_run().output_path
            )
        )
        if not self.args.noFastQ:
            if FolderPath in self.args.WATCHLIST:
                time.sleep(self.long_interval)
                self.args.WATCHLIST.remove(FolderPath)
                self.args.update = True
        log.debug("run stop observed")

    def jobs_monitor(self):
        """
        This function will check the remote server for new jobs to be done.
        :return:
        """
        while self.run_bool:
            log.debug("!!!!!!checking for jobs!!!!!!")
            jobs = self.minotour_api.get_minion_jobs(self.minion)
            log.debug(jobs)
            time.sleep(self.interval)
            for job in jobs:
                if job["job"] == "testmessage":
                    self.sendmessage(
                        1,
                        "minoTour is checking communication status with "
                        + str(self.minion["name"])
                        + ".",
                    )
                    self.minotour_api.complete_minion_job(self.minion, job)
                if job["job"] == "custommessage":
                    self.sendmessage(1, "minoTour: {}".format(job["custom"]))
                    self.minotour_api.complete_minion_job(self.minion, job)
                if job["job"] == "stopminion":
                    if self.args.enable_remote:
                        self.api_connection.protocol.stop_protocol()
                        self.sendmessage(
                            3, "minoTour was used to remotely stop your run."
                        )
                    self.minotour_api.complete_minion_job(self.minion, job)
                if job["job"] == "rename":
                    if self.args.enable_remote:
                        self.api_connection.protocol.set_sample_id(
                            sample_id=job["custom"]
                        )
                        self.sendmessage(
                            1, "minoTour renamed your run to {}".format(job["custom"])
                        )
                    self.minotour_api.complete_minion_job(self.minion, job)
                if job["job"] == "nameflowcell":
                    if self.args.enable_remote:
                        self.api_connection.device.set_user_specified_flow_cell_id(
                            id=job["custom"]
                        )
                        self.sendmessage(
                            1,
                            "minoTour renamed your flowcell to {}".format(
                                job["custom"]
                            ),
                        )
                    self.minotour_api.complete_minion_job(self.minion, job)
                if job["job"] == "startminion":
                    if self.args.enable_remote:

                        self.api_connection.protocol.start_protocol(
                            identifier=job["custom"]
                        )
                        self.sendmessage(
                            2, "minoTour attempted to start a run on your device."
                        )
                    self.minotour_api.complete_minion_job(self.minion, job)

    def minknow_command(self):
        """
        This function will recieve commands for a specific minION and handle the interaction.
        :return:
        """
        pass

    def get_flowcell_id(self):
        # ToDo make this function work out if we need to create a flowcell id for this run.

        if len(self.flowcell_data.user_specified_flow_cell_id) > 0:
            log.debug("We have a self named flowcell")
            flowcell_id = self.flowcell_data.user_specified_flow_cell_id
        else:
            log.debug("the flowcell id is fixed")
            flowcell_id = self.flowcell_data.flow_cell_id

        return flowcell_id

    def flowcell_monitor(self):
        """

        Returns
        -------

        """
        while self.run_bool:
            flowcellinfo = self.api_connection.device.stream_flow_cell_info()
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
        while self.run_bool:
            if str(self.status).startswith("ACQUISITION_RUNNING") or str(
                self.status
            ).startswith("ACQUISITION_STARTING"):
                ###We need to test if we are doing basecalling or not.
                self.run_information = (
                    self.api_connection.acquisition.get_current_acquisition_run()
                )
                self.basecalling = (
                    self.run_information.config_summary.basecalling_enabled
                )
                if self.basecalling:
                    rltype = 2
                else:
                    rltype = 1
                try:
                    histogram_stream = self.api_connection.statistics.stream_read_length_histogram(
                        # poll_time=60,
                        # wait_for_processing=True,
                        read_length_type=rltype,
                        bucket_value_type=1,
                        acquisition_run_id=self.run_information.run_id,
                    )
                    for histogram_event in histogram_stream:
                        log.debug(histogram_event)
                        self.histogram_data = histogram_event
                        if not str(self.status).startswith(
                            "ACQUISITION_RUNNING"
                        ) or not str(self.status).startswith("ACQUISITION_STARTING"):
                            break
                except Exception as e:
                    # print ("Histogram Problem: {}".format(e))
                    log.error("histogram problem: {}".format(e))
                    continue
            time.sleep(self.interval)
            pass

    def new_channel_state_monitor(self):
        while self.run_bool:
            channel_states = self.api_connection.data.get_channel_states(
                wait_for_processing=True, first_channel=1, last_channel=512
            )
            try:
                for state in channel_states:
                    for channel in state.channel_states:  # print (state)
                        self.channel_states[int(channel.channel)] = channel.state_name
                if not str(self.status).startswith("ACQUISITION_RUNNING") or not str(
                    self.status
                ).startswith("ACQUISITION_STARTING"):
                    break
            except:
                # print ("error")
                pass
            time.sleep(self.interval)
            pass

    def dutytimemonitor(self):
        while self.run_bool:
            log.debug("Duty Time Monitor Running: {}".format(self.status))
            log.debug(str(self.status))
            while str(self.status).startswith("ACQUISITION_RUNNING") or str(
                self.status
            ).startswith("ACQUISITION_STARTING"):
                log.debug("fetching duty time")
                dutytime = self.api_connection.statistics.stream_duty_time(
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
        while self.run_bool:
            for (
                acquisition_status
            ) in self.api_connection.acquisition.watch_current_acquisition_run():
                self.status = AcquisitionState.Name(acquisition_status.state)
                if str(self.status).startswith("ACQUISITION_RUNNING") or str(
                    self.status
                ).startswith("ACQUISITION_STARTING"):
                    self.device_active = True
                    self.run_start()

                if not self.device_active and str(self.status).startswith(
                    "ACQUISITION_FINISHING"
                ):
                    self.device_active = True
                    self.run_start()
                ###So - a run which is still basecalling will report as finishing - so we may need to spot this...
                if self.device_active and str(self.status).startswith(
                    "ACQUISITION_COMPLETED"
                ):
                    self.device_active = False
                    self.run_stop()
                log.debug(self.status)

    def update_minion_info(self):
        """
        Update the minion status information. Send it to minotour.
        Data may be None, if it is not present in the MinKnow status.
        Logic is supposed to be just information about MinKNOW/the minION device.
        Returns
        -------
        None

        """
        # if len(self.acquisition_data) < 1:

        ### changing as acquisition data will be None if nothing in it
        log.debug(self.acquisition_data)
        if self.acquisition_data is not None:
            minknowstatus = AcquisitionState.Name(self.acquisition_data.state)
            current_script = self.api_connection.protocol.get_run_info().protocol_id
        else:
            current_script = "Nothing Running"
            # ToDO: move minknowstatus to MinKNOWStatus object and work out how to handle a first connect with no active or previous run
            minknowstatus = "No Run"

        if not self.disk_space_info:
            self.disk_space_info = self.api_connection.instance.get_disk_space_info()
            log.debug(self.disk_space_info)

        payload = {
            "minion": str(self.minion["url"]),
            "minKNOW_status": minknowstatus,
            "minKNOW_current_script": current_script,
            "minKNOW_exp_script_purpose": self.api_connection.protocol.get_protocol_purpose().purpose,
            "minKNOW_flow_cell_id": self.get_flowcell_id(),
            "minKNOW_real_sample_rate": self.api_connection.device.get_sample_rate().sample_rate,
            "minKNOW_asic_id": self.flowcell_data.asic_id_str,
            "minKNOW_total_drive_space": self.disk_space_info.filesystem_disk_space_info[
                0
            ].bytes_capacity,
            "minKNOW_disk_space_till_shutdown": self.disk_space_info.filesystem_disk_space_info[
                0
            ].bytes_when_alert_issued,
            "minKNOW_disk_available": self.disk_space_info.filesystem_disk_space_info[
                0
            ].bytes_available,
            "minKNOW_warnings": self.disk_space_info.filesystem_disk_space_info[
                0
            ].recommend_stop,
            "minknow_version": self.minknow_version,
        }
        try:
            payload[
                "minKNOW_script_run_id"
            ] = self.api_connection.protocol.get_current_protocol_run().acquisition_run_ids[
                0
            ]
        except:
            # print ("!!!!!! big error")
            pass
        if hasattr(self, "sampleid"):
            log.debug(self.sampleid)
            log.debug(type(self.sampleid))
            log.debug(dir(self.sampleid))
            payload["minKNOW_sample_name"] = str(self.sampleid.sample_id.value)
            payload["minKNOW_run_name"] = str(self.sampleid.protocol_group_id.value)

        if self.acquisition_data:
            payload["read_length_type"] = "BASECALLED BASES" if self.acquisition_data.config_summary.basecalling_enabled else "ESTIMATED BASES"

        if hasattr(self, "run_information"):
            if hasattr(self.run_information, "run_id"):
                payload["minKNOW_hash_run_id"] = str(self.run_information.run_id)

        if hasattr(self, "runinfo_api"):
            payload["wells_per_channel"] = self.runinfo_api.flow_cell.wells_per_channel

        if self.minIONstatus:  # i.e the minION status already exists

            self.minIONstatus = self.minotour_api.update_minion_info_mt(
                payload, self.minion
            )

        else:

            self.minIONstatus = self.minotour_api.create_minion_info_mt(
                payload, self.minion
            )

    def update_minion_stats(self):
        """
        Update the statistics about a run that we have recorded from minKnow.
        Sent to Minotour and stored in minIon run stats table.
        Contains information about the run, not just minKNOW/minION.
        Returns
        -------
        None
        """

        asictemp = self.temperature_data.minion.asic_temperature.value
        heatsinktemp = self.temperature_data.minion.heatsink_temperature.value
        biasvoltage = int(self.bias_voltage)
        voltage_val = int(self.bias_voltage)  # todo this likely is wrong
        voltage_value = biasvoltage  # todo check this = probably wrong
        yield_val = self.acquisition_data.yield_summary.selected_events
        read_count = self.acquisition_data.yield_summary.read_count
        channel_panda = pd.DataFrame.from_dict(
            self.channel_states, orient="index", dtype=None
        )
        channel_dict = {}
        channel_dict["strand"] = 0
        channel_dict["adapter"] = 0
        channel_dict["good_single"] = 0
        channel_dict["pore"] = 0
        try:
            channelpandastates = channel_panda.groupby([0,]).size()
            # print (channelpandastates)
            log.debug(channelpandastates)
            for state, value in channelpandastates.iteritems():
                log.debug("{} {}".format(state, value))
                #    print (state,value)
                channel_dict[state] = value
            # print ("\n\n\n\n\n\n")
            instrand = 0  # channeldict["strand"]+channeldict["adapter"]
            openpore = 0  # channeldict["good_single"]+channeldict["pore"]
            meanratio = 0  # todo work out if we can still do this
        except:
            # ("error")
            meanratio = 0
            instrand = 0
            openpore = 0
            pass

        # Capturing the histogram data from MinKNOW
        # print (self.runinformation)

        payload = {
            "minion": str(self.minion["url"]),
            "run": self.minotour_run_url,
            "sample_time": str(datetime.datetime.now()),
            "event_yield": yield_val,
            "asic_temp": asictemp,
            "heat_sink_temp": heatsinktemp,
            "voltage_value": voltage_value,
            "mean_ratio": meanratio,
            "open_pore": openpore,
            "in_strand": instrand,
            "minKNOW_read_count": read_count,
            "estimated_selected_bases": self.acquisition_data.yield_summary.estimated_selected_bases,
        }
        if self.histogram_data:
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
        if self.acquisition_data:
            payload[
                "basecalled_bases"
            ] = int(self.acquisition_data.yield_summary.basecalled_pass_bases) + int(self.acquisition_data.yield_summary.basecalled_fail_bases)
            payload[
                "basecalled_fail_read_count"
            ] = self.acquisition_data.yield_summary.basecalled_fail_read_count
            payload[
                "basecalled_pass_read_count"
            ] = self.acquisition_data.yield_summary.basecalled_pass_read_count

        for channel in channel_dict:
            payload[str(channel)] = channel_dict[channel]
        log.debug("This our new payload: {}".format(payload))

        result = self.minotour_api.create_minion_statistic(
            payload, self.run_primary_key
        )
        log.debug("This is our result: {}".format(result))

    def run_information_monitor(self):
        """
        Get information on the run via the minKnow RPC. Basically just sets class values for any data we can get.
        Returns
        -------
        None

        """
        while self.run_bool:
            log.debug("Checking run info")
            try:
                self.acquisition_data = (
                    self.api_connection.acquisition.get_acquisition_info()
                )
            except:
                log.debug("No active run")
                self.acquisition_data = None
            self.temperature_data = self.api_connection.device.get_temperature()
            # ToDo: Check this code on a promethION.
            if str(self.device_type).startswith("PROMETHION"):
                self.minion_settings = (
                    self.api_connection.promethion_device.get_device_settings()
                )
            else:
                self.minion_settings = self.api_connection.minion_device.get_settings()
            self.bias_voltage = (
                self.api_connection.device.get_bias_voltage().bias_voltage
            )

            try:
                self.runinfo_api = self.api_connection.protocol.get_run_info()
            except:
                log.debug("Run Info not yet known.")
            try:
                self.sampleid = self.api_connection.protocol.get_run_info().user_info
            except:
                c = ProtocolRunUserInfo()
                c.sample_id.value = "Mux Scan"
                c.protocol_group_id.value = "Platform QC"
                self.sampleid = c
                log.debug("Sample ID not yet known.")
            log.debug("running update minion status")
            self.update_minion_info()

            if str(self.status).startswith("ACQUISITION_RUNNING") or str(
                self.status
            ).startswith("ACQUISITION_STARTING"):
                self.run_information = (
                    self.api_connection.acquisition.get_current_acquisition_run()
                )
                try:
                    log.debug("running update minion stats")
                    if hasattr(self, "run_primary_key"):
                        self.update_minion_stats()

                except Exception as err:
                    log.error("Problem updating stats to device.", err)
                    pass
            time.sleep(self.interval)

    def sendmessage(self, severitylevel, message):
        self.api_connection.log.send_user_message(
            severity=severitylevel, user_message=message
        )

    def get_messages(self):
        while self.run_bool:
            if not self.minotour_run_url:
                time.sleep(1)
                continue
            messages = self.api_connection.log.get_user_messages(
                include_old_messages=True
            )
            for message in messages:

                payload = {
                    "minion": self.minion["url"],
                    "message": message.user_message,
                    "run": "",
                    "identifier": message.identifier,
                    "severity": message.severity,
                    "timestamp": message.time.ToDatetime().strftime(
                        "%Y-%m-%d %H:%M:%S.%f"
                    )[:-3],
                }

                if self.minotour_run_url:
                    payload["run"] = self.minotour_run_url

                messagein = self.minotour_api.create_message(payload, self.minion)


class MinionManager(Manager):
    """
    manager for flowcell positions listed by minKNOW
    """

    def __init__(
        self, host="localhost", port=None, use_tls=False, args=None, header=None
    ):
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
                        self.args, position.connect(), self.header, device_id,
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
