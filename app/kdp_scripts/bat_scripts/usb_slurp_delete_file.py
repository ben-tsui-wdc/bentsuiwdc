# -*- coding: utf-8 -*-
""" Test cases to check delete USB Slurp backup files on the device.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import os
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP


class UsbSlurpDeleteFile(KDPTestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'KDP-199 - Delete USB Slurp backup files on the device'
    TEST_JIRA_ID = 'KDP-199'

    def test(self):
        # Generate checksum list for the files in USB
        status, output = self.ssh_client.execute('ls {}'.format(KDP.MOUNT_PATH))
        self.usb_mount = output.split()[0]
        usb_path = '{0}{1}/'.format(KDP.MOUNT_PATH, self.usb_mount)
        status, usb_files = self.ssh_client.execute('find {0} -type f'.format(usb_path))
        lists = [path.split(usb_path).pop() for path in usb_files.split()]
        user_id = self.uut_owner.get_user_id()
        if 'auth0|' in user_id:
            user_id = user_id.replace('auth0|', 'auth0\|')
        copy_id, usb_info, resp = self.uut_owner.usb_slurp()
        self.usb_name = usb_info.get('name')
        if self.ssh_client.check_is_kdp_device():
            usb_name = self.usb_name.replace(' ', '\ ')
            usb_path = os.path.join(KDP.USER_ROOT_PATH, user_id, usb_name)
            status, usb_sync_files1 = self.ssh_client.execute('find {0} -type f'.format(usb_path))
            sync_lists = [path for path in usb_sync_files1.split('\r\n')]
            sync_lists.pop()
            self.log.info('Current Sync Files: {}'.format(sync_lists))
            num_file = len(sync_lists)

        # Delete Files
        delete = 0
        if self.ssh_client.check_is_rnd_device():
            self.uut_owner.delete_file_by_name(self.usb_name)
        else:
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

        if self.ssh_client.check_is_kdp_device():
            # Check usb sync folder files status
            status, usb_sync_files2 = self.ssh_client.execute('find {0} -type f'.format(usb_path))
            sync_lists = [path for path in usb_sync_files2.split('\r\n')]
            sync_lists.pop()
            self.log.info('Current Sync Files: {}'.format(sync_lists))
            for item in sync_lists:
                if item in lists:
                    raise self.err.TestFailure('USB Slurp Delete Files FAILED!! {} is not DELETED!!'.format(item))
            else:
                self.log.info('There have {} files, Total Delete {} files'.format(num_file, delete))
        else:
            response = self.uut_owner.search_file_by_parent_and_name(self.usb_name, no_raise_error=True)
            print response
            if response.status_code == 404 and response.json()['message'] == 'Not Found':
                self.log.info('USB folder has been deleted !!')
            else:
                raise self.err.TestFailure('USB Slurp Delete Files FAILED!!')

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Check delete USB Slurp backup files on the device Test Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/usb_slurp_delete_file.py --uut_ip 10.92.224.68\
        """)

    test = UsbSlurpDeleteFile(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
