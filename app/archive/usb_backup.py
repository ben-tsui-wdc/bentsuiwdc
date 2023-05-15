___author___ = 'Kurt Jensen <kurt.jensen@wdc.com>'
#edited by v

from platform_libraries.adblib import ADB
import time
import argparse
import threading
import logging
from itertools import count
from platform_libraries import common_utils

class UsbBackup(object):
    _ids = count(0)

    def __init__(self, adb=None, source='/storage/55E7-C75B/test_data/', destination='/data/wd/diskVolume0/usbcopy/'):
        self.id = self._ids.next()
        self.adb = adb
        self.sourceFolder = str(source)
        self.destinationFolder = destination[:-1] + str(self.id) + '/'

        self.cpCommand = 'cp -F '
        self.rmCommand = 'rm -rf %s' %(self.destinationFolder)

        self.listFilesCommand = 'ls %s' %(self.sourceFolder)
        #self.filesizeCommand = 'busybox stat -c%%s '
        self.isRunning = False
        self.listOfCopySpeeds = []

        self.deviceModel = self.adb.getModel()
        self.deviceFirmware = self.adb.getFirmwareVersion()
        
        #formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-4s: %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        #common_utils.setupLogger(loggerName='usb', logfile='output/adb/usb.log', level=logging.DEBUG, formatter=formatter)
        common_utils.setupLogstashLogger(loggerName='usb{}'.format(self.id), level=logging.INFO, tags=[self.adb.uut_ip, "testresult"])
        self.log = logging.getLogger('usb{}'.format(self.id))

    def run(self):
        self.t1 = threading.Thread(target=self.usbBackupTest)
        self.t1.start()
        self.isRunning = True

    def stop(self):
        self.isRunning = False
        print 'Stopping usb {}'.format(self.id)
        self.t1.join()
        print 'Stopped usb {}'.format(self.id)

    def usbBackupTest(self):
        self.adb.connect() # make sure device is connected
        # remove output folder if it exists, or clear it before next iteration
        self.adb.executeShellCommand(cmd=self.rmCommand)
        count = 0
        while self.isRunning:
            self.makeOutputDir()
            self.listOfFiles = self.getListOfFiles()
            for file in self.listOfFiles:
                file = str(file)
                self.cpCommand = 'cp -F ' + '%s%s %s%s' %(self.sourceFolder, file, self.destinationFolder, file)
                filesizeCommand = 'busybox stat -c%%s "%s%s"' %(self.sourceFolder, file)

                filesize = self.getFilesize(cmd=filesizeCommand)
                filesizeCommand = ''
                start = time.time()
                self.adb.executeShellCommand(cmd=self.cpCommand, timeout=1000, consoleOutput=True)
                executionTime = time.time() - start

                copySpeed = filesize / executionTime

                self.listOfCopySpeeds.append(copySpeed)
                copySpeed = copySpeed / (1024*1024.0)
                extra = {'component':'usb','usb_copy_speed':copySpeed, 'device_ip':self.adb.uut_ip, 'model':self.deviceModel, 'firmware':self.deviceFirmware, 'iteration':count}
                self.log.info('USB copy', extra=extra)
                self.adb.executeShellCommand(cmd=self.rmCommand)
                print 'Copy Speed MB/sec: ' + str(copySpeed)
            count = count + 1
            

    def getAverageCopySpeed(self):
        averageSpeed = sum(self.listOfCopySpeeds) / len(self.listOfCopySpeeds)
        return averageSpeed

    def getListOfFiles(self):
        stdout, stderr = self.adb.executeShellCommand(cmd=self.listFilesCommand, consoleOutput=True)
        # Split stdout, returned in filename1\r\nfilename2\r\n... format
        fileList = stdout.split('\r\n')
        # Remove end element which is '' empty due to split
        del fileList[-1]
        return fileList

    def makeOutputDir(self):    
        mkDirCommand = 'mkdir -p ' + self.destinationFolder
        self.adb.executeShellCommand(cmd=mkDirCommand, consoleOutput=True)

    def getFilesize(self, cmd=None):
        stdout, stderr = self.adb.executeShellCommand(cmd=cmd, consoleOutput=True)
        return int(stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    parser.add_argument('-iter', help='Number of iterations')
    parser.add_argument('-dest', help='Filepath of destination, ex. /data/local/diskVolume0/5g.img')
    parser.add_argument('-source', help='Filepath of sourcefile, ex. /storage/57B6-3F8D/5G.img')
    parser.add_argument('-timer', help='Time to execute test (minutes), ex. 30')

    args = parser.parse_args()

    uut_ip = args.uut_ip
    if args.port:
        port = args.port
    else:
        port = '5555'
    if args.iter:
        iterations = int(args.iter)
    else:
        iterations = 1
    if args.source:
        usbSource = str(args.source)
    else:
        usbSource = '/storage/55E7-C75B/test_data/'
    if args.dest:
        usbDestination = str(args.dest)
    else:
        usbDestination = '/data/wd/diskVolume0/usbcopy/'
    if args.timer:
        timer = int(args.timer)
    else:
        timer = 30
    
    adb = ADB(uut_ip=uut_ip, port='5555')
    adb.connect()
    usb = UsbBackup(adb=adb, source=usbSource, destination=usbDestination)
    usb.getListOfFiles()

    try:
        usb.run()
    except Exception as e:
        print 'Exception ! %s' %(e)
    try:    
        time.sleep(timer*60)
    except KeyboardInterrupt:
        usb.stop()
        usb.getAverageCopySpeed
        adb.disconnect()
        
    usb.stop()
    usb.getAverageCopySpeed
    adb.disconnect()


