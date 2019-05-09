"""
File Routines for handling fastq files and monitoring locations. Built on watchdog.
"""
import logging
import os,sys
import threading
import time
import gzip
import numpy as np
import hashlib #for checking if a file is different to the value stored in the database

from tqdm import tqdm
from minFQ.minotourapiclient import Runcollection
from minFQ.minotourapi import MinotourAPI
from Bio import SeqIO
from watchdog.events import FileSystemEventHandler


log = logging.getLogger(__name__)

###Function modified from https://raw.githubusercontent.com/lh3/readfq/master/readfq.py

def readfq(fp): # this is a generator function
    last = None # this is a buffer keeping the last unprocessed line
    while True: # mimic closure; is it a bad idea?
        if not last: # the first record or a record following a fastq
            for l in fp: # search for the start of the next record
                if l[0] in '>@': # fasta/q header line
                    last = l[:-1] # save this line
                    break
        if not last: break
        desc, name, seqs, last = last[1:], last[1:].partition(" ")[0], [], None
        for l in fp: # read the sequence
            if l[0] in '@+>':
                last = l[:-1]
                break
            seqs.append(l[:-1])
        if not last or last[0] != '+': # this is a fasta record
            yield desc,name, ''.join(seqs), None # yield a fasta record
            if not last: break
        else: # this is a fastq record
            seq, leng, seqs = ''.join(seqs), 0, []
            for l in fp: # read the quality
                seqs.append(l[:-1])
                leng += len(l) - 1
                if leng >= len(seq): # have read enough quality
                    last = None
                    yield desc, name, seq, ''.join(seqs); # yield a fastq record
                    break
            if last: # reach EOF before reading enough quality
                yield desc, name, seq, None # yield a fasta record instead
                break


def md5Checksum(filePath):

    return os.path.getsize(filePath)

def check_fastq_path(path):
    folders = splitall(path)
    try:
        if folders[-2] in ("pass","fail"):
            return ("{}_{}".format(folders[-2],folders[-1]))
        elif folders[-3] in ("pass","fail"):
            return ("{}_{}_{}".format(folders[-3],folders[-2],folders[-1]))
        else:
            return ("{}".format(folders[-1]))
    except:
        return ("{}".format(folders[-1]))


def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

def check_is_pass(path, avg_quality):

    folders = os.path.split(path)

    if 'pass' in folders[0]:

        return True

    elif 'fail' in folders[0]:

        return False

    else:
        if avg_quality != None:

            if avg_quality >= 7:

                return True  # This assumes we have been unable to find either pass or fail and thus we assume the run is a pass run.

            else:

                return False

        else:

            return True


def parse_fastq_description(description):

    descriptiondict = dict()
    descriptors = description.split(" ")
    del descriptors[0]
    for item in descriptors:
        bits = item.split("=")
        descriptiondict[bits[0]] = bits[1]
    return descriptiondict


def parse_fastq_record(desc, name, seq, qual, fastq, rundict, args, header, fastqfile):

    log.debug("Parsing reads from file {}".format(fastq))



    fastq_read = {}

    description_dict = parse_fastq_description(desc)

    fastq_read['read'] = description_dict.get('read', None)
    fastq_read['runid'] = description_dict.get('runid', None)
    fastq_read['channel'] = description_dict.get('ch', None)
    fastq_read['start_time'] = description_dict.get('start_time', None)
    #fastq_read['is_pass'] = check_is_pass(fastq)
    fastq_read['read_id'] = name
    fastq_read['sequence_length'] = len(str(seq))
    fastq_read['fastqfile'] = fastqfile["id"]


    # get or create fastfile if not in dictionary?

    #fastq_read['fastqfilename'] = fastqfileid

    if fastq_read['runid'] not in rundict:

        rundict[fastq_read['runid']] = Runcollection(args, header)

        rundict[fastq_read['runid']].add_run(description_dict, args)

    rundict[fastq_read['runid']].get_readnames_by_run(fastqfile['id'])

    if fastq_read['read_id'] not in rundict[fastq_read['runid']].readnames:


        quality = qual


        ## Turns out this is not the way to calculate quality...
        #fastq_read['quality_average'] = quality_average = np.around([np.mean(np.array(list((ord(val) - 33) for val in quality)))], decimals=2)[0]

        if quality != None:
            fastq_read['quality_average'] = quality_average = round(-10 * np.log10(np.mean(np.array(list( (10**(-(ord(val)-33)/10)) for val in quality )))),2)

        fastq_read['is_pass'] = check_is_pass(fastq,fastq_read['quality_average'])
        #print (quality_average)

        # use 'No barcode' for non-barcoded reads
        barcode_name = description_dict.get('barcode', None)
        if barcode_name:

            fastq_read['barcode_name'] = barcode_name

        else:

            fastq_read['barcode_name'] = 'No barcode'

        # add control-treatment if passed as argument
        if args.treatment_control:

            if int(fastq_read['channel']) % args.treatment_control == 0:

                fastq_read['barcode_name'] = fastq_read['barcode_name'] + ' - control'

            else:

                fastq_read['barcode_name'] = fastq_read['barcode_name'] + ' - treatment'

        # check if sequence is sent or not
        if args.skip_sequence:

            fastq_read['sequence'] = ''
            fastq_read['quality'] = ''

        else:

            fastq_read['sequence'] = str(seq)
            fastq_read['quality'] = qual

        rundict[fastq_read['runid']].add_read(fastq_read)

    else:
        args.reads_skipped += 1

def get_runid(fastq):
    if fastq.endswith(".gz"):
        with gzip.open(fastq, "rt") as file:
            for _ in range(1):
                line = file.readline()
    else:
        with open(fastq, "r") as file:
            for _ in range(1):
                line = file.readline()
    for _ in line.split():
        if _.startswith("runid"):
            # print (_.split("=")[1])
            runid = _.split("=")[1]
    return runid


def parse_fastq_file(fastq, rundict, fastqdict, args, header, MinotourConnection):

    log.debug("Parsing fastq file {}".format(fastq))

    runid=get_runid(fastq)


    fastqfile = MinotourConnection.create_file_info(str(check_fastq_path(fastq)), runid, "0", None)

    counter = 0

    if fastq.endswith(".gz"):

        with gzip.open(fastq, "rt") as fp:
            try:
                for desc, name, seq, qual in readfq(fp):
                    counter += 1

                    args.reads_seen += 1

                    args.fastqmessage = "processing read {}".format(counter)

                    parse_fastq_record(desc, name, seq, qual, fastq, rundict, args, header,fastqfile)

            except Exception as e:

                args.reads_corrupt += 1

                log.error("Corrupt file observed in {}.".format(fastq))
                log.error(e)
                #continue

    else:

        try:

            #for record in SeqIO.parse(fastq, "fastq"):
            with open(fastq, "r") as fp:
                
                for desc, name, seq, qual in readfq(fp):

                    counter += 1

                    args.reads_seen += 1

                    args.fastqmessage = "processing read {}".format(counter)

                    parse_fastq_record(desc, name, seq, qual, fastq, rundict, args, header,fastqfile)

        except Exception as e:

            args.reads_corrupt += 1

            log.error("Corrupt file observed in {}.".format(fastq))
            log.error(e)

            #continue

    for runs in rundict:

        rundict[runs].commit_reads()

    try:
        fastqfile = MinotourConnection.create_file_info(str(check_fastq_path(fastq)), runid, md5Checksum(fastq), rundict[runid].run)
    except Exception as err:
        log.error("Problem with uploading file {}".format(err))

    return counter


def file_dict_of_folder_simple(path, args, MinotourConnection, fastqdict):

    file_list_dict = dict()

    if not args.ignoreexisting:
    
        counter = 0
    
        if os.path.isdir(path):

            log.info("caching existing fastq files in: %s" % (path))

            args.fastqmessage = "caching existing fastq files in: %s" % (path)

            novelrunset=set()

            seenfiletracker = dict()

            for path, dirs, files in os.walk(path):

                for f in files:

                    if f.endswith(".fastq") or f.endswith(".fastq.gz"):
                        log.debug("Processing File {}\r".format(f))
                        counter += 1

                        args.files_seen += 1
                        #### Here is where we want to check if the files have been created and what the checksums are
                        #### If the file checksums do not match, we pass the file to the rest of the script.
                        #### When we finish analysing a file, we will need to update this information n the server.
                        #### Currently just using size.
                        md5Check = md5Checksum(os.path.join(path, f))

                        runid = get_runid(os.path.join(path, f))
                        if runid not in novelrunset and runid not in seenfiletracker.keys():
                            result = (MinotourConnection.get_file_info_by_runid(runid))
                            #### Here we want to parse through the results and store them in some kind of dictionary in order that we can check what is happening
                            if result is not None:
                                for entry in result:
                                    if entry["runid"] not in seenfiletracker.keys():
                                        seenfiletracker[entry["runid"]]=dict()
                                    seenfiletracker[entry["runid"]][entry["name"]]=entry["md5"]
                        else:
                            result = None

                        filepath = os.path.join(path, f)
                        checkfilepath = check_fastq_path(filepath)
                        if checkfilepath not in fastqdict.keys():
                            fastqdict[checkfilepath]=dict()

                        fastqdict[checkfilepath]["runid"] = runid
                        fastqdict[checkfilepath]["md5"] = md5Check


                        """Here we are going to check if the files match or not. """
                        seenfile = False
                        if runid in seenfiletracker.keys() and checkfilepath in seenfiletracker[runid].keys():
                            seenfile = True
                            if int(md5Check) == int(seenfiletracker[runid][checkfilepath]):
                                args.files_skipped += 1
                            else:
                                file_list_dict[filepath] = os.stat(filepath).st_mtime
                                novelrunset.add(runid)

                        if not seenfile:
                            file_list_dict[filepath] = os.stat(filepath).st_mtime
                            novelrunset.add(runid)

        log.info("processed %s files" % (counter))

        args.fastqmessage = "processed %s files" % (counter)

        log.info("found %d existing fastq files to process first." % (len(file_list_dict)))

    else:
        args.fastqmessage = "Ignoring existing fastq files in: %s" % (path)
    
    return file_list_dict


class FastqHandler(FileSystemEventHandler):

    def __init__(self, args, header, rundict):
        """
        Collect information about files already in the folders
        """

        self.file_descriptor = dict()
        self.args = args
        self.header = header
        self.args.files_seen = 0
        self.args.files_processed = 0
        self.args.files_skipped = 0
        self.args.reads_seen = 0
        self.args.reads_corrupt = 0
        self.args.reads_skipped = 0
        self.args.reads_uploaded = 0
        # adding files to the file_descriptor is really slow - therefore lets skip that and only update the files when we want to basecall thread_number
        self.MinotourConnection = MinotourAPI(self.args.host_name, self.args.port_number, self.header)
        self.rundict = rundict
        self.fastqdict= dict()
        #if not self.args.ignoreexisting:
        self.creates = file_dict_of_folder_simple(self.args.watchdir, self.args, self.MinotourConnection,self.fastqdict)
        self.processing = dict()
        self.running = True


        self.t = threading.Thread(target=self.processfiles)
        self.grouprun = None

        try:
            self.t.start()
        except KeyboardInterrupt:
            self.t.stop()
            raise

    def addrunmonitor(self,runpath):
        """
        Add a new folder for checking reads in.
        :param runpath: the final part of the folder structure - effectively the sample name
        :return:
        """
        pass

    def stopt(self):
        self.running=False

    def lencreates(self):
        return len(self.creates)

    def lenprocessed(self):
        return len(self.processed)

    def processfiles(self):
        #print ("Process Files Inititated")
        while self.running:
            currenttime = time.time()
            #for fastqfile, createtime in tqdm(sorted(self.creates.items(), key=lambda x: x[1])):
            for fastqfile, createtime in sorted(self.creates.items(), key=lambda x: x[1]):

                delaytime = 10

                # file created 5 sec ago, so should be complete. For simulations we make the time longer.
                if (int(createtime) + delaytime < time.time()):

                    del self.creates[fastqfile]

                    #print (fastqfile,md5Checksum(fastqfile), "\n\n\n\n")

                    parse_fastq_file(fastqfile, self.rundict, self.fastqdict, self.args, self.header, self.MinotourConnection)

                    self.args.files_processed += 1

            if currenttime+5 > time.time():
                time.sleep(5)
            #print ("still ticking")

    def process_fastqfile(self, filename):

        parse_fastq_file(filename, self.rundict, self.fastqdict, self.args, self.header, self.MinotourConnection)

    def on_created(self, event):
        """Watchdog counts a new file in a folder it is watching as a new file"""
        """This will add a file which is added to the watchfolder to the creates and the info file."""
        # if (event.src_path.endswith(".fastq") or event.src_path.endswith(".fastq.gz")):
        #     self.creates[event.src_path] = time.time()

        log.info("Processing file {}".format(event.src_path))
        #time.sleep(5)
        if (event.src_path.endswith(".fastq") or event.src_path.endswith(".fastq.gz") or event.src_path.endswith(".fq") or event.src_path.endswith(".fq.gz")):
            self.args.files_seen += 1
            self.creates[event.src_path] = time.time()

    def on_modified(self, event):
        if (event.src_path.endswith(".fastq") or event.src_path.endswith(".fastq.gz") or event.src_path.endswith(".fq") or event.src_path.endswith(".fq.gz")):
            log.debug("Modified file {}".format(event.src_path))
            self.creates[event.src_path] = time.time()

        #self.process_fastqfile(event.src_path)

        # f = open(event.src_path, "r")
        # counter = 0
        # for line in f:
        #     log.info("{} - {}".format(event.src_path, counter))
        #     counter = counter + 1
