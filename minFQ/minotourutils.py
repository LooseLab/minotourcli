import gzip

from Bio import SeqIO

from minFQ.minotourapiclient import Runcollection


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

