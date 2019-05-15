import gzip
import logging

from Bio import SeqIO

from minFQ.minotourapiclient import Runcollection


log = logging.getLogger(__name__)

def parsefastq(fastq, rundict, args, header):

    print('Inside parsefastq: {}, {}, {}'.format(fastq, rundict, args))
    counter = 0
    if fastq.endswith(".gz"):
        with gzip.open(fastq, "rt") as handle:
            for record in SeqIO.parse(handle, "fastq"):
                counter += 1
                args.fastqmessage = "processing read {}".format(counter)
                descriptiondict = parsedescription(record.description)
                if descriptiondict["runid"] not in rundict:
                    rundict[descriptiondict["runid"]] = Runcollection(args,header)
                    rundict[descriptiondict["runid"]].add_run(descriptiondict)
                rundict[descriptiondict["runid"]].add_read(record, descriptiondict, fastq)
    else:
        for record in SeqIO.parse(fastq, "fastq"):
            counter += 1
            args.fastqmessage = "processing read {}".format(counter)
            descriptiondict = parsedescription(record.description)
            if descriptiondict["runid"] not in rundict:
                rundict[descriptiondict["runid"]] = Runcollection(args, header)
                rundict[descriptiondict["runid"]].add_run(descriptiondict)
            rundict[descriptiondict["runid"]].add_read(record, descriptiondict,fastq)
    for runs in rundict:
        rundict[runs].commit_reads()


def parsedescription(description):
    descriptiondict = dict()
    descriptors = description.split(" ")
    del descriptors[0]
    for item in descriptors:
        bits = item.split("=")
        descriptiondict[bits[0]] = bits[1]
    return descriptiondict



### Functions for minknowconnection

def determinetype(minION):
    """
    :param minION:
    :return: devicetype,deviceid,portstring
    """
    #print (minION)
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

def parse_ports(ports,minIONname):
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
