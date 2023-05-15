# -*- coding: utf-8 -*-
""" Test cases to check KAM-8767: [LED] Device reset.
"""
__author__ = "Fish Chiang <fish.chiang@wdc.com>"

# std modules
import sys
import time
import argparse

# platform modules
from pprint import pformat
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from bat_scripts_new.factory_reset import FactoryReset

class LEDDeviceReset(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = '[LED] Device reset'
    # Popcorn
    TEST_JIRA_ID = 'KAM-8767'

    SETTINGS = {
        'uut_owner': False
    }

    start = time.time()

    def init(self):
        self.timeout = 60*10

    def test(self):
        self.check_device_bootup()
        self.log.info('Reset button press 35 ses ...')
        self.adb.executeShellCommand('reset_button.sh short_start')
        time.sleep(30)
        self.adb.executeShellCommand('reset_button.sh middle_start')
        time.sleep(5)
        # Change to (Demote User)
        self.adb.executeShellCommand('reset_button.sh long')
        sys_dict = self.search_event(event_type='SYS', event_before= 'Reset Button Short', event_after='Reset Button Middle')
        if not sys_dict:
            raise self.err.TestFailure('LED state not change, failed the cases!!')
        self.check_led_state()
        self.factory_reset()

    def check_led_state(self):
        # Expected Result: LED 100% light and slow "breathing"
        # For Yoda/Yoda+ : LED will fast breathing to inform user 30s is up, then turn to solid at 36s.
        # Once you release reset button DUT will start device reset and slow breathing.
        led_dict = self.search_event(event_type='LED', event_before= 'Fast Breathing', event_after='Slow Breathing')
        if not led_dict:
            self.log.error('LED not Slow Breathing.')
            raise self.err.TestFailure('LED not Slow Breathing.')

    def search_event(self, event_type=None, event_before=None, event_after=None):
        count = 0
        dict_list = []
        self.led_list = self.adb.get_led_logs()
        for item in self.led_list:
            if event_type and event_before and event_after:
                if item.get('type')==event_type and item.get('before')==event_before and item.get('after')==event_after:
                    dict_list.append(item)
                    count+=1
            elif event_type and event_after:
                if item.get('type')==event_type and item.get('after')==event_after:
                    dict_list.append(item)
                    count+=1
        if count == 0:
            return None
        elif count > 0:
            if count > 1:
                self.log.warning('The LedServer item occurred many times({})! [type] {} [before] {} [after] {}'.format(count, event_type, event_before, event_after))
                self.log.warning('{}'.format(dict_list))
            return dict_list[0]

    def check_device_bootup(self):
        # check device boot up
        while not self.is_timeout(self.timeout):
            if self.adb.check_platform_bootable():
                self.log.info('Boot completed')
                break
            time.sleep(5)

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

    def factory_reset(self):
        self.log.info('Start to do factory reset ...')
        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=False']
        factory_reset = FactoryReset(env_dict)
        factory_reset.no_rest_api = True
        factory_reset.disable_ota = False
        factory_reset.test()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** [LED] YODA - Factory reset Check Script ***
        Examples: ./run.sh functional_tests/led_device_reset.py --cloud_env qa1 --serial_server_ip 10.0.0.6 --serial_server_port 20000\
        """)

    test = LEDDeviceReset(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
