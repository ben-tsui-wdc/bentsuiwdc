# -*- coding: utf-8 -*-
""" Test cases to check Samba Read/Write test.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import os
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class SambaRW(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Basic Samba Read&Write Test'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13981'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.samba_user = None
        self.samba_password = None

    def init(self):
        self.time_out = 60*5
        self.sharelocation = '//{}/Public'.format(self.adb.uut_ip)
        self.mountpoint = '/mnt/cifs'
        self._ismounted = False
        self.count = 50
        self.filename = 'test{}MB'.format(self.count)
        self.model = self.adb.getModel()

    def test(self):
        if self.model == 'yoda':
            raise self.err.TestSkipped('Device is Yoda! Skip the test !!')
        else:
            if not os.path.isdir(self.mountpoint):
                os.mkdir(self.mountpoint)
            self.mountsamba()
            self.adb.executeCommand('dd if=/dev/urandom of={0} bs=1M count={1}'.format(self.filename, self.count))
            self.adb.executeCommand('cp -f {0} {1}'.format(self.filename, self.mountpoint), timeout=self.time_out)
            file1 = self.adb.executeCommand('md5sum {0}'.format(self.filename))[0]
            file2 = self.adb.executeShellCommand('md5sum {0}/{1}'.format('/data/wd/diskVolume0/samba/share', self.filename))[0]
            if not file1.split()[0] == file2.split()[0]:
                raise self.err.TestFailure('Basic Samba RW Test FAILED!! Err: md5 checksum NOT match!!')

    def mountsamba(self):
        user = self.samba_user
        password = self.samba_password
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
        self.log.info('Mounting {} '.format(sharelocation))
        stdout, stderr = self.adb.executeCommand(mount_cmd + ' ' + mount_args)
        self.log.info('cmd= ' + mount_cmd + ' ' + mount_args)
        if 'No such file or directory' in stderr:
            self.log.warning("'mount error(2): No such file or directory' happened on {} path, \
                wait 1 min and try again...".format(sharelocation))
            time.sleep(60)
            self.adb.executeCommand(mount_cmd + ' ' + mount_args)
        mounted = self.adb.executeCommand('df')[0]
        if self.mountpoint in mounted:
            self._ismounted = True
        else:
            raise self.err.TestFailure('Mount samba folder failed!')

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

    def after_test(self):
        self.removeallcontentfiles(self.mountpoint)
        self.umountshare()
        os.remove(self.filename)

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Samba Read/Write Check Script ***
        Examples: ./run.sh bat_scripts_new/samba_rw_check.py --uut_ip 10.92.224.68\
        """)

    # Test Arguments
    parser.add_argument('--samba_user', help='Samba login user name')
    parser.add_argument('--samba_password', help='Samba login password')

    test = SambaRW(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
