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



def md5Checksum(filePath):

    return os.path.getsize(filePath)
    '''
    with open(filePath, 'rb') as fh:
        m = hashlib.md5()
        while True:
            data = fh.read(8192)
            if not data:
                break
            m.update(data)
        return m.hexdigest()
    '''

def check_is_pass(path):

    folders = os.path.split(path)

    if 'pass' in folders[0]:

        return True

    elif 'fail' in folders[0]:

        return False

    else:

        return True  # This assumes we have been unable to find either pass or fail and thus we assume the run is a pass run.


def parse_fastq_description(description):

    descriptiondict = dict()
    descriptors = description.split(" ")
    del descriptors[0]
    for item in descriptors:
        bits = item.split("=")
        descriptiondict[bits[0]] = bits[1]
    return descriptiondict


def parse_fastq_record(record, fastq, rundict, args, header, fastqfile):

    log.info("Parsing reads from file {}".format(fastq))

    fastq_read = {}

    description_dict = parse_fastq_description(record.description)

    #print (fastqfile)

    fastq_read['read'] = description_dict.get('read', None)
    fastq_read['runid'] = description_dict.get('runid', None)
    fastq_read['channel'] = description_dict.get('ch', None)
    fastq_read['start_time'] = description_dict.get('start_time', None)
    fastq_read['is_pass'] = check_is_pass(fastq)
    fastq_read['read_id'] = record.id
    fastq_read['sequence_length'] = len(str(record.seq))
    fastq_read['fastqfile'] = fastqfile["url"]

    # get or create fastfile if not in dictionary?

    #fastq_read['fastqfilename'] = fastqfileid



    if fastq_read['runid'] not in rundict:

        rundict[fastq_read['runid']] = Runcollection(args, header)

        rundict[fastq_read['runid']].add_run(description_dict)

    rundict[fastq_read['runid']].get_readnames_by_run(fastqfile['id'])

    if fastq_read['read_id'] not in rundict[fastq_read['runid']].readnames:

        quality = record.format('fastq').split('\n')[3]

        fastq_read['quality_average'] = quality_average = np.around([np.mean(np.array(list((ord(val) - 33) for val in quality)))], decimals=2)[0]

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

            fastq_read['sequence'] = str(record.seq)
            fastq_read['quality'] = record.format('fastq').split('\n')[3]

        rundict[fastq_read['runid']].add_read(fastq_read)


def parse_fastq_file(fastq, rundict, fastqdict, args, header, MinotourConnection):

    log.info("Parsing fastq file {}".format(fastq))

    print (fastqdict[str(os.path.basename(fastq))]["md5"])


    ## Get fastqfile id from database here

    #As it is the first time we are looking at this file, we set the md5 in the database to be 0

    print (fastqdict)


    with open(fastq, "r") as file:
        for _ in range(1):
            line = file.readline()
    for _ in line.split():
        if _.startswith("runid"):
            # print (_.split("=")[1])
            runid = _.split("=")[1]

    fastqfile = MinotourConnection.create_file_info(str(os.path.basename(fastq)), runid, "0", None)
    print ("Run")
    print (fastqfile)
    print ("\n\n\n\n")
    counter = 0

    if fastq.endswith(".gz"):

        with gzip.open(fastq, "rt") as handle:
            try:
                for record in SeqIO.parse(handle, "fastq"):

                    counter += 1

                    args.reads_seen += 1

                    args.fastqmessage = "processing read {}".format(counter)

                    parse_fastq_record(record, fastq, rundict, args, header,fastqfile)

            except:

                args.reads_corrupt += 1

                log.error("Corrupt file observed in {}.".format(fastq))

                #continue

    else:

        try:

            for record in SeqIO.parse(fastq, "fastq"):

                counter += 1

                args.reads_seen += 1

                args.fastqmessage = "processing read {}".format(counter)

                parse_fastq_record(record, fastq, rundict, args, header,fastqfile)

        except Exception as e:

            args.reads_corrupt += 1

            log.error("Corrupt file observed in {}.".format(fastq))
            raise CommandError(repr(e))

            #continue

    for runs in rundict:
        print (runs)
        print (rundict[runs].run)
        rundict[runs].commit_reads()

    print ("rundict {}".format(rundict))
    print ("file {}".format(fastqfile))
    print ("runid {}".format(runid))
    print ("run {}".format(rundict[runid].run))
    try:
        print (rundict[runid].run['url'])
    except Exception as err:
        print ("url problem {}".format(err))
    try:
        fastqfile = MinotourConnection.create_file_info(str(os.path.basename(fastq)), runid, fastqdict[str(os.path.basename(fastq))]["md5"], rundict[runid].run)
    except Exception as err:
        print ("Problem with uploading file {}".format(err))
    print (fastqfile)

    print ("finished and returning")
    return counter


def file_dict_of_folder_simple(path, args, MinotourConnection, fastqdict):

    file_list_dict = dict()
    
    counter = 0
    
    if os.path.isdir(path):
    
        log.info("caching existing fastq files in: %s" % (path))
    
        args.fastqmessage = "caching existing fastq files in: %s" % (path)


    
        for path, dirs, files in os.walk(path):
            
            for f in files:
            
                if f.endswith(".fastq") or f.endswith(".fastq.gz"):

                    counter += 1

                    args.files_seen += 1
                    #### Here is where we want to check if the files have been created and what the checksums are
                    #### If the file checksums do not match, we pass the file to the rest of the script.
                    #### When we finish analysing a file, we will need to update this information n the server.
                    md5Check = md5Checksum(os.path.join(path, f))
                    #print (f, md5Check)
                    with open(os.path.join(path, f), "r") as file:
                        for _ in range(1):
                            line = file.readline()
                    for _ in  line.split():
                        if _.startswith("runid"):
                            #print (_.split("=")[1])
                            runid = _.split("=")[1]
                            result = (MinotourConnection.get_file_info_by_runid(_.split("=")[1]))
                    if f not in fastqdict.keys():
                        fastqdict[f]=dict()

                    fastqdict[f]["runid"] = runid
                    fastqdict[f]["md5"] = md5Check

                    print (result)

                    print (len(result))

                    if result is None or len(result)< 1 :
                        """This adds the fastq file to the database if it isn't already there """
                        #print ("trying {} {} {}".format(f,runid,md5Check))
                        file_list_dict[os.path.join(path, f)] = os.stat(os.path.join(path, f)).st_mtime
                        ### We don't want to create the record till we have finished processing the file!±
                        #result2 = MinotourConnection.create_file_info(f,runid,md5Check)
                        #print ("done {} {} {}".format(f, runid, md5Check))
                        #print (result2)

                    else:
                        """Here we are going to check if the files match or not. """
                        seenfile = False
                        for file in result:

                            if file["name"] == f:
                                seenfile = True
                                print ("md5check : {} stored : {}".format(md5Check,file["md5"]))
                                if int(file["md5"])==int(md5Check):
                                    print ("File {} is not different.".format(f))
                                else:
                                    print ("File {} is different.".format(f))
                                    file_list_dict[os.path.join(path, f)] = os.stat(os.path.join(path, f)).st_mtime
                                    #result2 = MinotourConnection.create_file_info(f, runid, md5Check)
                                break

                        if not seenfile:
                            file_list_dict[os.path.join(path, f)] = os.stat(os.path.join(path, f)).st_mtime
                            #result2 = MinotourConnection.create_file_info(f, runid, md5Check)
    
    log.info("processed %s files" % (counter))
    
    args.fastqmessage = "processed %s files" % (counter)
    
    log.info("found %d existing fastq files to process first." % (len(file_list_dict)))
    
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
        self.args.reads_seen = 0
        self.args.reads_corrupt = 0
        self.args.reads_skipped = 0
        self.args.reads_uploaded = 0
        # adding files to the file_descriptor is really slow - therefore lets skip that and only update the files when we want to basecall thread_number
        self.MinotourConnection = MinotourAPI(self.args.full_host, self.header)
        self.rundict = rundict
        self.fastqdict= dict()
        self.creates = file_dict_of_folder_simple(self.args.watchdir, args, self.MinotourConnection,self.fastqdict)
        print (self.rundict)
        self.processing = dict()
        self.running = True


        self.t = threading.Thread(target=self.processfiles)
        self.grouprun = None

        try:
            self.t.start()
        except KeyboardInterrupt:
            self.t.stop()
            raise

    def stopt(self):
        self.running=False

    def lencreates(self):
        return len(self.creates)

    def lenprocessed(self):
        return len(self.processed)

    def processfiles(self):

        while self.running:
            currenttime = time.time()
            #for fastqfile, createtime in tqdm(sorted(self.creates.items(), key=lambda x: x[1])):
            for fastqfile, createtime in sorted(self.creates.items(), key=lambda x: x[1]):

                delaytime = 0

                # file created 5 sec ago, so should be complete. For simulations we make the time longer.
                if (int(createtime) + delaytime < time.time()):

                    del self.creates[fastqfile]

                    #print (fastqfile,md5Checksum(fastqfile), "\n\n\n\n")

                    parse_fastq_file(fastqfile, self.rundict, self.fastqdict, self.args, self.header, self.MinotourConnection)

                    self.args.files_processed += 1

            if currenttime+5 < time.time():
                time.sleep(5)

    def process_fastqfile(self, filename):

        parse_fastq_file(filename, self.rundict, self.fastqdict, self.args, self.header, self.MinotourConnection)

    def on_created(self, event):
        """Watchdog counts a new file in a folder it is watching as a new file"""
        """This will add a file which is added to the watchfolder to the creates and the info file."""
        # if (event.src_path.endswith(".fastq") or event.src_path.endswith(".fastq.gz")):
        #     self.creates[event.src_path] = time.time()

        log.info("Processing file {}".format(event.src_path))
        time.sleep(5)
        self.process_fastqfile(event.src_path)

        # f = open(event.src_path, "r")
        # counter = 0
        # for line in f:
        #     log.info("{} - {}".format(event.src_path, counter))
        #     counter = counter + 1
