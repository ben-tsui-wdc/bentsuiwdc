# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings


class LEDCheckBootSequence(TestCase):

    TEST_SUITE = "Led Test"
    TEST_NAME = "Led Boot Sequence Test"
    # Popcorn
    TEST_JIRA_ID = 'KAM-21779'

    SETTINGS = Settings(**{
        'uut_owner': False
    })

    '''
        Only run for yoda/yoda+
    '''
    def init(self):
        self.led_boot_sequence = ''
        self.sys_boot_sequence = ''

    def test(self):
        led_list = self.adb.get_led_logs()
        self.adb.print_led_info(led_list)

        for i, led_info in enumerate(led_list):
            if all([led_info.get('type') == 'SYS',
                    led_info.get('before') == 'Power up',
                    led_info.get('after') == 'BLE Started']):
                self.sys_boot_sequence = True
            elif all([led_info.get('type') == 'SYS',
                      led_info.get('after') == 'BLE Started']):
                # When yoda connect wi-fi slower than we expected
                self.sys_boot_sequence = True
            elif all([led_info.get('type') == 'LED',
                      led_info.get('before') == 'Slow Breathing',
                      led_info.get('after') == 'Full Solid']):
                #  http://jira.wdmv.wdc.com/browse/KAM200-3948
                self.led_boot_sequence = True
            elif all([led_info.get('type') == 'LED',
                      led_info.get('before') == 'Fast Breathing',
                      led_info.get('after') == 'Full Solid']):
                # When yoda connect wi-fi slower than we expected
                # That means DUT doesn't connect to cloud yet, causing PROXY error)
                # At that time, LED will be "Fast Breathing".
                self.led_boot_sequence = True

    def after_test(self):
        if any([not self.sys_boot_sequence, not self.led_boot_sequence]):
            raise self.err.TestFailure('LED Check: Boot Sequence Failed!')

if __name__ == '__main__':
    parser = InputArgumentParser("""
        *** LED Check: Boot sequence on Kamino Android ***
        """)
    test = LEDCheckBootSequence(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)