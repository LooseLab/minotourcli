import sys
import zerorpc
import threading
import time
import numpy as np

import os
import platform

from minFQ.FastqUtils import FastqHandler
from minFQ.controlutils import HelpTheMinion
import configargparse
from watchdog.observers.polling import PollingObserver as Observer

#from concurrent.futures import ThreadPoolExecutor
#from requests_futures.sessions import FuturesSession

#session = FuturesSession(executor=ThreadPoolExecutor(max_workers=10))

class MyDict(dict):
    pass

class MinFQApi(object):
    def __init__(self):
        self.version = "0.1"
        self.infostore = MyDict()
        self.infostore.GUI = True
        self.infostore.fastquprunning = False
        self.infostore.minKNOWmonitorrunning = False
        self.infostore.fastqup = False
        self.infostore.minKNOWmonitor = False
        self.infostore.fastqmessage = "Not Active"
        self.infostore.minKNOWmessage = "Not Active"
        self.infostore.minKNOWeventsseen = 0
        self.infostore.minKNOWreadsseen = 0
        self.infostore.flowcellcount = 0
        self.infostore.flowcellruncount = 0
        self.infostore.readcount = 0
        self.infostore.basecount = 0
        self.infostore.qualitysum = 0
        self.infostore.watchdir = ""
        self.infostore.targetdir = ""
        self.infostore.host_name = ""
        self.infostore.port_number = ""
        self.infostore.run_name = ""
        self.infostore.is_flowcell = True
        self.infostore.skip_sequence = False
        self.infostore.cust_barc = False
        self.infostore.noMinKNOW = True
        self.infostore.full_host = ""
        self.infostore.ipaddress = ""
        self.infostore.apiurl = ""
        self.infostore.apiport = ""
        self.infostore.api_key = ""
        self.infostore.apikey = ""
        self.infostore.runname = ""
        t = threading.Thread(target=self.monitor)

        try:
            t.start()
            print("Monitor started")
        except KeyboardInterrupt:
            print("Seen a ctrl-c")
            t.stop()
            raise

    def fetchfastqdata(self):
        return self.infostore.fastqmessage

    def fetchreadcount(self):
        print ("!!!!!!!!!!!!! {}".format(self.infostore.minKNOWreadsseen))
        if (self.infostore.readcount > 0) and (int(self.infostore.minKNOWreadsseen) > 0):
            return self.infostore.flowcellcount, self.infostore.flowcellruncount, self.infostore.readcount, self.infostore.basecount, float(
                np.around([(self.infostore.basecount / self.infostore.readcount)], decimals=2)), float(
                np.around([(self.infostore.qualitysum / self.infostore.readcount)], decimals=2)), self.infostore.minKNOWeventsseen, self.infostore.minKNOWreadsseen, float(np.around([(self.infostore.minKNOWeventsseen/self.infostore.minKNOWreadsseen)],decimals=2))
        elif (self.infostore.readcount > 0):
            return self.infostore.flowcellcount,self.infostore.flowcellruncount,self.infostore.readcount,self.infostore.basecount,float(np.around([(self.infostore.basecount/self.infostore.readcount)],decimals=2)),float(np.around([(self.infostore.qualitysum/self.infostore.readcount)],decimals=2)),0,0,0
        elif (int(self.infostore.minKNOWreadsseen) > 0):
            if self.infostore.minKNOWeventsseen > 0:
                return self.infostore.flowcellcount, self.infostore.flowcellruncount, self.infostore.readcount, self.infostore.basecount, 0, 0, self.infostore.minKNOWeventsseen, self.infostore.minKNOWreadsseen, float(np.around([(int(self.infostore.minKNOWeventsseen)/int(self.infostore.minKNOWreadsseen))],decimals=2))
            else:
                return (0, 0, 0, 0, 0, 0, 0, 0, 0)
        else:
            return (0,0,0,0,0,0,0,0,0)

    def monitor(self):
        global header
        while True:
            if self.infostore.fastqup:
                if not self.infostore.fastquprunning:
                    self.infostore.watchdir = self.infostore.targetdir
                    self.infostore.host_name=self.infostore.apiurl
                    self.infostore.port_number=self.infostore.apiport
                    self.infostore.run_name=self.infostore.runname
                    self.infostore.is_flowcell=True
                    #self.infostore.skip_sequence=False
                    self.infostore.cust_barc=False
                    self.infostore.noMinKNOW=True
                    self.infostore.full_host = "http://" + self.infostore.host_name + ":" + str(self.infostore.port_number) + "/"
                    print (self.infostore.watchdir)

                    header = {'Authorization': 'Token ' + self.infostore.api_key, 'Content-Type': 'application/json'}
                    event_handler = FastqHandler(self.infostore, header)
                    # This block handles the fastq
                    observer = Observer()
                    observer.schedule(event_handler, path=self.infostore.watchdir, recursive=True)
                    observer.daemon = True
                    observer.start()
                    self.infostore.fastquprunning=True
                    pass
            if self.infostore.fastquprunning:
                if not self.infostore.fastqup:
                    self.infostore.fastquprunning = False
                    self.infostore.fastqmessage = "FastQ read upload stopped."
                    event_handler.stopt()
                    observer.stop()
                    observer.join()
                    print ("we're stopping dude")
            if self.infostore.minKNOWmonitor:
                if not self.infostore.minKNOWmonitorrunning:
                    self.infostore.ip = self.infostore.ipaddress
                    self.infostore.host_name = self.infostore.apiurl
                    self.infostore.port_number = self.infostore.apiport
                    self.infostore.run_name = self.infostore.runname
                    self.infostore.is_flowcell = True
                    #self.infostore.skip_sequence = False
                    self.infostore.cust_barc = False
                    #self.infostore.api_key = self.infostore.api_key
                    self.infostore.full_host = "http://" + self.infostore.host_name + ":" + str(self.infostore.port_number) + "/"

                    header = {'Authorization': 'Token ' + self.infostore.api_key, 'Content-Type': 'application/json'}
                    minwsip = "ws://" + self.infostore.ip + ":9500/"
                    helper = HelpTheMinion(minwsip, self.infostore)
                    helper.connect()
                    t = threading.Thread(target=helper.process_minion)
                    t.daemon = True
                    t.start()
                    self.infostore.minKNOWmonitorrunning = True
            if self.infostore.minKNOWmonitorrunning:
                if not self.infostore.minKNOWmonitor:
                    self.infostore.minKNOWmonitorrunning = False
                    self.infostore.minknowmessage = "MinKNOW monitoring stopping."
                    helper.mcrunning = False
                    helper.hang_up()
                    self.infostore.minknowmessage = "MinKNOW monitoring stopped."

            print ("monitor fastq:{}".format(self.infostore.fastqmessage))
            time.sleep(1)

    def getversion(self):
        return (str(self.version))

    def echo(self, text):
        """echo any text"""
        return text

    def setparameter(self, parameter,text):
        setattr(self.infostore, parameter, text)
        return str(text)

    def getparameter(self, parameter):
        return getattr(self.infostore,parameter)

    def changestate(self,parameter):
        state = getattr(self.infostore,parameter)
        if state == True:
            setattr(self.infostore,parameter,False)
        else:
            setattr(self.infostore,parameter,True)
        return (getattr(self.infostore,parameter))

    def checkvariables(self, task):
        ## If task is fastq upload (fastqUP), check we have the necessary parameters (folder for reads, api_key, minotour url and port, run_name
        ## If task is monitor minKnow (minUP), check we have the necessary parameters (api_key, minotour_url and port, minKNOW IP)
        messages = {'apiurl': "minoTour url", 'apiport': "minoTour Port", 'api_key':"minotour API key", 'ipaddress':"minKNOW IP", 'targetdir':"FastQ Directory", 'runname':"Run Name"}
        if task == "minUP":
            passval = True
            status = "All OK"
            for var in vars(self.infostore):
                print (var)
                if var in ['ipaddress', 'apiurl', 'apiport','api_key']:
                    if len(vars(self.infostore)[var]) > 0:
                        pass
                    else:
                        passval = False
                        print ("problem var is {}".format(var))
                        status = messages[var]
                        break
            return (passval,status)
        if task == "fastqUP":
            passval = True
            status = "All OK"
            for var in vars(self.infostore):
                print(var)
                if var in ['targetdir', 'runname', 'apiurl', 'apiport', 'api_key']:
                    if len(vars(self.infostore)[var]) > 0:
                        pass
                    else:
                        passval = False
                        print("problem var is {}".format(var))
                        status = messages[var]
                        break
            return (passval, status)

    def getall(self):
        #print ("vars")
        print(vars(self.infostore))
        #print ("self dict")
        #print(self.__dict__)
        return (vars(self.infostore))



def parse_port():
    port = 4242
    try:
        port = int(sys.argv[1])
    except Exception as e:
        pass
    return '{}'.format(port)

def main():
    addr = 'tcp://127.0.0.1:' + parse_port()
    s = zerorpc.Server(MinFQApi())
    s.bind(addr)
    print('start running on {}'.format(addr))
    s.run()

if __name__ == '__main__':
    main()
