__author__ = 'Kurt Jensen <kurt.jensen@wdc.com>'

import time
import argparse
import threading
from itertools import count

from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from platform_libraries.device_monitor import AndroidDeviceMonitor
from transcoding_test import Transcoding
from usb_backup import UsbBackup

class UsbTranscodingStressTest(object):
    _ids = count(0)

    def __init__(self, adb=None, numTranscodingThreads=1, numUsbThreads=1, usbSource='/storage/55E7-C75B/test_data/',
                 transcodingSource='/data/wd/diskVolume0/jazz.mp4'):
        self.id = self._ids.next()
        self.adb = adb
        self.usbThreads = []
        self.transcodingThreads = []
        for i in range(0,numUsbThreads):
            self.usbThreads.append(UsbBackup(adb=adb, source=usbSource))
        for j in range(0,numTranscodingThreads):
            self.transcodingThreads.append(Transcoding(adb=adb, source=transcodingSource))

    def run(self, timer=1):
        print 'Starting {0} usb threads and {1} transcoding threads'.format(len(self.usbThreads), len(self.transcodingThreads))
        try:
            for usb in self.usbThreads:
                print 'Starting USB'
                usb.run()
                time.sleep(2)
            for transcoding in self.transcodingThreads:
                print 'Starting transcoding'
                transcoding.run()
                time.sleep(2)
            time.sleep(timer*60)
            print 'Done sleeping'
            self.stop()
        except Exception as e:    
            self.stop()

    def stop(self):
        print 'Stopping..'
        for transcoding in self.transcodingThreads:
            transcoding.stop()
        for usb in self.usbThreads:
            usb.stop()



if __name__ == '__main__':
    usbSource = '/storage/55E7-C75B/test_data/'
    usbDestination ='/data/wd/diskVolume0/usbcopy/'

    transcodingSource = '/data/wd/diskVolume0/jazz.mp4'
    transcodingDestination = '/data/wd/diskVolume0/jazz.ts'
    t2source = '/data/wd/diskVolume0/jazz.mp4'
    t2dest = '/data/wd/diskVolume0/jazz1.ts'

    parser = argparse.ArgumentParser(description='execute stress test for platform')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    parser.add_argument('-server_ip', help='ADB server ip address',default=None)
    parser.add_argument('-server_port', help='ADB server port number', default=None)
    parser.add_argument('-usbDest', help='Filepath of usbcopy destination, ex. /data/local/diskVolume0/5g.img')
    parser.add_argument('-usbSource', help='Filepath of usbcopy sourcefile, ex. /storage/57B6-3F8D/movie.mp4')
    parser.add_argument('-tSource', help='Filepath of transcoding sourcefile, ex. /data/local/diskVolume0/video.mp4')
    parser.add_argument('-tDest', help='Filepath of transcoding destination, ex. /data/local/diskVolume0/output.ts')
    parser.add_argument('-timer', help='Time to execute test (minutes), ex. 30')
    parser.add_argument('-usbT', help='Number of USB threads to execute, ex. 1')
    parser.add_argument('-transT', help='Number of transcoding threads to execute, ex. 2')

    args = parser.parse_args()

    uut_ip = args.uut_ip
    if args.port:
        port = str(args.port)
    else:
        port = '5555'
    if args.usbSource:
        usbSource = args.usbSource
    if args.usbDest:
        usbDestination = args.usbDest
    if args.tSource:
        transcodingSource = args.tSource
    if args.tDest:
        transcodingDestination = args.tDest
    if args.timer:
        timer = int(args.timer)
    else:
        timer = 30
    if args.usbT:
        usbThreads = int(args.usbT)
    else:
        usbThreads = 1
    if args.transT:
        transThreads = int(args.transT)
    else:
        transThreads = 1
    adbServer = args.server_ip
    adbServerPort = args.server_port


    adb = ADB(uut_ip=uut_ip, port='5555', adbServer=adbServer, adbServerPort=adbServerPort)
    adb.connect()
    time.sleep(5)
    stress = UsbTranscodingStressTest(adb=adb, numUsbThreads=usbThreads, numTranscodingThreads=transThreads, usbSource=usbSource)
    stress.run(timer=timer)
    adb.disconnect()