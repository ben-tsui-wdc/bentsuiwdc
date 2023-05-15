# -*- coding: utf-8 -*-
""" Case to confirm that every 15 minutes (use script to simulate), logs will be rotated if file size > 400 KB
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import urllib2
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckNormalLogRotateNegative(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-1107 - [ANALYTICS] Logs will not be rotated every 15 mins when log file size <= 400KB'
    TEST_JIRA_ID = 'KDP-1107'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.ramdisk_log_path = '/var/log/'
        self.test_log_file = '/var/log/otaclient.log'

    def test(self):
        self.log.info("*** Step 1: Trigger log force rotate and force upload to make sure no log file exist")
        self.ssh_client.log_rotate_kdp(force=True)
        self.ssh_client.log_upload_kdp()
        if self.ssh_client.check_file_in_device("{}.1".format(self.test_log_file)):
            raise self.err.TestFailure('The rotated file was not cleaned up after log upload!')

        self.log.info("*** Step 2: Generate a fake log file with size less than 400 KB")
        # It will take too long if we generate real logs to reach 200 KB
        self.ssh_client.execute_cmd("dd if=/dev/zero of={} bs=1K count=200".format(self.test_log_file))
        log_file_size = int(self.ssh_client.execute_cmd("du {}".format(self.test_log_file))[0].split()[0].strip())
        self.log.info("log_file_size of {0}: {1} KB".format(self.test_log_file, log_file_size))
        if log_file_size >= 400:
            raise self.err.TestSkipped('Log file size should not more than 400 KB after generating fake logs!')

        self.log.info("*** Step 3: Trigger the normal log ratote and check the rotated log file")
        self.ssh_client.log_rotate_kdp(force=False)
        if not self.ssh_client.check_file_in_device("{}.1".format(self.test_log_file)):
            self.log.info("Logs are nott rotated when file size < 400 KB, test passed!")
        else:
            raise self.err.TestFailure('Logs should not be rotated when file size < 400 KB!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_normal_log_rotate_negative.py --uut_ip 10.92.224.68\
        """)

    test = CheckNormalLogRotateNegative(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
