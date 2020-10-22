import datetime
import json
import logging
import sys, os
import threading
import time

import configargparse
import pandas as pd
from google.protobuf.json_format import MessageToJson
from ws4py.client.threadedclient import WebSocketClient

import minFQ.rpc as rpc
from minFQ.minotourapi import MinotourAPI as MinotourAPINew

log = logging.getLogger(__name__)


def parsemessage(message):
    return json.loads(
        MessageToJson(
            message,
            preserving_proto_field_name=True,
            including_default_value_fields=True,
        )
    )


import grpc

rpc._load()
import minFQ.rpc.protocol_pb2 as protocol
import minFQ.rpc.protocol_pb2_grpc as protocol_grpc
import minFQ.rpc.manager_pb2 as manager
import minFQ.rpc.manager_pb2_grpc as manager_grpc

# from minotourAPI import


class DeviceConnect(WebSocketClient):
    # def __init__(self, *args,**kwargs):
    #    super(DeviceConnect, self).__init__(*args,**kwargs)
    # self.detailsdict=dict()
    #    self.daemon=True
    def __init__(self, connectip, args, rpcconnection, header, minIONid):
        self.args = args
        ## Set a status to hold what we are currently doing.
        self.deviceactive = False
        if self.args.verbose:
            log.info("Client established!")
        WebSocketClient.__init__(self, connectip)
        self.rpc_connection = rpcconnection

        # Here we need to check if we are good to run against this version.
        self.version = self.rpc_connection.instance.get_version_info().minknow.full
        self.device_type = parsemessage(self.rpc_connection.instance.get_host_type())[
            "host_type"
        ]
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
        self.channels = parsemessage(self.rpc_connection.device.get_flow_cell_info())[
            "channel_count"
        ]
        self.channelstatesdesc = (
            self.rpc_connection.analysis_configuration.get_channel_states_desc()
        )
        self.channelstates = dict()
        for i in range(self.channels):
            self.channelstates[i + 1] = None
        self.status = ""
        self.interval = 30  # we will poll for updates every 30 seconds.
        self.longinterval = 30  # we have a short loop and a long loop
        self.minIONid = minIONid
        self.computer_name = self.rpc_connection.instance.get_machine_id().machine_id
        self.minknow_version = (
            self.rpc_connection.instance.get_version_info().minknow.full
        )
        self.minknow_status = self.rpc_connection.instance.get_version_info().protocols
        self.minotourapi = MinotourAPINew(
            self.args.host_name, self.args.port_number, self.header
        )
        self.minotourapi.test()
        self.disk_space_info = json.loads(
            MessageToJson(
                self.rpc_connection.instance.get_disk_space_info(),
                preserving_proto_field_name=True,
                including_default_value_fields=True,
            )
        )
        self.flowcelldata = parsemessage(
            self.rpc_connection.device.get_flow_cell_info()
        )
        minion = self.minotourapi.get_minion_by_name(self.minIONid)
        if not minion:
            minion = self.minotourapi.create_minion(self.minIONid)
        self.minion = minion
        self.minIONstatus = self.minotourapi.get_minion_status(self.minion)
        self.runidlink = ""

        try:
            self.acquisition_data = parsemessage(
                self.rpc_connection.acquisition.get_acquisition_info()
            )
        except:
            # if self.args.verbose:
            log.debug("No active run")
            self.acquisition_data = {}

        runmonitorthread = threading.Thread(target=self.runmonitor, args=())
        runmonitorthread.daemon = True  # Daemonize thread
        runmonitorthread.start()

        flowcellmonitorthread = threading.Thread(target=self.flowcellmonitor, args=())
        flowcellmonitorthread.daemon = True
        flowcellmonitorthread.start()

        runinforthread = threading.Thread(target=self.runinfo, args=())
        runinforthread.daemon = True  # Daemonize thread
        runinforthread.start()

        messagesmonitor = threading.Thread(target=self.getmessages, args=())
        messagesmonitor.daemon = True  # Daemonize thread
        messagesmonitor.start()

        # This is for future usage.
        # dutytimemonitorthread = threading.Thread(target=self.dutytimemonitor, args=())
        # dutytimemonitorthread.daemon = True
        # dutytimemonitorthread.start()

        newchannelstatethread = threading.Thread(
            target=self.newchannelstatemonitor, args=()
        )
        newchannelstatethread.daemon = True
        newchannelstatethread.start()

        newhistogrammonitorthread = threading.Thread(
            target=self.newhistogrammonitor, args=()
        )
        newhistogrammonitorthread.daemon = True
        newhistogrammonitorthread.start()

        jobsmonitorthread = threading.Thread(target=self.jobs_monitor, args=())
        jobsmonitorthread.daemon = True
        jobsmonitorthread.start()

        log.debug("All is well with connection.")
        self.first_connect()

    def disconnect_nicely(self):
        """
        User has ^C to quit minFQ. This function fires to let minoTour know.
        Returns
        -------

        """
        log.debug("Trying to disconnect nicely")
        self.minotourapi.update_minion_event(
            self.minion, self.computer_name, "unplugged"
        )
        try:
            self.minIONstatus["minKNOW_status"] = "unplugged"
        except:
            log.debug("Couldn't unplug MinION from website.")
        self.minIONstatus = self.minotourapi.update_minion_info_mt(
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
        print ("DO WE GET HERE?")
        self.minotourapi.update_minion_event(self.minion, self.computer_name, "active")
        # TODO removed for now as we are not allowing user to start runs. May be added back in later.
        # self.minotourapi.fetch_minion_scripts(self.minion)
        # for protocol in self.rpc_connection.protocol.list_protocols().ListFields()[0][1]:
        #     protocoldict = self.parse_protocol(protocol)
        #     #print (self.minion,protocoldict)
        #     self.minotourapi.update_minion_script(self.minion,protocoldict)
        print  ("!!!!!!!!!  MONKEY {}".format(self.status))
        if str(self.status).startswith("status: PROCESSING"):
            self.deviceactive = True
            self.run_start()

    def parse_protocol(self, protocol):
        protocoldict = dict()
        flowcell = "N/A"
        kit = "N/A"
        basecalling = "N/A"
        try:
            kit = protocol.tags["kit"].ListFields()[0][1]
            flowcell = protocol.tags["flow cell"].ListFields()[0][1]
            basecalling = protocol.tags["base calling"].ListFields()[0][1]
        except:
            pass
        # print (protocol.name, protocol.identifier)
        protocoldict["identifier"] = protocol.identifier
        # protocoldict["name"]=protocol.name
        # print (protocol.name)
        if basecalling:
            basecalling = "BaseCalling"
        else:
            basecalling = "NoBaseCalling"
        protocoldict["name"] = "{}/{}_{}_{}".format(
            protocol.name, flowcell, kit, basecalling
        )
        for tag in protocol.tags:
            try:
                protocoldict[tag] = protocol.tags[tag].ListFields()[0][1]
            except:
                pass
        return protocoldict

    def run_start(self):
        """
        This function will fire when a run first begins.
        It will drive the creation of a run.
        :return:
        """
        self.minotourapi.update_minion_event(
            self.minion, self.computer_name, "sequencing"
        )

        log.debug("run start observed")
        log.debug("MINION:", self.minion)
        # We wait for 10 seconds to allow the run to start
        time.sleep(self.interval)
        try:
            self.runinformation = (
                self.rpc_connection.acquisition.get_current_acquisition_run()
            )

            log.debug(self.runinfo_api)
            log.debug(self.sampleid)
            log.debug(self.runinformation)
            log.debug("RUNID: {}".format(self.runinformation.start_time))
            log.debug(self.channelstatesdesc)
            log.debug(self.channels)
            log.debug("FLOWCELL DATA: {}".format(self.get_flowcell_id()))
            log.debug("trying to create run")
            self.create_run(self.runinformation.run_primary_key)
            log.debug("run created!!!!!!!")
            #### Grab the folder and if we are allowed, add it to the watchlist?
            FolderPath = parsemessage(
                self.rpc_connection.protocol.get_current_protocol_run()
            )["output_path"]
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
                self.rpc_connection.protocol.get_run_info().protocol_id
            ),
            "minKNOW_sample_name": str(self.sampleid.sample_id),
            "minKNOW_exp_script_purpose": str(
                self.rpc_connection.protocol.get_protocol_purpose()
            ),
            "minKNOW_flow_cell_id": self.get_flowcell_id(),
            "minKNOW_run_name": str(self.sampleid.sample_id),
            "run": self.runidlink,
            "minKNOW_version": str(
                self.rpc_connection.instance.get_version_info().minknow.full
            ),
            "minKNOW_hash_run_id": str(self.runinformation.run_primary_key),
            "minKNOW_script_run_id": str(
                self.rpc_connection.protocol.get_current_protocol_run().acquisition_run_ids[
                    0
                ]
            ),
            "minKNOW_real_sample_rate": int(
                str(self.rpc_connection.device.get_sample_rate().sample_rate)
            ),
            "minKNOW_asic_id": self.flowcelldata["asic_id"],
            "minKNOW_start_time": self.runinformation.start_time.ToDatetime().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            # "minKNOW_colours_string": str(self.rpc_connection.analysis_configuration.get_channel_states_desc()),
            "minKNOW_colours_string": str(
                MessageToJson(
                    self.rpc_connection.analysis_configuration.get_channel_states_desc(),
                    preserving_proto_field_name=True,
                    including_default_value_fields=True,
                )
            ),
            "minKNOW_computer": str(self.computer_name),
            "target_temp": self.temperaturedata.target_temperature,
            "flowcell_type": self.flowcelldata["user_specified_product_code"]
            # "read_length_type": self.histogramdata["histogram_data"]["read_length_type"],
        }

        contextinfo = parsemessage(self.rpc_connection.protocol.get_context_info())[
            "context_info"
        ]
        for k, v in contextinfo.items():
            payload[k] = v

        ruinfo = parsemessage(self.rpc_connection.protocol.get_run_info())

        try:
            payload["experiment_id"] = ruinfo["user_info"]["protocol_group_id"]
        except:
            payload["experiment_id"] = "Not Known"

        log.debug(">>>>>>>>{}".format(payload))
        updateruninfo = self.minotourapi.update_minion_run_info(payload, self.runid)
        log.debug(updateruninfo)

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
        log.debug(">>> inside create_run")

        log.debug(self.minotourapi)

        log.debug(">>> after self.minotourapi")

        self.minotourapi.test()

        log.debug(">>> after self.minotourapi.test()")

        run = self.minotourapi.get_run_by_runid(runid)

        log.debug(run)

        if not run:
            log.debug(">>> no run {}".format(runid))
            #
            # get or create a flowcell
            #
            flowcell = self.minotourapi.get_flowcell_by_name(self.get_flowcell_id())[
                "data"
            ]
            log.debug(flowcell)

            if not flowcell:
                log.debug(">>> no flowcell")
                flowcell = self.minotourapi.create_flowcell(self.get_flowcell_id())

            is_barcoded = False  # TODO do we known this info at this moment? This can be determined from run info.

            has_fastq = True  # TODO do we known this info at this moment? This can be determined from run info
            log.debug(">>> before self.minotourapi.create_run")
            log.debug("self.sampleid.sample_id {}".format(self.sampleid.sample_id))
            createrun = self.minotourapi.create_run(
                self.sampleid.sample_id,
                runid,
                is_barcoded,
                has_fastq,
                flowcell,
                self.minion,
                self.runinformation.start_time.ToDatetime().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            )
            log.debug(">>> after self.minotourapi.create_run")

            # createrun = requests.post(self.args.full_host+'api/v1/runs/', headers=self.header, json={"run_name": self.status_summary['run_name'], "run_id": runid, "barcode": barcoded, "is_barcoded":is_barcoded, "minION":self.minion["url"]})

            if not createrun:
                log.error("Run not created!")

            else:
                log.info(createrun)
                self.runidlink = createrun["url"]
                self.runid = createrun["id"]  # TODO is it id or runid?
                # self.runidlink = json.loads(createrun.text)["url"]
                # self.runid = json.loads(createrun.text)["id"]
                # self.create_flowcell(self.status_summary['flow_cell_id'])
                # self.create_flowcell_run()

        else:
            self.runidlink = run["url"]
            self.runid = run["id"]
        log.debug("***** self.runid: {}".format(self.runid))

        log.debug("**** run stats updated")

    def run_live(self):
        """
        This function will update the run information to the server at a given rate during a live run.
        :return:
        """
        pass

    def run_stop(self):
        """
        This function will clean up when a run finishes.
        :return:
        """
        ## ToDo We need to remove the run from the rundict when we stop a run to prevent massive memory problems.
        self.minotourapi.update_minion_event(self.minion, self.computer_name, "active")
        FolderPath = str(
            os.path.normpath(
                parsemessage(self.rpc_connection.protocol.get_current_protocol_run())[
                    "output_path"
                ]
            )
        )
        if not self.args.noFastQ:
            if FolderPath in self.args.WATCHLIST:
                time.sleep(self.longinterval)
                self.args.WATCHLIST.remove(FolderPath)
                self.args.update = True
        log.debug("run stop observed")

    def jobs_monitor(self):
        """
        This function will check the remote server for new jobs to be done.
        :return:
        """
        while True:
            log.debug("!!!!!!checking for jobs!!!!!!")
            jobs = self.minotourapi.get_minion_jobs(self.minion)
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
                    self.minotourapi.complete_minion_job(self.minion, job)
                if job["job"] == "custommessage":
                    self.sendmessage(1, "minoTour: {}".format(job["custom"]))
                    self.minotourapi.complete_minion_job(self.minion, job)
                if job["job"] == "stopminion":
                    if self.args.enable_remote:
                        self.rpc_connection.protocol.stop_protocol()
                        self.sendmessage(
                            3, "minoTour was used to remotely stop your run."
                        )
                    self.minotourapi.complete_minion_job(self.minion, job)
                if job["job"] == "rename":
                    if self.args.enable_remote:
                        self.rpc_connection.protocol.set_sample_id(
                            sample_id=job["custom"]
                        )
                        self.sendmessage(
                            1, "minoTour renamed your run to {}".format(job["custom"])
                        )
                    self.minotourapi.complete_minion_job(self.minion, job)
                if job["job"] == "nameflowcell":
                    if self.args.enable_remote:
                        self.rpc_connection.device.set_user_specified_flow_cell_id(
                            id=job["custom"]
                        )
                        self.sendmessage(
                            1,
                            "minoTour renamed your flowcell to {}".format(
                                job["custom"]
                            ),
                        )
                    self.minotourapi.complete_minion_job(self.minion, job)
                if job["job"] == "startminion":
                    if self.args.enable_remote:
                        print(job["custom"], "\n\n\n\n\n")
                        self.rpc_connection.protocol.start_protocol(
                            identifier=job["custom"]
                        )
                        self.sendmessage(
                            2, "minoTour attempted to start a run on your device."
                        )
                    self.minotourapi.complete_minion_job(self.minion, job)

    def minknow_command(self):
        """
        This function will recieve commands for a specific minION and handle the interaction.
        :return:
        """
        pass

    def get_flowcell_id(self):
        # ToDo make this function work out if we need to create a flowcell id for this run.
        if len(self.flowcelldata["user_specified_flow_cell_id"]) > 0:
            log.debug("We have a self named flowcell")
            flowcell_id = str(self.flowcelldata["user_specified_flow_cell_id"])
        else:
            log.debug("the flowcell id is fixed")
            flowcell_id = str(self.flowcelldata["flow_cell_id"])
        return flowcell_id

    def flowcellmonitor(self):
        """

        Returns
        -------

        """
        while True:
            flowcellinfo = self.rpc_connection.device.stream_flow_cell_info()
            for event in flowcellinfo:
                log.debug(event)
                self.flowcelldata = parsemessage(event)
                log.debug(self.get_flowcell_id())
                self.update_minion_info()

    def newhistogrammonitor(self):
        """
        Monitor the histogram output from minKnow. It is the best.
        Returns
        -------
        None

        """
        while True:
            if str(self.status).startswith("status: PROCESSING"):
                ###We need to test if we are doing basecalling or not.
                self.runinformation = parsemessage(
                    self.rpc_connection.acquisition.get_current_acquisition_run()
                )
                if self.runinformation["config_summary"]["basecalling_enabled"]:
                    self.basecalling = True
                else:
                    self.basecalling = False
                if self.basecalling:
                    rltype = 2
                else:
                    rltype = 1
                histogram_stream = self.rpc_connection.statistics.stream_read_length_histogram(
                    poll_time=60,
                    wait_for_processing=True,
                    read_length_type=rltype,
                    bucket_value_type=1,
                )
                try:
                    for histogram_event in histogram_stream:
                        # print (parsemessage(histogram_event))
                        self.histogramdata = parsemessage(histogram_event)
                        if not str(self.status).startswith("status: PROCESSING"):
                            break
                except Exception as e:
                    # print ("Histogram Problem: {}".format(e))
                    log.error("histogram problem: {}".format(e))
                    break
            time.sleep(self.interval)
            pass

    def newchannelstatemonitor(self):
        while True:
            channel_states = self.rpc_connection.data.get_channel_states(
                wait_for_processing=True, first_channel=1, last_channel=512
            )
            try:
                for state in channel_states:
                    for channel in state.channel_states:  # print (state)
                        self.channelstates[int(channel.channel)] = channel.state_name
                if not str(self.status).startswith("status: PROCESSING"):
                    break
            except:
                pass
            time.sleep(self.interval)
            pass

    def dutytimemonitor(self):
        while True:
            log.debug("Duty Time Monitor Running: {}".format(self.status))
            log.debug(str(self.status))
            while str(self.status).startswith("status: PROCESSING"):
                log.debug("fetching duty time")
                dutytime = self.rpc_connection.statistics.stream_duty_time(
                    wait_for_processing=True, step=60
                )
                if self.args.verbose:
                    for duty in dutytime:
                        log.debug(duty)
            time.sleep(1)

    def runmonitor(self):
        """
        Monitor whether or not a run has just started or stopped. Alerts Minotour in the event of run start/stop.
        Returns
        -------
        None
        """

        # fixme Status watcher not in minKnow api 4.0
        while True:
            status_watcher = rpc.wrappers.StatusWatcher(self.rpc_connection)
            msgs = rpc.acquisition_service
            while True:
                for status in status_watcher.wait():
                    self.status = status
                    if str(self.status).startswith("status: STARTING"):
                        self.deviceactive = True
                        self.run_start()

                    if not self.deviceactive and str(self.status).startswith(
                        "status: FINISHING"
                    ):
                        self.deviceactive = True
                        self.run_start()
                    ###So - a run which is still basecalling will report as finishing - so we may need to spot this...
                    if self.deviceactive and str(self.status).startswith(
                        "status: READY"
                    ):
                        self.deviceactive = False
                        self.run_stop()
                    log.debug(status)

    def update_minion_info(self):
        """
        Update the minion status information. Send it to minotour.
        Data may be None, if it is not present in the MinKnow status.
        Logic is supposed to be just information about MinKNOW/the minION device.
        Returns
        -------
        None

        """
        acquisition_data = dict()

        if len(self.acquisition_data) < 1:
            acquisition_data["state"] = "No Run"
            currentscript = "Nothing Running"
        else:
            acquisition_data = self.acquisition_data
            currentscript = str(self.rpc_connection.protocol.get_run_info().protocol_id)

        if len(self.disk_space_info) < 1:
            self.disk_space_info = json.loads(
                MessageToJson(
                    self.rpc_connection.instance.get_disk_space_info(),
                    preserving_proto_field_name=True,
                    including_default_value_fields=True,
                )
            )
            log.debug(self.disk_space_info)

        payload = {
            "minion": str(self.minion["url"]),
            "minKNOW_status": acquisition_data["state"],
            "minKNOW_current_script": currentscript,
            "minKNOW_exp_script_purpose": str(
                self.rpc_connection.protocol.get_protocol_purpose()
            ),
            "minKNOW_flow_cell_id": self.get_flowcell_id(),
            "minKNOW_real_sample_rate": int(
                str(self.rpc_connection.device.get_sample_rate().sample_rate)
            ),
            "minKNOW_asic_id": self.flowcelldata[
                "asic_id"
            ],  # self.status_summary['asic_id'],
            "minKNOW_total_drive_space": self.disk_space_info[
                "filesystem_disk_space_info"
            ][0]["bytes_capacity"],
            "minKNOW_disk_space_till_shutdown": self.disk_space_info[
                "filesystem_disk_space_info"
            ][0]["bytes_when_alert_issued"],
            "minKNOW_disk_available": self.disk_space_info[
                "filesystem_disk_space_info"
            ][0]["bytes_available"],
            "minKNOW_warnings": self.disk_space_info["filesystem_disk_space_info"][0][
                "recommend_stop"
            ],
            "minknow_version": self.minknow_version,
        }
        try:
            payload[
                "minKNOW_script_run_id"
            ] = self.rpc_connection.protocol.get_current_protocol_run().acquisition_run_ids[
                0
            ]
        except:
            pass
        if hasattr(self, "sampleid"):
            payload["minKNOW_sample_name"] = str(self.sampleid.sample_id)
            payload["minKNOW_run_name"] = str(self.sampleid.sample_id)

        if hasattr(self, "runinformation"):
            if hasattr(self.runinformation, "run_id"):
                payload["minKNOW_hash_run_id"] = str(self.runinformation.run_id)

        if hasattr(self, "runinfo_api"):
            payload["wells_per_channel"] = parsemessage(self.runinfo_api)[
                "flow_cell"
            ].get("wells_per_channel", -1)

        if self.minIONstatus:  # i.e the minION status already exists

            self.minIONstatus = self.minotourapi.update_minion_info_mt(
                payload, self.minion
            )

        else:

            self.minIONstatus = self.minotourapi.create_minion_info_mt(
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
        asictemp = self.temperaturedata.minion.asic_temperature.value
        heatsinktemp = self.temperaturedata.minion.heatsink_temperature.value
        biasvoltage = int(self.bias_voltage)
        voltage_val = int(self.bias_voltage)  # todo this likely is wrong
        voltage_value = biasvoltage  # todo check this = probably wrong
        yield_val = self.acquisition_data["yield_summary"]["selected_events"]
        read_count = self.acquisition_data["yield_summary"]["read_count"]
        channelpanda = pd.DataFrame.from_dict(
            self.channelstates, orient="index", dtype=None
        )
        channeldict = dict()
        channeldict["strand"] = 0
        channeldict["adapter"] = 0
        channeldict["good_single"] = 0
        channeldict["pore"] = 0
        try:
            channelpandastates = channelpanda.groupby([0,]).size()
            # print (channelpandastates)
            log.debug(channelpandastates)
            for state, value in channelpandastates.iteritems():
                log.debug("{} {}".format(state, value))
                #    print (state,value)
                channeldict[state] = value
            # print ("\n\n\n\n\n\n")
            instrand = 0  # channeldict["strand"]+channeldict["adapter"]
            openpore = 0  # channeldict["good_single"]+channeldict["pore"]
            meanratio = 0  # todo work out if we can still do this
        except:
            meanratio = 0
            instrand = 0
            openpore = 0
            pass

        # Capturing the histogram data from MinKNOW
        # print (self.runinformation)

        payload = {
            "minion": str(self.minion["url"]),
            "run": self.runidlink,
            "sample_time": str(datetime.datetime.now()),
            "event_yield": yield_val,
            "asic_temp": asictemp,
            "heat_sink_temp": heatsinktemp,
            "voltage_value": voltage_value,
            "mean_ratio": meanratio,
            "open_pore": openpore,
            "in_strand": instrand,
            "minKNOW_histogram_values": str(
                self.histogramdata["histogram_data"]["buckets"]
            ),
            "minKNOW_histogram_bin_width": self.histogramdata["histogram_data"][
                "width"
            ],
            "actual_max_val": self.histogramdata["histogram_data"]["actual_max_val"],
            "minKNOW_read_count": read_count,
            "n50_data": self.histogramdata["n50_data"]["value"],
            "estimated_selected_bases": self.acquisition_data["yield_summary"][
                "estimated_selected_bases"
            ],
            "basecalled_bases": self.acquisition_data["yield_summary"][
                "basecalled_bases"
            ],
            "basecalled_fail_read_count": self.acquisition_data["yield_summary"][
                "basecalled_fail_read_count"
            ],
            "basecalled_pass_read_count": self.acquisition_data["yield_summary"][
                "basecalled_pass_read_count"
            ],
        }
        for channel in channeldict:
            payload[str(channel)] = channeldict[channel]

        log.debug("This our new payload: {}".format(payload))

        result = self.minotourapi.create_minion_statistic(payload, self.runid)

        log.debug("This is our result: {}".format(result))

    def runinfo(self):
        """
        Get information on the run via the minKnow RPC. Basically just sets class values for any data we can get.
        Returns
        -------
        None

        """
        while True:
            log.debug("Checking run info")
            try:
                self.acquisition_data = parsemessage(
                    self.rpc_connection.acquisition.get_acquisition_info()
                )
            except:
                log.debug("No active run")
                self.acquisition_data = {}
            self.temperaturedata = self.rpc_connection.device.get_temperature()
            self.disk_space_info = json.loads(
                MessageToJson(
                    self.rpc_connection.instance.get_disk_space_info(),
                    preserving_proto_field_name=True,
                    including_default_value_fields=True,
                )
            )
            if str(self.device_type).startswith("PROMETHION"):
                self.minion_settings = (
                    self.rpc_connection.promethion_device.get_device_settings()
                )
            else:
                self.minion_settings = self.rpc_connection.minion_device.get_settings()
            self.bias_voltage = json.loads(
                MessageToJson(
                    self.rpc_connection.device.get_bias_voltage(),
                    preserving_proto_field_name=True,
                    including_default_value_fields=True,
                )
            )["bias_voltage"]

            try:
                self.runinfo_api = self.rpc_connection.protocol.get_run_info()
            except:
                log.debug("Run Info not yet known.")
            try:
                self.sampleid = self.rpc_connection.protocol.get_sample_id()
            except:
                self.sampleid = {"sample_id": "Mux Scan"}
                log.debug("Sample ID not yet known.")
            log.debug("running update minion status")
            self.update_minion_info()
            if str(self.status).startswith("status: PROCESSING"):
                self.runinformation = (
                    self.rpc_connection.acquisition.get_current_acquisition_run()
                )
                try:
                    log.debug("running update minion stats")
                    if hasattr(self, "runid"):
                        self.update_minion_stats()
                except Exception as err:
                    log.error("Problem updating stats to device.", err)
                    pass
            try:
                log.debug(self.read_event_weighted_hist)
                log.debug(self.read_hist_bin_width)
            except:
                log.debug("Couldn't log histogram data.")
            time.sleep(self.interval)

    def sendmessage(self, severitylevel, message):
        self.rpc_connection.log.send_user_message(
            severity=severitylevel, user_message=message
        )

    def getmessages(self):
        while True:
            if not self.runidlink:
                time.sleep(1)
                continue
            messages = self.rpc_connection.log.get_user_messages(
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

                if self.runidlink:
                    payload["run"] = self.runidlink

                messagein = self.minotourapi.create_message(payload, self.minion)

    def opened(self):
        log.debug("Connected to MinIONs")
        ##print "Trying \"engine_states\":\"1\",\"channel_states\":\"1\",\"multiplex_states\":\"1\""
        # self.send(json.dumps({'engine_states':'1','channel_states':'1','multiplex_states':'1','channel_info':'1'}))
        # self.send(json.dumps({'engine_states':'1','channel_states':'1','channel_info':'1'}))
        # self.send(json.dumps({'engine_states':'1','channel_states':'1'}))
        # self.send(json.dumps({'engine_states':'1'}))
        # self.send(json.dumps({'channel_info':'1','channel_states':'1'}))
        # self.send(transport.getvalue(), binary=True)

    def closed(self, code, reason="client disconnected for some reason"):
        log.info("socket", self.sock.fileno())
        log.info("Closed down", code, reason)

    def received_message(self, m):
        ## All we do here is grab the old read_hist_bin - we shouldn't need to do this anymore?
        ## This code is now deprecated
        if not m.is_binary:
            # print ("****************** Non binary message")
            json_object = json.loads(str(m))
            # print (json_object)
            try:
                for key in json_object:
                    # print (key)
                    # if str(key) == "engine_states":
                    #    print (json_object[key])
                    if str(key) == "statistics":
                        log.debug(json_object[key].keys())
                        if (
                            "read_event_count_weighted_hist_bin_width"
                            in json_object[key]
                        ):
                            self.read_hist_bin_width = json_object[key][
                                "read_event_count_weighted_hist_bin_width"
                            ]
                        else:
                            self.read_hist_bin_width = 0
                        if "read_event_count_weighted_hist" in json_object[key]:
                            self.read_event_weighted_hist = json_object[key][
                                "read_event_count_weighted_hist"
                            ]
                        else:
                            self.read_event_weighted_hist = ""
                # print (json_object.keys())
            except:
                log.error("key error")


class MinknowConnectRPC:
    def __init__(self, minswip, args, header):
        self.args = args
        log.debug("initialising minknow connection via rpc")
        self.header = header
        self.minIONdict = dict()  # A dictionary to store minION connection data.
        devicemonitorthread = threading.Thread(target=self.devicemonitor, args=())
        devicemonitorthread.daemon = True  # Daemonize thread
        devicemonitorthread.start()

    def devicemonitor(self):
        # -------------------------------------------------------------------------------
        # Connect to the running Manager instance:
        #
        # We can connect to minknow manager on port 9501.
        #
        channel = grpc.insecure_channel("localhost:9501")
        stub = manager_grpc.ManagerServiceStub(channel)
        while True:
            # Send the list request
            list_request = manager.ListDevicesRequest()
            response = stub.list_devices(list_request)
            for device in response.active:
                log.debug(device.name)
                deviceid = device.name
                if deviceid not in self.minIONdict:
                    self.minIONdict[deviceid] = dict()
                    self.minIONdict[deviceid]["state"] = "pending"
                if self.minIONdict[deviceid]["state"] != "active":
                    self.minIONdict[deviceid]["grpc_port"] = device.ports.insecure_grpc
                    self.minIONdict[deviceid][
                        "ws_longpoll_port"
                    ] = device.ports.json_websocket
                    log.debug(self.minIONdict[deviceid]["grpc_port"])
                    self.minIONdict[deviceid]["grpc_connection"] = rpc.Connection(
                        port=self.minIONdict[deviceid]["grpc_port"]
                    )
                    connectip = (
                        "ws://"
                        + self.args.ip
                        + ":"
                        + str(self.minIONdict[deviceid]["ws_longpoll_port"])
                        + "/"
                    )

                    self.minIONdict[deviceid]["device_connection"] = DeviceConnect(
                        connectip,
                        self.args,
                        self.minIONdict[deviceid]["grpc_connection"],
                        self.header,
                        deviceid,
                    )
                    self.minIONdict[deviceid]["state"] = "active"
            time.sleep(5)

    def minIONnumber(self):
        return len(self.minIONdict)

    def disconnect_nicely(self):
        for device in self.minIONdict:
            log.info("Disconnecting {} from the server.".format(device))
            self.minIONdict[device]["device_connection"].stop_monitoring()
        log.info("Stopped successfully.")


def parsearguments():
    parser = configargparse.ArgParser(
        description="interaction: A program to provide real time interaction for minION runs."
    )
    parser.add(
        "-ip",
        "--ip-address",
        type=str,
        dest="ip",
        required=True,
        default=None,
        help="The IP address of the minKNOW machine.",
    )
    parser.add("-d", "--debug", action="store_true")
    args = parser.parse_args()
    return args


def main():
    args = parsearguments()
    ##First thing to do is to try and connect to minKNOW to retrieve information on which minIONs are present.
    minwsip = "ws://" + args.ip + ":9500/"
    Minknow = MinknowConnect(minwsip, args)
    try:
        Minknow.connect()
    except Exception as err:
        log.error("Error", err)
        log.error(
            "We guess you have not got minKNOW running on your computer at the ip address specified. Please try again."
        )
        log.error("bye bye")
        sys.exit()

    while True:
        time.sleep(1)
        # print (Minknow.computer_name,Minknow.minknow_status,Minknow.minknow_version)
        # Minknow.reportinformation()


if __name__ == "__main__":
    main()
