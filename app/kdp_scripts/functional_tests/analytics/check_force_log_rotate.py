# -*- coding: utf-8 -*-
""" Case to confirm that every 60 minutes (use script to simulate), logs will be force rotated if file size > 0 KB
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckForceLogRotate(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-1108 - [ANALYTICS] Logs will be force rotated hourly if the log file size > 0 KB'
    TEST_JIRA_ID = 'KDP-1108'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.ramdisk_log_path = '/var/log/'
        self.test_log_file = '/var/log/otaclient.log'
        self.log_messages = 3

    def test(self):
        self.log.info("*** Step 1: Trigger log force rotate and force upload to make sure no log file exist")
        self.ssh_client.log_rotate_kdp(force=True)
        self.ssh_client.log_upload_kdp()
        if self.ssh_client.check_file_in_device("{}.1".format(self.test_log_file)):
            raise self.err.TestFailure('The rotated file was not cleaned up after log upload!')

        self.log.info("*** Step 2: Generate some logs and make sure log file size is > 0")
        for i in range(self.log_messages):
            self.ssh_client.generate_logs(log_number=7, log_type="INFO", log_messages="dummy_test_logs_{}".format(i))

        log_file_size = int(self.ssh_client.execute_cmd("du {}".format(self.test_log_file))[0].split()[0].strip())
        self.log.info("log_file_size of {0}: {1} KB".format(self.test_log_file, log_file_size))
        if log_file_size <= 0:
            raise self.err.TestFailure('Log file size should not less than 0 after generating log messages!')

        self.log.info("*** Step 3: Trigger the force log ratote and check the rotated log file")
        self.ssh_client.log_rotate_kdp(force=True)
        if self.ssh_client.check_file_in_device("{}.1".format(self.test_log_file)):
            self.log.info("Logs are rorated when file size > 0 KB, test passed!")
        else:
            raise self.err.TestFailure('Logs should not be rotated when file size > 0 KB!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_force_log_rotate.py --uut_ip 10.92.224.68\
        """)

    test = CheckForceLogRotate(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
