import os
import sys
import datetime
import configargparse
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
        default=8100,
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
            #print (file)
            if file.endswith("fast5"):
                if file.split('_read_')[0] != last_seen:
                    #print (last_seen,file.split('_read_')[0])
                    last_seen = file.split('_read_')[0]
                    try:
                        try:
                            myfile  = fast5_file.Fast5File(os.path.join(root,file))

                        except:
                            mymultifile = multi_fast5.MultiFast5File(os.path.join(root,file))
                            myid = mymultifile.get_read_ids()[0]
                            myfile = mymultifile.get_read(myid)

                        #print (myfile)
                        #print (myfile.get_tracking_id())
                        minIONid = myfile.get_tracking_id()['device_id']
                        minION.add(minIONid)
                        flowcell = myfile.get_tracking_id()['flow_cell_id']
                        print ("seen flowcell:{}".format(flowcell))
                        if len(flowcell) < 1:
                            print ("Flowcell ID missing from file {}.".format(file))
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

                #else:
                    #print ("same read")

                #print (myfile.get_context_tags())


    #print (minION)
    #print (flowcelldict)

    print ("Adding new runs.")

    full_host = "http://{}:{}/".format(args.host_name, str(args.port_number))


    header = {
        'Authorization': 'Token {}'.format(args.api_key),
        'Content-Type': 'application/json'
    }

    minotourapi = MinotourAPI(full_host, header)


    for minIONs in minION:
        #print ("Create {}".format(minIONs))
        minion = minotourapi.get_minion_by_name(minIONs)
        if not minion:
            minion = minotourapi.create_minion(minIONs)
        minion = minion

#    print (flowcelldict)

    for sample_id in tqdm(flowcelldict):
#        print ("sample_id:{}".format(sample_id))
        for flowcellid in flowcelldict[sample_id].keys():
            print ("Looking for {}".format(flowcellid))
            flowcell = minotourapi.get_flowcell_by_name(flowcellid)
            #print ("found flowcell {}".format(flowcell))
            if len(flowcell["data"])==0:
                print ("Not found Flowcell")
                flowcell = minotourapi.create_flowcell(flowcellid)

            for run_id in flowcelldict[sample_id][flowcellid]:
                #print (run_id)
                run = minotourapi.get_run_by_runid(run_id)
                if not run:
                    is_barcoded = False  # TODO do we known this info at this moment? This can be determined from run info.
                    has_fastq = True  # TODO do we known this info at this moment? This can be determined from run info

                    run = minotourapi.create_run(sample_id, run_id, is_barcoded, has_fastq,
                                                            flowcell, minion,
                                                            flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['exp_start_time'])

                minion = minotourapi.get_minion_by_name(flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['device_id'])

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
                    "minKNOW_real_sample_rate": int(str(flowcelldict[sample_id][flowcellid][run_id]['context_tags']['sample_frequency'])),
                    "minKNOW_asic_id": flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['asic_id'],
                    "minKNOW_start_time": flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['exp_start_time'],
                    # "minKNOW_colours_string": str(self.rpc_connection.analysis_configuration.get_channel_states_desc()),
                    #"minKNOW_colours_string": str(
                    #    MessageToJson(self.rpc_connection.analysis_configuration.get_channel_states_desc(),
                    #                  preserving_proto_field_name=True, including_default_value_fields=True)),
                    "minKNOW_computer": str(flowcelldict[sample_id][flowcellid][run_id]['tracking_id']['hostname']),
                }
                payload['flowcell_type']=str(flowcelldict[sample_id][flowcellid][run_id]['context_tags']['flowcell_type'])
                payload['sequencing_kit']=str(flowcelldict[sample_id][flowcellid][run_id]['context_tags']['sequencing_kit'])
                #print (run)
                updateruninfo = minotourapi.update_minion_run_info(payload, run['id'])
                #print (updateruninfo)

    print ("Metadata Uploaded to MinoTour.")
