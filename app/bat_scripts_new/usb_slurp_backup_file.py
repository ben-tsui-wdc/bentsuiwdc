# -*- coding: utf-8 -*-
""" Test cases to check USB Slurp backup function.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import os

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class UsbSlurpBackupFile(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'USB Slurp Backup Test'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13984'
    COMPONENT = 'PLATFORM'

    def init(self):
        self.mount_path = '/mnt/media_rw/'
        self.root_folder = '/data/wd/diskVolume0/restsdk/userRoots/'

    def test(self):
        model = self.uut.get('model')
        if model == 'yoda':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(model))
        # Generate checksum list for the files in USB
        bat_chk_dic = {}
        self.usb_mount = self.adb.executeShellCommand('ls {}'.format(self.mount_path))[0].split()[0]
        usb_path = '{0}{1}/'.format(self.mount_path, self.usb_mount)
        usb_files = self.adb.executeShellCommand('find {0} -type f'.format(usb_path))[0]
        lists = [path.split(usb_path).pop() for path in usb_files.split()]
        for item in lists:
            if any(char.isdigit() for char in item) and not item.startswith('.'):
                md5sum = self.adb.executeShellCommand('busybox md5sum {0}{1}/{2}'
                                                      .format(self.mount_path, self.usb_mount, item),
                                                      consoleOutput=False)[0].split()[0]
                bat_chk_dic.update({item: md5sum})
        user_id = self.uut_owner.get_user_id()
        if 'auth0|' in user_id:
            user_id = user_id.replace('auth0|', 'auth0\|')
        copy_id, usb_info, resp = self.uut_owner.usb_slurp()
        self.usb_name = usb_info.get('name')
        PASSED = 0
        FAILED = 0
        for key, value in bat_chk_dic.iteritems():
            sync_chksum = self._md5_checksum(user_id, key)
            source_chksum = bat_chk_dic[key]
            self.log.info('{} - sync_chksum:{}, source_chksum:{}'.format(key, sync_chksum, source_chksum))
            if sync_chksum == source_chksum:
                PASSED += 1
            else:
                FAILED += 1
        if FAILED > 0:
            raise self.err.TestFailure('USB Slurp Backup Compare FAILED!! PASSED_FILES: {0}, FAILED_FILES: {1}'
                       .format(PASSED, FAILED))

    def _md5_checksum(self, user_id, file_name):
        usb_name = self.usb_name.replace(' ', '\ ')
        path = os.path.join(self.root_folder, user_id, usb_name, file_name)
        result = self.adb.executeShellCommand('busybox md5sum {}'.format(path), consoleOutput=False, timeout=180)
        self.log.debug(result)
        result = result[0].strip().split()[0]
        return result

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Check USB Slurp Backup Test Script ***
        Examples: ./run.sh bat_scripts_new/usb_slurp_backup_file.py --uut_ip 10.92.224.68\
        """)

    test = UsbSlurpBackupFile(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
