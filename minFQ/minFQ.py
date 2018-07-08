import os
import platform
import sys
import fnmatch, shutil, platform
import fileinput

import time
import threading



root_directory = os.path.dirname(os.path.realpath(__file__))

"""We are setting up the code to copy and import the rpc service from minKNOW and make
it work on our own code. This prevents us from having to distribute ONT code ourselves."""

def copyfiles(srcdir, dstdir, filepattern):
    def failed(exc):
        raise exc
    dstdir = os.path.join(root_directory,dstdir)
    for dirpath, dirs, files in os.walk(srcdir, topdown=True, onerror=failed):
        for file in fnmatch.filter(files, filepattern):
            shutil.copy2(os.path.join(dirpath, file), dstdir)
            editfile(os.path.join(dstdir,file),'minknow.rpc','minFQ.rpc')
        break # no recursion

def editfile(filename,text_to_search,replacement_text):
    with fileinput.FileInput(filename, inplace=True) as file:
        for line in file:
            print(line.replace(text_to_search, replacement_text), end='')


dstRPC = "rpc"

OPER = platform.system()

RPCPATH = os.path.join('ont-python','lib','python2.7','site-packages','minknow','rpc')

if os.path.isfile(os.path.join(root_directory, 'rpc', '__init__.py')):
    pass
else:
    print ("No RPC")
    if OPER == "Darwin":
        minknowbase = os.path.join(os.sep,'Applications','MinKNOW.app','Contents','Resources')
    elif OPER == "Linux":
        minknowbase = os.path.join(os.sep,'opt','ONT','MinKNOW')
    elif OPER == "Windows":
        minknowbase = os.path.join(os.sep,"Program Files",'OxfordNanopore','MinKNOW')
    else:
        print ("Not configured for {} yet. Sorry.".format(OPER))
        sys.exit()
    sourceRPC = os.path.join(minknowbase,RPCPATH)
    copyfiles(sourceRPC,dstRPC,'*.py')
    print ('RPC Configured')


sys.path.insert(0,os.path.join(root_directory, 'rpc'))



from minFQ.fastqutils import FastqHandler
from minFQ.minknowcontrolutils import HelpTheMinion
from minFQ.minknowconnection import MinknowConnect
import configargparse
from watchdog.observers.polling import PollingObserver as Observer

from minFQ.minotourapi import MinotourAPI
from minFQ.minknowconnection import MinknowConnect

CLIENT_VERSION = '1.0'


def main():

    global OPER

    OPER = platform.system()

    if OPER is 'Windows':  # MS

        OPER = 'windows'

    else:

        OPER = 'linux'  # MS

    if OPER is 'linux':

        config_file = os.path.join(os.path.sep, \
                                   os.path.dirname(os.path.realpath('__file__' \
                                                                    )), 'minfq_posix.config')
    if OPER is 'windows':

        config_file = os.path.join(os.path.sep, sys.prefix,
                                   'minfq_windows.config')

    parser = \
        configargparse.ArgParser(
            description='minFQ: A program to analyse minION fastq files in real-time or post-run and monitor the activity of MinKNOW.' \
            , default_config_files=[config_file])

    parser.add(
        '-w',
        '--watch-dir',
        type=str,
        required=True,
        default=None,
        help='The path to the folder containing the downloads directory with fast5 reads to analyse - e.g. C:\\data\\minion\\downloads (for windows).',
        dest='watchdir'
    )

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
        '-v',
        '--verbose',
        action='store_true',
        help='Display debugging information.',
        default=False,
        dest='verbose',
    )
    parser.add(
        '-nf',
        '--no_fastq',
        action='store_true',
        help='Run minFQ without monitoring fastq files.',
        default=False,
        dest='noFastQ',
    )

    parser.add(
        '-nm',
        '--no_minKNOW',
        action='store_true',
        help='Run minFQ without monitoring minKNOW for live activity.',
        default=False,
        dest='noMinKNOW',
    )

    parser.add(
        '-n',
        '--name',
        type=str,
        required=True,
        default=None,
        help='The run name you wish to provide.',
        dest='run_name',
    )

    parser.add(
        '-f',
        '--is_flowcell',
        action='store_true',
        help='If you add this flag, all runs added here will be considered as a single flow cell with the name set by the name flag.',
        dest='is_flowcell',
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
        help='The run name you wish to provide.',
        dest='host_name',
    )

    parser.add(
        '-tc',
        '--treatment-control',
        type=int,
        required=False,
        default=None,
        help='Optionally split reads based in treatment and control groups based on the channel number. The integer value informed is used to mover ish read to the control group.',
        dest='treatment_control'
    )

    parser.add(
        '-s',
        '--skip_sequence',
        action='store_true',
        required=False,
        help='If selected only read metrics, not sequence, will be uploaded to the databse.',
        dest='skip_sequence'
    )

    parser.add(
        '-g',
        '--gui',
        action='store_true',
        required=False,
        default=False,
        help='configure the code for GUI use.',
        dest='GUI'
    )

    args = parser.parse_args()

    # Makes no sense to run if both no minKNOW and no FastQ is set:
    if args.noFastQ and args.noMinKNOW:
        print("You must monitor either FastQ or MinKNOW.")
        print("This program will now exit.")
        os._exit(0)

    args.full_host = "http://{}:{}/".format(args.host_name, str(args.port_number))

    args.read_count = 0

    header = {
        'Authorization': 'Token {}'.format(args.api_key),
        'Content-Type': 'application/json'
    }

    minotourapi = MinotourAPI(args.full_host, header)

    version = minotourapi.get_server_version()

    shall_exit = False

    if not version:

        print("Server does not support this client. Please change the client to a previous version or upgrade server.")

        shall_exit = True

    clients = version['clients']

    if CLIENT_VERSION not in clients:

        print("Server does not support this client. Please change the client to a previous version or upgrade server.")

        shall_exit = True

    if not shall_exit:

        rundict = dict()

        if not args.noFastQ:
            event_handler = FastqHandler(args, header, rundict)
            # This block handles the fastq
            observer = Observer()
            observer.schedule(event_handler, path=args.watchdir, recursive=True)
            observer.daemon = True

        if not args.noMinKNOW:
            # this block is going to handle the running of minControl.
            minwsip = "ws://" + args.ip + ":9500/"
            #helper = HelpTheMinion(minwsip, args, header)
            #helper.connect()

            MinKNOWConnection = MinknowConnect(minwsip, args, header)
            MinKNOWConnection.connect()

        try:

            if not args.noFastQ:

                observer.start()

            #if not args.noMinKNOW:

                #t = threading.Thread(target=helper.process_minion())
                #t.daemon = True
                #t.start()

            while 1:

                time.sleep(1)

        except KeyboardInterrupt:

            print(": Exiting")

            if not args.noMinKNOW:
                #helper.mcrunning = False
                #helper.hang_up()
                pass
            MinKNOWConnection.disconnect_nicely()

            if not args.noFastQ:
                observer.stop()
                observer.join()

            os._exit(0)


if __name__ == '__main__':

    main()
