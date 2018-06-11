import sys,os
import curses
import time
import minFQ.rpc as rpc
import configargparse
import json
import struct
import threading
import math
import requests
import pandas as pd
import numpy as np

from ws4py.client.threadedclient import WebSocketClient
#from minotourAPI import

class DeviceConnect(WebSocketClient):
    #def __init__(self, *args,**kwargs):
    #    super(DeviceConnect, self).__init__(*args,**kwargs)
        #self.detailsdict=dict()
    #    self.daemon=True
    def __init__(self, connectip,args,rpcconnection):
        print ("Client established!")
        WebSocketClient.__init__(self, connectip)
        #print (args)
        self.rpc_connection=rpcconnection
        #self.rpc_connection=args[2]
        self.channels = self.rpc_connection.device.get_flow_cell_info().channel_count
        self.channelstatesdesc = self.rpc_connection.analysis_configuration.get_channel_states_desc()
        self.channelstates = dict()
        for i in range(self.channels):
            self.channelstates[i+1]=None
        self.status = ""
        self.interval = 10 #we will poll for updates every 10 seconds.

        runmonitorthread = threading.Thread(target=self.runmonitor, args=())
        runmonitorthread.daemon = True                            # Daemonize thread
        runmonitorthread.start()
        runinforthread = threading.Thread(target=self.runinfo, args=())
        runinforthread.daemon = True  # Daemonize thread
        runinforthread.start()
        messagesmonitor = threading.Thread(target=self.getmessages, args=())
        messagesmonitor.daemon = True  # Daemonize thread
        messagesmonitor.start()
        dutytimemonitorthread = threading.Thread(target=self.dutytimemonitor, args=())
        dutytimemonitorthread.daemon = True
        dutytimemonitorthread.start()
        flowcellmonitorthread = threading.Thread(target=self.flowcellmonitor, args=())
        flowcellmonitorthread.daemon = True
        flowcellmonitorthread.start()
        newchannelstatethread = threading.Thread(target=self.newchannelstatemonitor, args=())
        newchannelstatethread.daemon = True
        newchannelstatethread.start()
        print ("everything is loaded")
        self.first_connect()


    def first_connect(self):
        """
        This function will run when we first connect to the MinION device.
        It will provide the information to minotour necessary to remotely control the minION device.
        :return:
        """
        print ("First connection observed")
        pass

    def run_start(self):
        """
        This function will fire when a run first begins.
        It will drive the creation of a run.
        :return:
        """
        print ("run start observed")
        pass

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
        print ("run stop observed")
        pass

    def messages_monitor(self):
        """
        This function will handle the events of a new message arriving in minknow.
        :return:
        """
        pass

    def minknow_command(self):
        """
        This function will recieve commands for a specific minION and handle the interaction.
        :return:
        """
        pass

    def flowcellmonitor(self):
        while True:
            flowcellinfo = self.rpc_connection.device.stream_flow_cell_info()
            for event in flowcellinfo:
                print (event)
                self.flowcelldata = event

    def newchannelstatemonitor(self):
        while True:
            channel_states = self.rpc_connection.data.get_channel_states(wait_for_processing=True, first_channel=1,
                                                                         last_channel=512)
            try:
                for state in channel_states:
                    for channel in state.channel_states:#print (state)
            # print (channel)
            # print (channel.channel,channel.state_name)
                        self.channelstates[int(channel.channel)]=channel.state_name
                if not str(self.status).startswith("status: PROCESSING"):
                    break
            except:
                pass
            time.sleep(10)
            pass

    def dutytimemonitor(self):
        while True:
            print ("Duty Time Monitor Running", self.status)
            print (str(self.status))
            while str(self.status).startswith("status: PROCESSING"):
                print ("fetching duty time")
                dutytime = self.rpc_connection.statistics.stream_duty_time(step=60)
                for duty in dutytime:
                    #print (duty)
                    pass
            time.sleep(1)


    def runmonitor(self):
        while True:
            status_watcher = rpc.wrappers.StatusWatcher(self.rpc_connection)
            msgs = rpc.acquisition_service
            while True:
                for status in status_watcher.wait():
                    self.status = status
                    if str(self.status).startswith("status: STARTING"):
                        self.run_start()
                    if str(self.status).startswith("status: FINISHING"):
                        self.run_stop()
                    print(status)

    def runinfo(self):
        while True:
            #self.flowcelldata = self.rpc_connection.device.get_flow_cell_info()
            self.temperaturedata = self.rpc_connection.device.get_temperature()
            self.disk_space_info = self.rpc_connection.instance.get_disk_space_info()
            self.minion_settings = self.rpc_connection.minion_device.get_settings()
            self.bias_voltage = self.rpc_connection.device.get_bias_voltage()
            self.runinfo = self.rpc_connection.protocol.get_run_info()
            self.sampleid = self.rpc_connection.protocol.get_sample_id()
            print (self.minion_settings)
            if str(self.status).startswith("status: PROCESSING"):
                self.runinformation = self.rpc_connection.acquisition.get_current_acquisition_run()
                print (self.runinformation)
                channelpanda = pd.DataFrame.from_dict(self.channelstates, orient='index', dtype=None)
                #print (channelpanda.head())
                print (channelpanda.groupby([0,]).size())
                #print (channelpanda)
            try:
                print (self.read_event_weighted_hist)
                print (self.read_hist_bin_width)
            except:
                pass
            time.sleep(self.interval)

    def sendmessage(self,severitylevel,message):
        self.rpc_connection.log.send_user_message(severity=severitylevel, user_message=message)

    def getmessages(self):
        while True:
            messages = self.rpc_connection.log.get_user_messages(include_old_messages=True)
            for message in messages:
                #print (message)
                pass


    def opened(self):
        print ("Connection Success!!!!!!!!!!!!")
        ##print "Trying \"engine_states\":\"1\",\"channel_states\":\"1\",\"multiplex_states\":\"1\""
        #self.send(json.dumps({'engine_states':'1','channel_states':'1','multiplex_states':'1','channel_info':'1'}))
        #self.send(json.dumps({'engine_states':'1','channel_states':'1','channel_info':'1'}))
        #self.send(json.dumps({'engine_states':'1','channel_states':'1'}))
        self.send(json.dumps({'engine_states':'1'}))
        #self.send(json.dumps({'channel_info':'1','channel_states':'1'}))
        #self.send(transport.getvalue(), binary=True)

    def closed(self, code, reason="client disconnected for some reason"):
        print ("socket",self.sock.fileno())
        print ("Closed down", code, reason)

    def received_message(self, m):
        if not m.is_binary:
            #print ("****************** Non binary message")
            json_object = json.loads(str(m))
            #print (json_object)
            try:
                for key in json_object:
                    #print (key)
                    #if str(key) == "engine_states":
                    #    print (json_object[key])
                    if str(key) == "statistics":
                        #print (json_object[key].keys())
                        if "read_event_count_weighted_hist_bin_width" in json_object[key]:
                            self.read_hist_bin_width = json_object[key]["read_event_count_weighted_hist_bin_width"]
                        if "read_event_count_weighted_hist" in json_object[key]:
                            self.read_event_weighted_hist = json_object[key]["read_event_count_weighted_hist"]
                #print (json_object.keys())
            except:
                print ("key error")

class MinknowConnect(WebSocketClient):
    def __init__(self, minswip,args):
        print ("initialising")
        WebSocketClient.__init__(self, minswip)
        self.args = args
        self.minIONdict=dict() #A dictionary to store minION connection data.
        self.computer_name = ""
        self.minknow_version = ""
        self.minknow_status = ""


    def reportinformation(self):
        for minION in self.minIONdict:
            print (self.minIONdict[minION]["device_connection"].flowcelldata)
            print (self.minIONdict[minION]["device_connection"].temperaturedata)
            print (self.minIONdict[minION]["device_connection"].disk_space_info)

    def received_message(self, m):
        for thing in ''.join(map(chr, map(ord, (m.data).decode('latin-1')))).split('\n'):
            if len(thing) > 5 and "2L" not in thing and "2n" not in thing:
                print (thing)
                devicetype, deviceid = self.determinetype(thing)
                print (devicetype, deviceid)
                if deviceid not in self.minIONdict:
                    self.minIONdict[deviceid] = dict()
                minIONports = self.parse_ports(thing, deviceid)

                if len(minIONports) > 3:
                    try:
                        self.minIONdict[deviceid]["state"] = "active"
                        """
                        "port": 8001,
                        "ws_longpoll_port": 8003,
                        "ws_event_sampler_port": 8002,
                        "ws_raw_data_sampler_port": 8006,
                        "grpc_port": 8007,
                        "grpc_web_port": 8008
                        """
                        port = minIONports[0]
                        ws_longpoll_port = minIONports[1]
                        ws_event_sampler_port = minIONports[2]
                        ws_raw_data_sampler_port = minIONports[3]
                        grpc_port = minIONports[4]
                        grpc_web_port = minIONports[5]
                    except:
                        minIONports = list(map(lambda x: x - 192 + 8000 + 128, filter(lambda x: x > 120, map(ord, thing))))
                        self.minIONdict[deviceid]["state"] = "active"
                        port = minIONports[0]
                        ws_longpoll_port = minIONports[1]
                        ws_event_sampler_port = minIONports[2]
                        ws_raw_data_sampler_port = minIONports[3]
                        grpc_port = minIONports[4]
                        grpc_web_port = minIONports[5]
                    self.minIONdict[deviceid]["port"] = port
                    self.minIONdict[deviceid]["ws_longpoll_port"] = ws_longpoll_port
                    self.minIONdict[deviceid]["ws_event_sampler_port"] = ws_event_sampler_port
                    self.minIONdict[deviceid]["ws_raw_data_sampler_port"] = ws_raw_data_sampler_port
                    self.minIONdict[deviceid]["grpc_port"] = grpc_port
                    self.minIONdict[deviceid]["grpc_web_port"] = grpc_web_port
                    self.minIONdict[deviceid]["grpc_connection"] = rpc.Connection(port=self.minIONdict[deviceid]["grpc_port"])
                    self.computer_name = self.minIONdict[deviceid]["grpc_connection"].instance.get_machine_id().machine_id
                    self.minknow_version = self.minIONdict[deviceid][
                        "grpc_connection"].instance.get_version_info().minknow.full
                    self.minknow_status = self.minIONdict[deviceid]["grpc_connection"].instance.get_version_info().protocols
                    connectip = "ws://" + self.args.ip + ":" + str(self.minIONdict[deviceid]["ws_longpoll_port"]) + "/"
                    print ("setting up the goldmine")
                    self.minIONdict[deviceid]["device_connection"] = DeviceConnect(connectip,self.args,self.minIONdict[deviceid]["grpc_connection"])
                    #self.minIONdict[deviceid]["legacydevicedata"] = DeviceConnectLegacy(connectip,self.args,self.minIONdict[deviceid]["grpc_connection"])
                    try:
                        print ('trying to activate the connection')
                        self.minIONdict[deviceid]["device_connection"].connect()
                    except Exception as err:
                        print ("Arses", err)
                else:
                    self.minIONdict[deviceid]["state"] = "inactive"
                    self.minIONdict[deviceid]["port"] = ""
                    self.minIONdict[deviceid]["ws_longpoll_port"] = ""
                    self.minIONdict[deviceid]["ws_event_sampler_port"] = ""
                    self.minIONdict[deviceid]["ws_raw_data_sampler_port"] = ""
                    self.minIONdict[deviceid]["grpc_port"] = ""
                    self.minIONdict[deviceid]["grpc_web_port"] = ""
                    self.minIONdict[deviceid]["grpc_connection"] = ""
                    #self.minIONdict[deviceid]["APIHelp"].update_minion_status(deviceid, 'UNKNOWN', 'inactive')

    def determinetype(self,minION):
        """
        :param minION:
        :return: devicetype,deviceid,portstring
        """
        devicetype = "unknown"
        deviceid = "unknown"
        if minION[1] == "M":
            devicetype = "MinION"
            deviceid=minION[1:8]
        elif minION[1] == "G":
            devicetype = "GridION"
            deviceid = minION[1:8]
        elif minION[1] =="1" or minION[1]=="2":
            devicetype = "PromethION"
            promvals = minION[1:9].split('-')
            if len(promvals[1])==2:
                deviceid = minION[1:8]
            else:
                deviceid = minION[1:10]
        return devicetype,deviceid  #,portstring

    def parse_ports(self,ports,minIONname):
        """
        :param ports: string to parse representing the ports
        :return: list of ports
        """
        portset = list()
        rawports = list(map(lambda x: x, filter(lambda x: x, map(ord, ports))))
        chomplen = len(minIONname)+4
        rawports = rawports[chomplen:-2]
        rawvalues = list()
        offset = list()
        for index,port in enumerate(rawports):
            if index%3==0:
                try:
                    rawvalues.append(port)
                    offset.append(rawports[(index+1)])
                except:
                    pass
        for index,rawvalue in enumerate(rawvalues):
            try:
                off = offset[index]
                if off == 62:
                    correction = 192
                elif off == 63:
                    correction = 64
                else:
                    correction = 0
                port = rawvalue - correction + 8000
                portset.append(port)
            except:
                pass
        return portset



def parsearguments():
    parser = \
        configargparse.ArgParser(description='interaction: A program to provide real time interaction for minION runs.')
    parser.add(
        '-ip',
        '--ip-address',
        type=str,
        dest='ip',
        required=True,
        default=None,
        help='The IP address of the minKNOW machine.',
    )
    parser.add(
        '-d',
        '--debug',
        action='store_true'
    )
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
        if args.debug: print ("Error", err)
        if args.debug: print (
            "We guess you have not got minKNOW running on your computer at the ip address specified. Please try again.")
        if args.debug: print ("bye bye")
        sys.exit()

    while True:
        time.sleep(1)
        #print (Minknow.computer_name,Minknow.minknow_status,Minknow.minknow_version)
        #Minknow.reportinformation()

if __name__ == "__main__":
    main()