# -*- coding: utf-8 -*-
""" Test cases to check USB Slurp delete files function.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import os
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class UsbSlurpDeleteFile(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Delete USB Slurp backup files on the device'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13985'
    COMPONENT = 'PLATFORM'

    def init(self):
        self.mount_path = '/mnt/media_rw/'
        self.root_folder = '/data/wd/diskVolume0/restsdk/userRoots/'

    def test(self):
        model = self.uut.get('model')
        if model == 'yoda':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(model))
        # Generate checksum list for the files in USB
        self.usb_mount = self.adb.executeShellCommand('ls {}'.format(self.mount_path))[0].split()[0]
        usb_path = '{0}{1}/'.format(self.mount_path, self.usb_mount)
        usb_files = self.adb.executeShellCommand('find {0} -type f'.format(usb_path))[0]
        lists = [path.split(usb_path).pop() for path in usb_files.split()]
        user_id = self.uut_owner.get_user_id()
        if 'auth0|' in user_id:
            user_id = user_id.replace('auth0|', 'auth0\|')
        copy_id, usb_info, resp = self.uut_owner.usb_slurp()
        self.usb_name = usb_info.get('name')
        usb_name = self.usb_name.replace(' ', '\ ')
        usb_path = os.path.join(self.root_folder, user_id, usb_name)
        usb_sync_files1 = self.adb.executeShellCommand('find {0} -type f'.format(usb_path))[0]
        sync_lists = [path for path in usb_sync_files1.split('\r\n')]
        sync_lists.pop()
        self.log.info('Current Sync Files: {}'.format(sync_lists))
        num_file = len(sync_lists)

        # Delete Files
        delete = 0
        for file in sync_lists:
            usb_folder, search_time = self.uut_owner.search_file_by_parent_and_name(parent_id='root', name=self.usb_name)
            folder_id = usb_folder['id']
            folder_name = file.split(self.usb_name)[1].split('/')[1]
            file = file.split(self.usb_name+'/')[1]
            while '/' in file:
                folder, search_time = self.uut_owner.search_file_by_parent_and_name(parent_id=folder_id, name=folder_name)
                folder_id = folder['id']
                file = file.split(folder_name+'/')[1]
                folder_name = file.split('/')[0]
            self.log.info("Deleting file: {}".format(file))
            file_info, search_time = self.uut_owner.search_file_by_parent_and_name(parent_id=folder_id, name=file)
            file_id = file_info['id']
            result, timing = self.uut_owner.delete_file(file_id)
            if result:
                self.log.info('{} has been deleted'.format(file))
                delete += 1
            else:
                self.error("Delete file: {} failed!".format(file))
        time.sleep(10)

        # Check usb sync folder files status
        usb_sync_files2 = self.adb.executeShellCommand('find {0} -type f'.format(usb_path))[0]
        sync_lists = [path for path in usb_sync_files2.split('\r\n')]
        sync_lists.pop()
        self.log.info('Current Sync Files: {}'.format(sync_lists))
        for item in sync_lists:
            if item in lists:
                raise self.err.TestFailure('USB Slurp Delete Files FAILED!! {} is not DELETED!!'.format(item))
        else:
            self.log.info('There have {} files, Total Delete {} files'.format(num_file, delete))

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Check USB Slurp Delete Files Test Script ***
        Examples: ./run.sh bat_scripts_new/usb_slurp_delete_file.py --uut_ip 10.92.224.68\
        """)

    test = UsbSlurpDeleteFile(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
