___author___ = 'Kurt Jensen <kurt.jensen@wdc.com>'

from platform_libraries.adblib import ADB
from platform_libraries import common_utils

import time
import argparse
import threading
import logging
from itertools import count

class Transcoding(object):
    _ids = count(0)

    def __init__(self, adb=None, source='/data/wd/diskVolume0/jazz.mp4', destination='/data/wd/diskVolume0/ffmpeg_test/output/test'):
        self.id = self._ids.next()
        self.adb = adb
        self.adb.executeShellCommand(cmd="mkdir -p /data/wd/diskVolume0/ffmpeg_test/output")
        self.transcodeCommand = '/system/bin/ffmpeg  -eFps 30 -eWid 1280 -eHei 720  -re -i {0} -c:a copy -c:v h264 -b:v 2500k -mediacodec_output_size 1280x720 {1}{2}.ts'.format(source,destination,self.id)
        print self.transcodeCommand
        self.rmCommand = rmCommand = 'rm -rf {0}{1}.ts'.format(destination, self.id)

        self.deviceModel = self.adb.getModel()
        self.deviceFirmware = self.adb.getFirmwareVersion()

    def run(self):
        self.t1 = threading.Thread(target=self.transcodingTest)
        self.t1.start()
        self.isRunning = True

    def stop(self):
        if self.isRunning:
            self.isRunning = False
            print 'Stopping transcoding {}'.format(self.id)
            self.t1.join()
            print 'Stopped transcoding {}'.format(self.id)
        else:
            print 'Thread already stopped'

    def transcodingTest(self):
        self.adb.connect()
        self.adb.executeShellCommand(cmd=self.rmCommand)
        count = 0
        while self.isRunning:
            stdout, stderr = self.adb.executeShellCommand(cmd=self.transcodeCommand, timeout=3600, consoleOutput=True)
            stdoutList = stdout.strip().split()

            #remove transcoded output
            self.adb.executeShellCommand(cmd=self.rmCommand)
            count = count + 1
            

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Test script for transcoding, 2 threads created')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    parser.add_argument('-iter', help='Number of iterations')
    #parser.add_argument('-dest', help='Filepath of destination, ex. /data/local/diskVolume0/output.ts')
    #parser.add_argument('-source', help='Filepath of sourcefile, ex. /storage/57B6-3F8D/movie.mp4')
    parser.add_argument('-timer', help='Time to execute test (minutes), ex. 30')

    args = parser.parse_args()

    if (args.iter and args.timer):
        parser.error('Iterations and timer specified, please pick one')

    uut_ip = args.uut_ip
    if args.port:
        port = args.port
    else:
        port = '5555'
    if args.iter:
        iterations = int(args.iter)
    else:
        iterations = 1
    '''
    if args.source:
        source = str(args.source)
    else:
        source = '/data/wd/diskVolume0/jazz.mp4'
    if args.dest:
        destination = str(args.dest)
    else:
        destination = '/data/wd/diskVolume0/jazz.ts'
    '''
    if args.timer:
        timer = int(args.timer)
    else:
        timer = 30

    adb = ADB(uut_ip=uut_ip, port='5555')
    adb.connect()
    time.sleep(1)
    transcoding1 = Transcoding(adb=adb)
    transcoding1.run()
    transcoding2 = Transcoding(adb=adb)
    transcoding2.run()

    for i in xrange(0, timer):
        print 'Minute: %i of %i' %(i, timer)
        time.sleep(60)
    print 'done sleeping'
    transcoding1.stop()
    transcoding2.stop()
    print 'Transcoding thread1 stopped..'

    adb.disconnect()
