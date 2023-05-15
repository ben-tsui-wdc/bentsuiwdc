# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import os
import shutil
import random

from multiprocessing import Process, Queue

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings


class LEDCheckUSBSlurp(TestCase):

    TEST_SUITE = "Led Test"
    TEST_NAME = "Led USB Slurp Test"
    # Popcorn
    TEST_JIRA_ID = 'KAM-23591'

    SETTINGS = Settings(**{
        'uut_owner': False
    })

    def init(self):
        self.usb_slurp_start_index = ''
        self.usb_slurp_finish_index = ''

    def test(self):
        led_list = self.adb.get_led_logs()
        self.adb.print_led_info(led_list)

        for i, led_info in enumerate(led_list):
            if all([led_info.get('type') == 'SYS',
                    led_info.get('before') == 'Ready',
                    led_info.get('after') == 'Data Transfer']):
                self.usb_slurp_start_index = i
            elif all([led_info.get('type') == 'SYS',
                      led_info.get('before') == 'Ready',
                      led_info.get('after') == 'Data Transfer Completed']):
                self.usb_slurp_finish_index = i

    def after_test(self):
        if any([self.usb_slurp_start_index == '',
                self.usb_slurp_finish_index == '',
                int(self.usb_slurp_finish_index) < int(self.usb_slurp_start_index)]):
            raise self.err.TestFailure('LED Check: USB Slurp Failed!')

if __name__ == '__main__':
    parser = InputArgumentParser("""
        *** LED Check: USB Slurp on Kamino Android ***
        """)
    test = LEDCheckUSBSlurp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)