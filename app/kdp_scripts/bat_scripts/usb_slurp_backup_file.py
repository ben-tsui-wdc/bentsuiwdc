# -*- coding: utf-8 -*-
""" Test cases to check USB Slurp backup function.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"
__author2__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time
import os
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP
from platform_libraries.constants import RnD


class UsbSlurpBackupFile(KDPTestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'KDP-207 - USB Slurp Backup file Test'
    TEST_JIRA_ID = 'KDP-207'

    def test(self):
        # Generate checksum list for the files in USB
        bat_chk_dic = {}
        status, output = self.ssh_client.execute('ls {}'.format(KDP.MOUNT_PATH))
        self.usb_mount = output.split()[0]
        usb_path = '{0}{1}/'.format(KDP.MOUNT_PATH, self.usb_mount)
        status, usb_files = self.ssh_client.execute('find {0} -type f'.format(usb_path))
        lists = [path.split(usb_path).pop() for path in usb_files.split()]
        for item in lists:
            if any(char.isdigit() for char in item) and not item.startswith('.'):
                path = '{0}/{1}/{2}'.format(KDP.MOUNT_PATH, self.usb_mount, item)
                md5sum = None
                for idx in xrange(5):
                    md5sum = self.ssh_client.get_file_md5_checksum(path)
                    if md5sum:
                        break
                    else:
                        self.log.warning('Failed to get checksum, try again...')
                        time.sleep(5)
                        md5sum = self.ssh_client.get_file_md5_checksum(path)
                bat_chk_dic.update({item: md5sum})

        user_id = self.uut_owner.get_user_id(escape=True)
        copy_id, usb_info, resp = self.uut_owner.usb_slurp()
        usb_name = usb_info.get('name').replace(' ', '\ ')
        if self.ssh_client.check_is_kdp_device():
            user_roots_path = KDP.USER_ROOT_PATH
        else:
            user_roots_path = RnD.USER_ROOT_PATH

        PASSED = 0
        FAILED = 0
        for key, value in bat_chk_dic.iteritems():
            path = os.path.join(user_roots_path, user_id, usb_name, key)
            sync_chksum = self.ssh_client.get_file_md5_checksum(path)
            source_chksum = bat_chk_dic[key]
            self.log.info('{} - sync_chksum:{}, source_chksum:{}'.format(key, sync_chksum, source_chksum))
            if sync_chksum == source_chksum:
                PASSED += 1
            else:
                self.log.error('Compare failed!!')
                FAILED += 1
        if FAILED > 0:
            raise self.err.TestFailure('USB Slurp Backup Compare FAILED!! PASSED_FILES: {0}, FAILED_FILES: {1}'.
                                       format(PASSED, FAILED))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Check USB Slurp Backup Test Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/usb_slurp_backup_file.py --uut_ip 10.92.224.68\
        """)

    test = UsbSlurpBackupFile(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
