__author__ = 'Kurt Jensen <kurt.jensen@wdc.com'

from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from platform_libraries.monsoon_wrapper import MonsoonWrapper
from platform_libraries.device_monitor import AndroidDeviceMonitor
import time
import argparse
import threading
from transcoding_test import Transcoding
from usb_backup import UsbBackup
from stress_tests import UsbTranscodingStressTest


usbSource = '/storage/57B6-3F8D/test_data/'
usbDestination ='/data/wd/diskVolume0/usbcopy/'

transcodingSource = '/data/wd/diskVolume0/jazz.mp4'
transcodingDestination = '/data/wd/diskVolume0/jazz.ts'

parser = argparse.ArgumentParser(description='execute stress test for platform')
parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
parser.add_argument('-usbDest', help='Filepath of usbcopy destination, ex. /data/local/diskVolume0/5g.img')
parser.add_argument('-usbSource', help='Filepath of usbcopy sourcefile, ex. /storage/57B6-3F8D/movie.mp4')
parser.add_argument('-tSource', help='Filepath of transcoding sourcefile, ex. /data/local/diskVolume0/video.mp4')
parser.add_argument('-tDest', help='Filepath of transcoding destination, ex. /data/local/diskVolume0/output.ts')
parser.add_argument('-timer', help='Time to execute test (minutes), ex. 30')
parser.add_argument('-post_wait', help='sleep after test execution (minutes), ex 30')
parser.add_argument('-usbT', help='Number of USB threads to execute, ex. 1')
parser.add_argument('-transT', help='Number of transcoding threads to execute, ex. 2')

args = parser.parse_args()

uut_ip = args.uut_ip
if args.port:
    port = str(args.port)
else:
    port = '5555'
if args.usbSource:
    usbSource = str(args.usbSource)
if args.usbDest:
    usbDestination = str(args.usbDest)
if args.tSource:
    transcodingSource = str(args.tSource)
if args.tDest:
    transcodingDestination = str(args.tDest)
if args.timer:
    timer = int(args.timer)
else:
    timer = 30
if args.post_wait:
    postWait = int(args.post_wait)
else:
    postWait = 30
if args.usbT:
    usbThreads = args.usbT
else:
    usbThreads = 1
if args.transT:
    transThreads = args.transT
else:
    transThreads = 2

mon = MonsoonWrapper(prometheusDevice='monarch_pm')
#Set vout to 4.2V, turn on usbpassthrough, max current at 8 amps
mon.setOutputValues(usb=1, vout=4.2, maxCurrent=8)
# Start logging data at 5hz
mon.startDataLogging(hz=1, prometheusUpload=False, logstashUpload=True)

time.sleep(120)

adb = ADB(uut_ip=uut_ip, port='5555')
adb.connect()
time.sleep(5)

print usbSource

stress = UsbTranscodingStressTest(adb=adb, numTranscodingThreads=transThreads, numUsbThreads=usbThreads, usbSource=usbSource)
### RUN INDEFINITELY ###
try:
    stress.run(timer=timer)
except Exception as e:
    print 'Exception! %s' %(e)

adb.disconnect()

time.sleep(postWait*60)

mon.stopDataLogging()



