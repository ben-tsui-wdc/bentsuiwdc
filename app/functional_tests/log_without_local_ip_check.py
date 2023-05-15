# -*- coding: utf-8 -*-
""" Test cases to check log without local ip information [KAM-21400]
"""
__author__ = "Andrew Tsai <andrew.tsai@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class LogWithoutLocalIPCheck(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Log Without Local IP Check'
    # Popcorn
    TEST_JIRA_ID = 'KAM-21400'


    def test(self):
        # do reboot
        self.timeout = 60*5
        self.uut_owner.reboot_device()
        # Wait for reboot.
        self.log.info('Expect device do reboot in {} secs...'.format(self.timeout))
        if not self.adb.wait_for_device_to_shutdown(timeout=self.timeout):
            self.log.error('Reboot device: FAILED.')
            raise self.err.TestFailure('Reboot device failed')
        # Wait for boot up.
        self.log.info('Wait for device boot completed...')
        if not self.adb.wait_for_device_boot_completed(timeout=self.timeout):
            self.log.error('Device seems down.')
            raise self.err.TestFailure('Device seems down, device boot not completed')
        self.log.info('Device reboot completed.')
        # check log message
        log_find_linkaddresses = self.adb.executeShellCommand("logcat -d | grep -E 'LinkAddresses'")[0]
        if log_find_linkaddresses == "":
            self.log.info('No any LinkAddresses info. Log Without Local IP Check: PASSED.')
        else:
            check_list = ['busybox sed', '/LinkAddresses/d']
            if not all(word in log_find_linkaddresses for word in check_list):
                self.log.error('LinkAddresses is not be deleted. Log Without Local IP Check: FAILED.')
                raise self.err.TestFailure('Log without local IP check failed')
            self.log.info('LinkAddresses is already be deleted. Log Without Local IP Check: PASSED.')
        
if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Log Without Local IP Check Script ***
        Examples: ./run.sh functional_tests/log_without_local_ip_check.py --uut_ip 10.92.224.68 -dcll\
        """)

    test = LogWithoutLocalIPCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
