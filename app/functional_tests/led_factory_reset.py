# -*- coding: utf-8 -*-
""" Test cases to check [LED] YODA - Factory reset.
"""
__author__ = "Ben Lin <ben.lin@wdc.com>"

# std modules
import sys
import time
import argparse

# platform modules
from pprint import pformat
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.serial_client import SerialClient
from bat_scripts_new.factory_reset import FactoryReset

class LEDFactoryReset(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = '[LED] YODA - Factory reset'
    # Popcorn
    TEST_JIRA_ID = 'KAM-24686'

    SETTINGS = {
        'uut_owner': False
    }

    start = time.time()

    def init(self):
        self.model = self.uut.get('model')

    def declare(self):
        self.timeout = 300

    def test(self):
        self.check_device_bootup()

        self.adb.executeShellCommand('reset_button.sh short_start')
        time.sleep(30)
        self.adb.executeShellCommand('reset_button.sh middle_start')
        time.sleep(5)
        self.adb.executeShellCommand('reset_button.sh long_start')
        time.sleep(25)
        if self.model == 'yoda' or self.model == 'yodaplus':
            sys_state_log = self.adb.executeShellCommand("logcat -d | grep  'sys state change'")[0]
            check_list = ['(Reset Button Short) -> (Reset Button Middle)', '(Reset Button Middle) -> (Reset Button Long)']
            if not all(word in sys_state_log for word in check_list):
                raise self.err.TestFailure('LED state not change, failed the cases!!')

        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=False']
        factory_reset = FactoryReset(env_dict)
        factory_reset.no_rest_api = True
        factory_reset.disable_ota = False
        factory_reset.test()

    def check_device_bootup(self):
        # check device boot up
        while not self.is_timeout(self.timeout):
            if self.adb.check_platform_bootable():
                self.log.info('Boot completed')
                break
            time.sleep(5)

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** [LED] YODA - Factory reset Check Script ***
        Examples: ./run.sh functional_tests/led_factory_reset.py --cloud_env qa1 --serial_server_ip 10.0.0.6 --serial_server_port 20000\
        """)

    test = LEDFactoryReset(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
