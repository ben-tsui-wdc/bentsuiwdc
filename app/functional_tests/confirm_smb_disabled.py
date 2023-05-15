# -*- coding: utf-8 -*-
""" Test cases to check Confirm SMB protocol has been disabled.
"""
__author__ = "Vodka Chen <vodka.chen@wdc.com>"

# std modules
import sys
import time
import argparse

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.ssh_client import SSHClient


class ConfirmSMBDisabled(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Confirm SMB protocol has been disabled'
    # Popcorn
    TEST_JIRA_ID = 'KAM-23480'

    SETTINGS = {
        'uut_owner': False
    }

    start = time.time()

    def declare(self):
        self.timeout = 300
        self.test_protocol = 'smb'

    def test(self):
        self.check_device_bootup()

        # check if smb can be mounted.
        dst_folder = '/Volumes/functional_test_{}_{}'.format(self.uut.get('model'), int(time.time()))
        mac_ssh = SSHClient(self.mac_server_ip, self.mac_username, self.mac_password)
        mac_ssh.connect()
        mac_ssh.unmount_folder(dst_folder, force=True)
        mac_ssh.create_folder(dst_folder)
        mac_ssh.mount_folder(self.test_protocol, self.env.uut_ip, 'TimeMachineBackup', dst_folder)
        if mac_ssh.check_folder_mounted('{}/TimeMachineBackup'.format(self.env.uut_ip), dst_folder=dst_folder, protocol=self.test_protocol):
            mac_ssh.unmount_folder(dst_folder, force=True)
            mac_ssh.delete_folder(dst_folder)
            raise self.err.TestFailure('{} mount successed on {}'.format(self.test_protocol, self.uut.get('model')))
        else:
            pass
        mac_ssh.close()

        # check smbd
        stdout, stderr = self.adb.executeShellCommand('ps | grep smbd')
        if not stdout:
            pass
        else:
            raise self.err.TestFailure('smbd process is running on {}.\n{}'.format(self.uut.get('model'), stdout))

    def check_device_bootup(self):
        # check device boot up
        while not self.is_timeout(self.timeout):
            boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed', timeout=10)[0]
            if '1' in boot_completed:
                self.log.info('Boot completed')
                break
            time.sleep(2)

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Confirm SMB protocol has been disabled Check Script ***
        Examples: ./run.sh functional_tests/confirm_smb_disabled.py --uut_ip 10.92.224.68\
        """)

    parser.add_argument('--mac_server_ip', help='mac_server_ip which is used to be as client.' , default='10.92.224.28')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='root')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac clientt', default='`1q')

    test = ConfirmSMBDisabled(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
