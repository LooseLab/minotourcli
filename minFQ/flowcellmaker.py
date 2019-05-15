import os
import sys
import datetime
import configargparse
import validators

from ont_fast5_api import fast5_file, multi_fast5

from minFQ.minotourapi import MinotourAPI

from tqdm import tqdm


def main():
    parser = \
        configargparse.ArgParser(
            description='minFQ: A program to analyse minION fastq files in real-time or post-run and monitor the activity of MinKNOW.'
        )

    parser.add(
        '-w',
        '--watch-dir',
        type=str,
        required=True,
        default=None,
        help='The path to the folders containing fast5 reads to analyse - e.g. C:\\data\\minion\\downloads (for windows).',
        dest='watchdir'
    )

    parser.add(
        '-k',
        '--key',
        type=str,
        required=True,
        default=None,
        help='The api key for uploading data.',
        dest='api_key',
    )

    parser.add(
        '-p',
        '--port',
        type=int,
        # required=True,
        default=80,
        help='The port number for the local server.',
        dest='port_number',
    )

    parser.add(
        '-hn',
        '--hostname',
        type=str,
        # required=True,
        default='127.0.0.1',
        help='The host name you are loading data too.',
        dest='host_name',
    )

    args = parser.parse_args()




    minION = set()
    flowcelldict = dict()
    rundict = dict()



    print('Searching for files in {}'.format(os.path.abspath(args.watchdir)))
    last_seen=""
    for root, subdirs, files in tqdm(os.walk(args.watchdir)):
        files.sort()
        for file in tqdm(files):
            if file.endswith("fast5"):
                if file.split('_read_')[0] != last_seen:
                    last_seen = file.split('_read_')[0]
                    try:
                        try:
                            myfile  = fast5_file.Fast5File(os.path.join(root,file))

                        except:
                            mymultifile = multi_fast5.MultiFast5File(os.path.join(root,file))
                            myid = mymultifile.get_read_ids()[0]
                            myfile = mymultifile.get_read(myid)
                        minIONid = myfile.get_tracking_id()['device_id']
                        minION.add(minIONid)
                        flowcell = myfile.get_tracking_id()['flow_cell_id']
                        if len(flowcell) < 1:
                            flowcell = input('Enter a flowcell name: ')
                        sample_id = myfile.get_tracking_id()['sample_id']
                        run_id = myfile.get_tracking_id()['run_id']
                        if sample_id not in flowcelldict.keys():
                            flowcelldict[sample_id]=dict()
                        if flowcell not in flowcelldict[sample_id].keys():
                            flowcelldict[sample_id][flowcell] = dict()
                        if run_id not in flowcelldict[sample_id][flowcell].keys():
                            flowcelldict[sample_id][flowcell][run_id]=dict()
                            flowcelldict[sample_id][flowcell][run_id]["tracking_id"]=myfile.get_tracking_id()
                            flowcelldict[sample_id][flowcell][run_id]["context_tags"]=myfile.get_context_tags()
                    except:
                        print ("Non fast5file seen.")
    print ("Adding new runs.")

    header = {
        'Authorization': 'Token {}'.format(args.api_key),
        'Content-Type': 'application/json'
    }
    minotourapi = MinotourAPI(args.host_name,args.port_number, header)
    for minIONs in minION:
        minion = minotourapi.get_minion_by_name(minIONs)
        if not minion:
            minion = minotourapi.create_minion(minIONs)
        minion = minion
    for sample_id in tqdm(flowcelldict):
        for flowcellid in flowcelldict[sample_id].keys():
            flowcell = minotourapi.get_flowcell_by_name(flowcellid)
            if len(flowcell["data"])==0:
                create_flowcell = minotourapi.create_flowcell(flowcellid)
                flowcell = minotourapi.get_flowcell_by_name(flowcellid)
            for run_id in flowcelldict[sample_id][flowcellid]:
                run = minotourapi.get_run_by_runid(run_id)
                if not run:
                    '''print (flowcell)'''
                    is_barcoded = False  # TODO do we known this info at this moment? This can be determined from run info.
                    has_fastq = True  # TODO do we known this info at this moment? This can be determined from run info
                    run = minotourapi.create_run(sample_id, run_id, is_barcoded, has_fastq,
                                                            flowcell['data'], minion,
                                                            flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['exp_start_time'])

                minion = minotourapi.get_minion_by_name(flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['device_id'])

                try: 
                    sample_rate =int(str(flowcelldict[sample_id][flowcellid][run_id]['context_tags']['sample_frequency']))
                except:
                    sample_rate = 0

                payload = {
                    "minION": str(minion["url"]),
                    "minKNOW_current_script": str(""),
                    "minKNOW_sample_name": str(sample_id),
                    "minKNOW_exp_script_purpose": str(flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['exp_script_purpose']),
                    "minKNOW_flow_cell_id": flowcellid,
                    "minKNOW_run_name": str(""),
                    "run_id": str(run['url']),
                    "minKNOW_version": str(flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['version']),
                    "minKNOW_hash_run_id": str(run_id),
                    "minKNOW_script_run_id": str(""),
                    "minKNOW_real_sample_rate": sample_rate,
                    "minKNOW_asic_id": flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['asic_id'],
                    "minKNOW_start_time": flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['exp_start_time'],
                    "minKNOW_computer": str(flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['hostname']),
                }
                try:
                    payload['flowcell_type']=str(flowcelldict[sample_id][flowcellid][run_id]['context_tags']['flowcell_type'])
                except:
                    payload['flowcell_type']="unknown"
                try:
                    payload['sequencing_kit']=str(flowcelldict[sample_id][flowcellid][run_id]['context_tags']['sequencing_kit'])
                except:
                    payload['sequencing_kit']="unknown"

                updateruninfo = minotourapi.update_minion_run_info(payload, run['id'])

    print ("Metadata Uploaded to MinoTour.")
