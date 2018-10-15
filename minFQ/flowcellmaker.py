import os
import sys
import datetime
from ont_fast5_api import fast5_file

from minFQ.minotourapi import MinotourAPI

walk_dir = sys.argv[1]

api_key = "73800956cdb157d48493a4f07711a69450cfdb3e"

print('walk_dir = ' + walk_dir)

# If your current working directory may change during script execution, it's recommended to
# immediately convert program arguments to an absolute path. Then the variable root below will
# be an absolute path as well. Example:
# walk_dir = os.path.abspath(walk_dir)

#create a dictionary of minIONS that we have seen

minION = set()
flowcelldict = dict()
rundict = dict()

def main():
    print('walk_dir (absolute) = ' + os.path.abspath(walk_dir))
    last_seen=""
    for root, subdirs, files in os.walk(walk_dir):
        files.sort()
        for file in files:
            if file.endswith("fast5"):
                if file.split('_read_')[0] != last_seen:
                    print (last_seen,file.split('_read_')[0])
                    last_seen = file.split('_read_')[0]
                    try:
                        myfile  = fast5_file.Fast5File(os.path.join(root,file))
                        #print (myfile.get_tracking_id())
                        minIONid = myfile.get_tracking_id()['device_id']
                        minION.add(minIONid)
                        flowcell = myfile.get_tracking_id()['flow_cell_id']
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
                else:
                    print ("same read")

                #print (myfile.get_context_tags())


    print (minION)
    print (flowcelldict)

    full_host = "http://{}:{}/".format("147.188.173.55", str(80))

    header = {
        'Authorization': 'Token {}'.format(api_key),
        'Content-Type': 'application/json'
    }

    minotourapi = MinotourAPI(full_host, header)


    for minIONs in minION:
        print ("Create {}".format(minIONs))
        minion = minotourapi.get_minion_by_name(minIONs)
        if not minion:
            minion = minotourapi.create_minion(minIONs)
        minion = minion

    for sample_id in flowcelldict:
        for flowcellid in flowcelldict[sample_id]:
            flowcell = minotourapi.get_flowcell_by_name(flowcellid)
            if not flowcell:
                flowcell = minotourapi.create_flowcell(flowcellid)

            for run_id in flowcelldict[sample_id][flowcellid]:
                print (run_id)
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
                print (run)
                updateruninfo = minotourapi.update_minion_run_info(payload, run['id'])
                print (updateruninfo)
