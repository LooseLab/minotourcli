import os
import platform
import sys
import fnmatch, shutil, platform
import fileinput
import logging
import logging.handlers
import time
import threading
import validators

"""We are setting up the code to copy and import the rpc service from minKNOW and make
it work on our own code. This prevents us from having to distribute ONT code ourselves."""

root_directory = os.path.dirname(os.path.realpath(__file__))

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


if not os.path.exists(os.path.join(root_directory, 'rpc')):
    os.makedirs(os.path.join(root_directory, 'rpc'))
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

def up(lines=1):
    clearline = '\033[2K' # clear a line
    upline = '\033[1A'    # Move cursor up a line
    for _ in range(lines):
        sys.stdout.write(upline)
        sys.stdout.write(clearline)

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
        required=False,
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
        default=80,
        help='The port number for the minoTour server.',
        dest='port_number',
    )

    parser.add(
        '-hn',
        '--hostname',
        type=str,
        # required=True,
        default='127.0.0.1',
        help='The host name for the minoTour server.',
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

    parser.add(
        '-ll',
        '--loglevel',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level',
        dest = 'loglevel'
    )

    args = parser.parse_args()

    if not args.noMinKNOW and args.ip is None:
        parser.error("To monitor MinKNOW in real time you must specify the IP address of your local machine.\nUsually:\n-ip 127.0.0.1")

    # Makes no sense to run if both no minKNOW and no FastQ is set:
    if args.noFastQ and args.noMinKNOW:
        print("You must monitor either FastQ or MinKNOW.")
        print("This program will now exit.")
        os._exit(0)

    if args.host_name.startswith("http://"):
        args.full_host = "{}:{}/".format(args.host_name, str(args.port_number))
    else:
        args.full_host = "http://{}:{}/".format(args.host_name, str(args.port_number))

    if not validators.url(args.full_host):
        print ("Please check your url.")
        print ("You entered:")
        print ("{}".format(args.host_name))
        sys.exit()

    logging.basicConfig(
        format='%(asctime)s %(module)s:%(levelname)s:%(thread)d:%(message)s',
        filename='minFQ.log',
        #level=os.environ.get('LOGLEVEL', 'INFO')
        level = args.loglevel
    )

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    #formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    formatter = logging.Formatter('%(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)

    log = logging.getLogger(__name__)

    log.info("Initialising minFQ.")

    args.read_count = 0

    header = {
        'Authorization': 'Token {}'.format(args.api_key),
        'Content-Type': 'application/json'
    }

    minotourapi = MinotourAPI(args.full_host, header)

    version = minotourapi.get_server_version()

    log.info(version)

    shall_exit = False

    if not version:

        log.error("Server does not support this client. Please change the client to a previous version or upgrade server.")

        shall_exit = True

    clients = version['clients']


    if CLIENT_VERSION not in clients:

        log.error("Server does not support this client. Please change the client to a previous version or upgrade server.")

        shall_exit = True

    if not shall_exit:

        rundict = dict()


        if not args.noFastQ:
            log.info("Setting up FastQ monitoring.")
            event_handler = FastqHandler(args, header, rundict)
            # This block handles the fastq
            observer = Observer()
            observer.schedule(event_handler, path=args.watchdir, recursive=True)
            observer.daemon = True
            log.info("FastQ Monitoring Running.")

        if not args.noMinKNOW:
            # this block is going to handle the running of minControl.
            log.info("Configuring MinKNOW Monitoring.")
            minwsip = "ws://" + args.ip + ":9500/"

            MinKNOWConnection = MinknowConnect(minwsip, args, header)
            MinKNOWConnection.connect()
            log.info("MinKNOW Monitoring Working.")

        sys.stdout.write("To stop minFQ use CTRL-C.\n")

        try:

            if not args.noFastQ:

                observer.start()

            while 1:
                linecounter = 0
                if not args.noFastQ:

                    sys.stdout.write('{}\n'.format(args.fastqmessage))
                    sys.stdout.write('FastQ Upload Status:\n')
                    sys.stdout.write('Files queued/processed/skipped:{}/{}/{}\n'.format(
                        args.files_seen - args.files_processed - args.files_skipped,
                        args.files_processed,
                        args.files_skipped
                    ))
                    sys.stdout.write('New reads seen/uploaded/skipped:{}/{}/{}\n'.format(
                        args.reads_seen-args.reads_uploaded-args.reads_skipped,
                        args.reads_uploaded,
                        args.reads_skipped
                    ))

                    linecounter+=4

                if not args.noMinKNOW:

                    sys.stdout.write('MinKNOW Monitoring Status:\n')
                    sys.stdout.write("Connected minIONs: {}\n".format(MinKNOWConnection.minIONnumber()))
                    linecounter+=2


                sys.stdout.flush()

                time.sleep(1)
                if not args.verbose: up(linecounter)

        except KeyboardInterrupt:

            log.info("Exiting - Will take a few seconds to clean up!")

            if not args.noMinKNOW:
                MinKNOWConnection.disconnect_nicely()

            if not args.noFastQ:
                observer.stop()
                observer.join()

            os._exit(0)


if __name__ == '__main__':

    main()
