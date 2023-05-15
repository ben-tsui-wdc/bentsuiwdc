___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from junit_xml import TestCase


class sambaRW(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env
        self.start_time = time.time()
        self.testcase = None
        self.device_init()
        self._ismounted = False
        self.sharelocation = '//{}/Public'.format(self.adb.uut_ip)
        self.mountpoint = '/mnt/cifs'
        self.user = None
        self.password = None
        self.count = 50
        self.filename = 'test{}MB'.format(self.count)

    def run(self):
        try:
            if not os.path.isdir(self.mountpoint):
                os.mkdir(self.mountpoint)
            self.mountsamba()
            self.adb.executeCommand('dd if=/dev/urandom of={0} bs=1M count={1}'.format(self.filename, self.count))
            self.adb.executeCommand('cp -f {0} {1}'.format(self.filename, self.mountpoint), timeout=300)
            file1 = self.adb.executeCommand('md5sum {0}'.format(self.filename))[0]
            file2 = self.adb.executeShellCommand('md5sum {0}/{1}'.format('/data/wd/diskVolume0/samba/share', self.filename))[0]
            if file1.split()[0] == file2.split()[0]:
                print 'Basic Samba RW Test PASSED!!'
                self.testcase = TestCase(name='Basic Samba RW Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            else:
                self.testcase = TestCase(name='Basic Samba RW Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
                self.testcase.add_failure_info('Basic Samba RW Test FAILED!! Err: md5 checksum NOT match!!')
            self.removeallcontentfiles(self.mountpoint)
            self.umountshare()
            os.remove(self.filename)
        except Exception as ex:
            self.testcase = TestCase(name='Basic Samba RW Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            self.testcase.add_failure_info('Basic Samba RW Test FAILED!! Err: {}'.format(ex))
            raise Exception('Test Failed. Err: {}'.format(ex))
        finally:
            return self.testcase

    def device_init(self):
        try:
            self.adb.connect()
            time.sleep(2)
            version = self.adb.getFirmwareVersion()
            platform = self.adb.getModel()
            print 'Firmware is :{}'.format(version.split()[0])
            print 'Platform is :{}'.format(platform.split()[0])
            time.sleep(1)
            return version.split()[0], platform.split()[0]
        except Exception as ex:
            raise Exception('Failed to connect to device and execute adb command! Err: {}'.format(ex))

    def mountsamba(self):
        user = self.user
        password = self.password
        mountpoint = self.mountpoint
        sharelocation = self.sharelocation

        if user is None:
            authentication = 'guest'
        else:
            if password is None:
                password = ''

            authentication = 'username=' + user + ',password=' + password

        mount_cmd = 'mount.cifs'
        mount_args = (sharelocation +
                      ' ' +
                      mountpoint +
                      ' -o ' +
                      authentication +
                      ',' +
                      'rw,nounix,file_mode=0777,dir_mode=0777')

        # Run the mount command
        print 'Mounting {} '.format(sharelocation)
        self.adb.executeCommand(mount_cmd + ' ' + mount_args)
        print mount_cmd + ' ' + mount_args
        mounted = self.adb.executeCommand('df')[0]
        if self.mountpoint in mounted:
            self._ismounted = True
        else:
            raise Exception('Mount samba folder failed!')

    def removeallcontentfiles(self, path):
        import shutil
        for root, dirs, files in os.walk(path):
            for f in files:
                os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))

    def umountshare(self):
        umount_cmd = 'umount'
        umount_args = '-l -f ' + self.mountpoint

        # Run the umount command
        self.adb.executeCommand(umount_cmd + ' ' + umount_args)

        os.rmdir(self.mountpoint)

        # Clear the mountpoint
        self.mountpoint = None
        self._ismounted = False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    if args.port:
        port = args.port
    else:
        port = '5555'
    adb = ADB(uut_ip=uut_ip, port=port)

    testrun = sambaRW(adb=adb)
    testrun.run()
