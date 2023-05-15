# -*- coding: utf-8 -*-
""" Case to confirm that the max log rotate number is 7
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckMaxRotateLogNumber(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-1110 - Verify the maximum number of rotated logs'
    TEST_JIRA_ID = 'KDP-1110'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.ramdisk_log_path = '/var/log/'
        self.test_log_file = '/var/log/analyticpublic.log'
        self.max_log_number = 7
        self.log_facility_number = 5  # analyticpublic.log

    def before_test(self):
        self.log.info("Trigger log force rotate and force upload to make sure no log file exist")
        self.ssh_client.log_rotate_kdp(force=True)
        self.ssh_client.log_upload_kdp()
        self.log.info("Stop LogPP tepporarily to prevent log upload by schedule")
        self.ssh_client.stop_logpp()

    def test(self):
        self.log.info("*** Step 1: Check there are no rotated file in {}".format(self.ramdisk_log_path))
        if self.ssh_client.check_file_in_device("{}.1".format(self.test_log_file)):
            raise self.err.TestFailure('The rotated file was not cleaned up after log upload!')

        self.log.info("*** Step 2: Generate logs and run force log rotate for {}+1 times".format(self.max_log_number))
        for i in range(self.max_log_number+1):
            self.ssh_client.generate_logs(log_number=self.log_facility_number, log_type="INFO",
                                          log_messages="dummy_test_logs_{}".format(i+1))
            self.ssh_client.log_rotate_kdp(force=True)
            if i == self.max_log_number:
                # suffix with max_log_number + 1 should not exist
                if self.ssh_client.check_file_in_device("{0}.{1}".format(self.test_log_file, self.max_log_number + 1)):
                    raise self.err.TestFailure('Rotate log {0}.{1} should not exist!'.
                                               format(self.test_log_file, self.max_log_number + 1))
            else:
                if not self.ssh_client.check_file_in_device("{0}.{1}".format(self.test_log_file, i+1)):
                    raise self.err.TestFailure('Cannot find rotated log {0}.{1}!'.format(self.test_log_file, i+1))

    def after_test(self):
        self.ssh_client.start_logpp()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_max_rotate_log_number.py --uut_ip 10.92.224.68\
        """)

    test = CheckMaxRotateLogNumber(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
