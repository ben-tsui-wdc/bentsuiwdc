# -*- coding: utf-8 -*-
""" Case to confirm that every 60 minutes (use script to simulate), logs will be force rotated if file size > 0 KB
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckForceLogRotateNegative(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-1109 - [ANALYTICS] Logs will not be force rotated hourly if the log size = 0 KB'
    TEST_JIRA_ID = 'KDP-1109'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.ramdisk_log_path = '/var/log/'
        self.test_log_file = '/var/log/appMgr.log'
        self.max_retries = 3

    def test(self):
        self.log.info("*** Step 1: Trigger log force rotate and upload to make sure the log file size of {} is 0 KB".
                      format(self.test_log_file))
        self.ssh_client.log_rotate_kdp(force=True)
        self.ssh_client.log_upload_kdp()
        if self.ssh_client.check_file_in_device("{}.1".format(self.test_log_file)):
            raise self.err.TestFailure('The rotated file was not cleaned up after log upload!')

        for i in range(self.max_retries):
            log_file_size = int(self.ssh_client.execute_cmd("du {}".format(self.test_log_file))[0].split()[0].strip())
            if log_file_size != 0:
                self.log.warning("The log size was not 0 KB, try to rotate and upload again! {} retries remaining...".
                                 format(self.max_retries - i))
                self.ssh_client.log_rotate_kdp(force=True)
                self.ssh_client.log_upload_kdp()
                if self.ssh_client.check_file_in_device("{}.1".format(self.test_log_file)):
                    raise self.err.TestFailure('The rotated file was not cleaned up after log upload!')
            else:
                self.log.info("log_file_size of {0}: {1} KB".format(self.test_log_file, log_file_size))
                break
        else:
            raise self.err.TestFailure('The log size of {} was not changed to 0 KB after {} times retries!'.
                                       format(self.test_log_file, self.max_retries))

        self.log.info("*** Step 2: Run log rotate immediately, log should not be force rotated when log size = 0")
        self.ssh_client.log_rotate_kdp(force=True)
        if self.ssh_client.check_file_in_device("{}.1".format(self.test_log_file)):
            raise self.err.TestFailure('Logs should not be rotated when file size = 0 KB!')
        else:
            self.log.info("Logs are not rotated when file size = 0 KB, test passed!")


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_force_log_rotate_negative.py --uut_ip 10.92.224.68\
        """)

    test = CheckForceLogRotateNegative(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
