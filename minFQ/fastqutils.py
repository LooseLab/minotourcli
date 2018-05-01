"""
File Routines for handling fastq files and monitoring locations. Built on watchdog.
"""
import os,sys
import threading
import time
import gzip
import numpy as np

from tqdm import tqdm
from minFQ.minotourapiclient import Runcollection
from Bio import SeqIO
from watchdog.events import FileSystemEventHandler


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


def parse_fastq_record(record, fastq, rundict, args, header):

    fastq_read = {}

    description_dict = parse_fastq_description(record.description)

    fastq_read['read'] = description_dict.get('read', None)
    fastq_read['runid'] = description_dict.get('runid', None)
    fastq_read['channel'] = description_dict.get('ch', None)
    fastq_read['start_time'] = description_dict.get('start_time', None)
    fastq_read['is_pass'] = check_is_pass(fastq)
    fastq_read['read_id'] = record.id
    fastq_read['sequence_length'] = len(str(record.seq))

    quality = record.format('fastq').split('\n')[3]

    fastq_read['quality_average'] = quality_average = np.around([np.mean(np.array(list((ord(val) - 33) for val in quality)))], decimals=2)[0]

    # use 'No barcode' for non-barcoded reads
    if not description_dict.get('barcode', None):

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

    if fastq_read['runid'] not in rundict:
        rundict[fastq_read['runid']] = Runcollection(args, header)

        rundict[fastq_read['runid']].add_run(description_dict)

    rundict[fastq_read['runid']].add_read(fastq_read)


def parse_fastq_file(fastq, rundict, args, header):

    counter = 0

    if fastq.endswith(".gz"):

        with gzip.open(fastq, "rt") as handle:

            for record in SeqIO.parse(handle, "fastq"):

                counter += 1

                args.fastqmessage = "processing read {}".format(counter)

                parse_fastq_record(record, fastq, rundict, args, header)

    else:

        for record in SeqIO.parse(fastq, "fastq"):

            counter += 1

            args.fastqmessage = "processing read {}".format(counter)

            parse_fastq_record(record, fastq, rundict, args, header)

    for runs in rundict:

        rundict[runs].commit_reads()

def file_dict_of_folder_simple(path,args):
    file_list_dict = dict()
    counter = 0
    if os.path.isdir(path):
        print("caching existing fastq files in: %s" % (path))
        args.fastqmessage = "caching existing fastq files in: %s" % (path)
        for path, dirs, files in os.walk(path):
            for f in files:
                counter += 1
                if (f.endswith(".fastq") or f.endswith(".fastq.gz")):
                    file_list_dict[os.path.join(path, f)] = os.stat(os.path.join(path, f)).st_mtime
    print("processed %s files" % (counter))
    args.fastqmessage = "processed %s files" % (counter)
    print("found %d existing fastq files to process first." % (len(file_list_dict)))
    return file_list_dict


class FastqHandler(FileSystemEventHandler):

    def __init__(self, args,header,rundict):
        """Collect information about files already in the folders"""
        self.file_descriptor = dict()
        self.args = args
        self.header=header
        # adding files to the file_descriptor is really slow - therefore lets skip that and only update the files when we want to basecall thread_number
        self.creates = file_dict_of_folder_simple(args.watchdir,args)
        self.processing = dict()
        self.running = True
        self.rundict = rundict
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

            for fastqfile, createtime in tqdm(sorted(self.creates.items(), key=lambda x: x[1])):

                delaytime = 0

                # file created 5 sec ago, so should be complete. For simulations we make the time longer.
                if (int(createtime) + delaytime < time.time()):

                    del self.creates[fastqfile]
                    parse_fastq_file(fastqfile, self.rundict, self.args, self.header)

            # readsuploaded=0
            #
            # for runid in self.rundict:
            #
            #     print("RunID", runid)
            #     if self.rundict[runid].readcount > 0:
            #         print("Read Number:", self.rundict[runid].readcount, "Total Length:", self.rundict[runid].cumulength,
            #           "Average Length", self.rundict[runid].cumulength / self.rundict[runid].readcount, "Chan Count",
            #           len(self.rundict[runid].chandict))
            #     readsuploaded+=self.rundict[runid].readcount
            #     if self.args.GUI:
            #         try:
            #             (mean, median, std, maxval, minval) = self.rundict[runid].mean_median_std_max_min()
            #             print("mean", mean, "median", median, "std", std, "max", maxval, "min", minval)
            #         except:
            #             pass
            # print ("Uploaded {} reads in total.".format(readsuploaded))
            # self.args.fastqmessage ="Uploaded {} reads in total.".format(readsuploaded)

            time.sleep(5)

    def on_created(self, event):
        """Watchdog counts a new file in a folder it is watching as a new file"""
        """This will add a file which is added to the watchfolder to the creates and the info file."""
        if (event.src_path.endswith(".fastq") or event.src_path.endswith(".fastq.gz")):
            self.creates[event.src_path] = time.time()

    def on_modified(self, event):
        if (event.src_path.endswith(".fastq") or event.src_path.endswith(".fastq.gz")):
            self.creates[event.src_path] = time.time()

    def on_moved(self, event):
        """Watchdog considers a file which is moved within its domain to be a move"""
        """When a file is moved, we just want to update its location in the master dictionary."""
        if (event.dest_path.endswith(".fastq") or event.dest_path.endswith(".fastq.gz")):
            print("seen a fastq file move")
