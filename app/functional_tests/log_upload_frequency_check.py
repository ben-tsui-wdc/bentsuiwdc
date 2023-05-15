# -*- coding: utf-8 -*-
""" Test cases to check log upload frequency [KAM-21401]
"""
__author__ = "Andrew Tsai <andrew.tsai@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class LogUploadFrequencyCheck(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Log Upload Frequency Check'
    # Popcorn
    TEST_JIRA_ID = 'KAM-21401'

    SETTINGS = {
        'uut_owner': False
    }


    def test(self):
        self.retry = 1
        self.MAX_RETRIES = 5

        while self.retry <= self.MAX_RETRIES:
            self.adb.executeShellCommand("logcat -c")
            self.adb.executeShellCommand("move_upload_logs.sh -a")
            self.adb.executeShellCommand("move_upload_logs.sh -n")
            log_upload_frequency, stderr = self.adb.executeShellCommand("logcat -d | grep -E 'LogUploader.*Device log upload cadence'")
            if log_upload_frequency == "":
                self.log.warning("Log Upload Frequency Check: Log message is empty, remaining {} retries".format(self.retry))
                self.retry += 1
                time.sleep(10)
            else:
                break

        if log_upload_frequency == "":
            raise self.err.TestFailure('Log upload frequency check failed, Log message is empty')
        else:
            if 'hour' not in log_upload_frequency:
                raise self.err.TestFailure('Log upload frequency is not 1 hour.')
            self.log.info('Log Upload Frequency Check: PASSED.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Log Upload Frequency Check Script ***
        Examples: ./run.sh functional_tests/log_upload_frequency_check.py --uut_ip 10.92.224.68 -dcll\
        """)

    test = LogUploadFrequencyCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
