# -*- coding: utf-8 -*-
""" Test cases to check FTP Read/Write test.
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import os

# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.common_utils import execute_local_cmd
from platform_libraries.common_utils import delete_local_file


class FTPRW(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Basic FTP Read Write Test'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1481'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.ftp_user = "admin"
        self.ftp_password = "adminadmin"
        self.skip_enable_service = False
        self.disable_share_ftp = False
        self.share_folder = 'Public'

    def init(self):
        self.time_out = 60*5
        self.share_location = 'ftp://{}/{}/'.format(self.env.ssh_ip, self.share_folder)
        self.count = 50
        self.filename = 'test{}MB'.format(self.count)

    def before_test(self):
        if not self.skip_enable_service:
            self.ssh_client.enable_ftp_service()
        if self.disable_share_ftp:
            self.ssh_client.disable_share_ftp(share_name=self.share_folder)
        else:
            self.ssh_client.enable_share_ftp(share_name=self.share_folder)

    def test(self):
        self.log.info("Step 1: Create a dummy test file: {}".format(self.filename))
        execute_local_cmd('dd if=/dev/urandom of={0} bs=1M count={1}'.format(self.filename, self.count))

        self.log.info("Step 2: Start the Write test")
        execute_local_cmd('curl -u {0}:{1} -T {2} {3} --connect-timeout 180 -m {4}'.format(
            self.ftp_user, self.ftp_password, self.filename, self.share_location, self.time_out), timeout=self.time_out)
        if not self.ssh_client.check_file_in_device('/shares/Public/{}'.format(self.filename)):
            raise self.err.TestFailure('Upload file failed!')

        self.log.info("Step 3: Compare the md5 checksum")
        local_md5 = execute_local_cmd('md5sum {0}'.format(self.filename))[0]
        device_md5 = self.ssh_client.execute_cmd('md5sum {0}/{1}'.format('/shares/Public', self.filename))[0]
        if not local_md5.split()[0] == device_md5.split()[0]:
            raise self.err.TestFailure('Basic FTP Write Test Failed! Error: md5 checksum not match!')

        self.log.info("Step 4: Start the Read test")
        execute_local_cmd('curl -u {0}:{1} {2}{3} -o {4}_clone'.format(
            self.ftp_user, self.ftp_password, self.share_location, self.filename, self.filename), timeout=self.time_out)
        if not os.path.isfile('./{}_clone'.format(self.filename)):
            raise self.err.TestFailure('Download file failed!')

        self.log.info("Step 5: Compare the md5 checksum")
        local_clone_md5 = execute_local_cmd('md5sum {0}_clone'.format(self.filename))[0]
        if not local_md5.split()[0] == local_clone_md5.split()[0]:
            raise self.err.TestFailure('Basic Samba Read Test Failed! Error: md5 checksum not match!')

    def after_test(self):
        self.log.info("Clean local test files")
        delete_local_file(self.filename)
        delete_local_file("{}_clone".format(self.filename))
        self.log.info("Clean device test files")
        self.ssh_client.delete_file_in_device('/shares/Public/{}'.format(self.filename))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** FTP Read/Write Check Script ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/ftp_rw_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    # Test Arguments
    parser.add_argument('--ftp_user', help='Samba login user name', default="admin")
    parser.add_argument('--ftp_password', help='Samba login password', default="adminadmin")
    parser.add_argument('--skip_enable_service', help='do not enable the service before testing', action='store_true')
    parser.add_argument('--disable_share_ftp', help='disable the ftp function in share folder for negative tests', action='store_true')
    parser.add_argument('--share_folder', help='The test share folder name', default="Public")

    test = FTPRW(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
