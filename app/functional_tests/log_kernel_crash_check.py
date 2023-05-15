# -*- coding: utf-8 -*-
""" Test cases for KAM-23481
    Platform store pstore- kernel crash log
    From Bing:  Implemented the automation test code. 
                Because the message is shown a very short time, can't get the 100% verification success in the automation test. 
                Ssuggest marking this ticket as Non-automatable.
"""
__author__ = "Fish Chiang <fish.chiang@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase

class LogKernelCrashCheck(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Log kernel crash Check'
    # Popcorn
    TEST_JIRA_ID = 'KAM-23481'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        self.serial_client.serial_write('echo c > /proc/sysrq-trigger')
        self.log.info('Expect device do rebooting ...')
        time.sleep(20)
        self.adb.connect()
        time.sleep(2)
        result = self.adb.executeShellCommand('ls /sys/fs/pstore', timeout=10)[0]
        if 'console-ramoops-0' not in result:
            raise self.err.TestFailure('Log kernel crash Check: Failed, console-ramoops-0 not exist.')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Kernel crash log Check Script ***
        Examples: ./run.sh functional_tests/log_kernel_crash_check.py --uut_ip 10.92.224.68 -dcll\
        """)

    test = LogKernelCrashCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
