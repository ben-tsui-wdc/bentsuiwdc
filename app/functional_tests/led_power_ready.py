# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings


class LEDCheckPowerUp(TestCase):

    TEST_SUITE = "Led Test"
    TEST_NAME = "Led Check Power Up Test"
    # Popcorn
    TEST_JIRA_ID = 'KAM-7871'

    def init(self):
        self.led_power_ready = ''
        self.sys_power_ready = ''

    def test(self):
        self.log.info("Execute Power Cycle on test device")
        self.power_switch.power_cycle(self.env.power_switch_port, cycle_time=10)

        self.log.info('Wait 10 seconds and then check if boot complete')
        time.sleep(10)

        if self.uut.get('model') in ('yodaplus', 'yoda'):
            self.serial_client.wait_for_boot_complete()

        self.log.info('Wait for device boot completed...')
        if not self.adb.wait_for_device_boot_completed(max_retries=3):
            raise self.err.TestFailure('Device seems down, device boot not completed')

        self.log.info('Wait for 30 seconds to check LedServer messages because sometimes "Power up" and "Full Solid" will delay in Pelican.')
        time.sleep(30)

        led_list = self.adb.get_led_logs()
        self.adb.print_led_info(led_list)

        for i, led_info in enumerate(led_list):
            if self.uut.get('model') in ('yodaplus', 'yoda'):
                if all([led_info.get('type') == 'SYS',
                        led_info.get('before') == 'Power up',
                        led_info.get('after') == 'BLE Started']):
                    self.sys_power_ready = True
                elif all([led_info.get('type') == 'SYS',
                          led_info.get('after') == 'BLE Started']):
                    # When yoda connect wi-fi slower than we expected
                    self.sys_power_ready = True
                elif all([led_info.get('type') == 'LED',
                          led_info.get('before') == 'Slow Breathing',
                          led_info.get('after') == 'Full Solid']):
                    # http://jira.wdmv.wdc.com/browse/KAM200-3948
                    self.led_power_ready = True
                elif all([led_info.get('type') == 'LED',
                          led_info.get('before') == 'Fast Breathing',
                          led_info.get('after') == 'Full Solid']):
                    # When yoda connect wi-fi slower than we expected
                    # That means DUT doesn't connect to cloud yet, causing PROXY error)
                    # At that time, LED will be "Fast Breathing".
                    self.led_power_ready = True
            else:
                if all([led_info.get('type') == 'SYS',
                        led_info.get('before') == 'Power up',
                        led_info.get('after') == 'Ready']):
                    self.sys_power_ready = True
                elif all([led_info.get('type') == 'LED',
                          led_info.get('before') == 'Slow Breathing',
                          led_info.get('after') == 'Full Solid']):
                    self.led_power_ready = True

    def after_test(self):
        if any([not self.sys_power_ready, not self.led_power_ready]):
            raise self.err.TestFailure('LED Check: Power Ready Failed! LED status is not correct.')

        data = self.uut_owner.get_device_info()
        flag = data.get('cloudConnected')
        if not flag:
            raise self.err.TestFailure('LED Check: Power Ready Failed! Check cloudConnected failed!')

if __name__ == '__main__':
    parser = InputArgumentParser("""
        *** LED Check: Power Ready on Kamino Android ***
        """)
    test = LEDCheckPowerUp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)