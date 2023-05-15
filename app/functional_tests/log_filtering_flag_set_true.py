# -*- coding: utf-8 -*-
""" Test cases to check log filtering flag set true [KAM-18068]
"""
__author__ = "Andrew Tsai <andrew.tsai@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class LogFilteringFlagSetTrue(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Log Filtering Flag Set True'
    # Popcorn
    TEST_JIRA_ID = 'KAM-18068'

    SETTINGS = {
        'uut_owner': False
    }

    start = time.time()

    def declare(self):
        self.timeout = 300

    def test(self):
        # Check device boot up
        self.check_device_bootup()
        # Verify wd.log.filtering flag
        log_filtering_flag = self.adb.executeShellCommand("getprop | grep -E 'wd.log.filtering'")[0]
        build_type = self.adb.executeShellCommand("getprop | grep -E 'build.type'")[0]
        # wd.log.filtering flag is set to true in user build
        if '[user]' in build_type:
            if log_filtering_flag == "":
                self.log.error('No any log filtering flag. Log Filtering Flag Set True: FAILED.')
                raise self.err.TestFailure('Log filtering flag set true failed')
            else:
                if 'true' not in log_filtering_flag:
                    self.log.error('Log Filtering Flag Set True: FAILED.')
                    raise self.err.TestFailure('Log filtering flag set true failed')
                self.log.info('Log Filtering Flag Set True: PASSED.')
        # wd.log.filtering flag is set to false in userdebug build
        elif '[userdebug]' in build_type:
            if log_filtering_flag == "":
                self.log.error('No any log filtering flag. Log Filtering Flag Set True: FAILED.')
                raise self.err.TestFailure('Log filtering flag set true failed')
            else:
                if 'false' not in log_filtering_flag:
                    self.log.error('Log Filtering Flag Set True: FAILED.')
                    raise self.err.TestFailure('Log filtering flag set true failed')
                self.log.info('Log Filtering Flag Set True: PASSED.')

    def check_device_bootup(self):
        while not self.is_timeout(self.timeout):
            boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed', timeout=10)[0]
            if '1' in boot_completed:
                self.log.info('Boot completed')
                break
            time.sleep(5)

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Log Filtering Flag Set True Script ***
        Examples: ./run.sh functional_tests/log_filtering_flag_set_true.py --uut_ip 10.92.224.68\
        """)

    test = LogFilteringFlagSetTrue(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
