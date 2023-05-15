# -*- coding: utf-8 -*-
""" Test case to check log without Java exception on boot (KAM-21404).
"""
__author__ = "Edison Chou <edison.chou@wdc.com>"

# std modules
import sys
import time
import os

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class LogWithoutJavaExceptionOnBoot(TestCase):

    TEST_SUITE = 'Functional Tests'
    TEST_NAME = 'Log Without Java Exception On Boot'
    # Popcorn
    TEST_JIRA_ID = 'KAM-21404'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        #do reboot
        self.timeout = 3600
        self.adb.executeShellCommand('busybox nohup reboot')
        self.adb.disconnect()

        self.start_time = time.time()
        while self.adb.is_device_pingable():
            self.log.info('Waiting device power off ...')
            time.sleep(2)
            if time.time() - self.start_time >= 600:
                raise self.err.TestError('Device failed to power off within {} seconds'.format(600))
        time.sleep(15)

        self.start_time = time.time()
        while not self.adb.is_device_pingable():
            self.log.info('Waiting device boot up ...')
            time.sleep(5)
            if time.time() - self.start_time > 600:
                raise self.err.TestError('Timeout waiting to boot within {} seconds'.format(600))

        self.start_time = time.time()
        while (self.timeout > time.time() - self.start_time):
            if self.adb.check_adb_connectable():
                break
            time.sleep(5)
        time.sleep(30)

        log_without_java_exception_on_boot = self.adb.executeShellCommand("logcat -d | grep -E 'java.lang.RuntimeException'")[0]
        if log_without_java_exception_on_boot == "":
            self.log.info('Log Without Java Exception On Boot Check: PASSED.')
        else:
            self.log.error('Log Without Java Exception On Boot Check: FAILED.')
            raise self.err.TestFailure('Log Without Java Exception On Boot Check Failed')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Log Without Java Exception On Boot Script ***
        Examples: ./run.sh functional_tests/reboot_device.py --uut_ip 192.168.11.100 -dcll
        """)

    test = LogWithoutJavaExceptionOnBoot(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
