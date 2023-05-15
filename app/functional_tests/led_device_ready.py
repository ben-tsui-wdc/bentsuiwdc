# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings


class LEDCheckDeviceReady(TestCase):

    TEST_SUITE = "Led Test"
    TEST_NAME = "Led Device Ready Test"
    # Popcorn
    TEST_JIRA_ID = 'KAM-23590'

    SETTINGS = Settings(**{
        'uut_owner': False
    })

    def init(self):
        self.led_device_ready = ''
        self.sys_device_ready = ''


    def test(self):

        led_list = self.adb.get_led_logs()
        self.adb.print_led_info(led_list)

        for i, led_info in enumerate(led_list):
            if self.uut.get('model') in ('yodaplus', 'yoda'):
                if all([led_info.get('type') == 'SYS',
                        led_info.get('before') == 'Power up',
                        led_info.get('after') == 'BLE Started']):
                    self.sys_device_ready = True
                elif all([led_info.get('type') == 'SYS',
                        led_info.get('after') == 'BLE Started']):
                    # When yoda connect wi-fi slower than we expected
                    self.sys_device_ready = True

                elif all([led_info.get('type') == 'LED',
                          led_info.get('before') == 'Slow Breathing',
                          led_info.get('after') == 'Full Solid']):
                    # http://jira.wdmv.wdc.com/browse/KAM200-3948
                    self.led_device_ready = True
                elif all([led_info.get('type') == 'LED',
                          led_info.get('before') == 'Fast Breathing',
                          led_info.get('after') == 'Full Solid']):
                    # When yoda connect wi-fi slower than we expected
                    # That means DUT doesn't connect to cloud yet, causing PROXY error)
                    # At that time, LED will be "Fast Breathing".
                    self.led_device_ready = True
            else:
                if all([led_info.get('type') == 'SYS',
                        led_info.get('before') == 'Power up',
                        led_info.get('after') == 'Ready']):
                    self.sys_device_ready = True
                elif all([led_info.get('type') == 'SYS',
                        led_info.get('before') == 'Power up',
                        led_info.get('after') == 'Ready']):
                    self.sys_device_ready = True
                elif all([led_info.get('type') == 'LED',
                          led_info.get('before') == 'Slow Breathing',
                          led_info.get('after') == 'Full Solid']):
                    self.led_device_ready = True

    def after_test(self):
        if any([not self.sys_device_ready, not self.led_device_ready]):
            raise self.err.TestFailure('LED Check: Device Ready Failed!')

if __name__ == '__main__':
    parser = InputArgumentParser("""
        *** LED Check: Device Ready on Kamino Android ***
        """)
    test = LEDCheckDeviceReady(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)