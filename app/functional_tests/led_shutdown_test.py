# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class LEDCheckShutdown(TestCase):

    TEST_SUITE = "Led Test"
    TEST_NAME = "Led Shutdown Test"
    # Popcorn
    TEST_JIRA_ID = 'KAM-8768'


    def init(self):
        self.led_shutdown = ''
        self.sys_shutdown = ''
        self.led_boot_complete = ''
        self.sys_boot_complete = ''

    def test(self):

        is_device_shutdown = self.uut_owner.shutdown_device()
        if not is_device_shutdown:
            self.log.error('Shutdown device: FAILED.')
            raise self.err.TestFailure('Shutdown device failed')
        led_list = self.adb.get_led_logs()
        self.adb.print_led_info(led_list)

        for led_info in led_list:
            if all([led_info.get('type') == 'LED',
                    led_info.get('before') == 'Full Solid',
                    led_info.get('after') == 'Slow Breathing']):
                self.led_shutdown = True
            elif all([led_info.get('type') == 'SYS',
                      led_info.get('before') == 'Ready',
                      led_info.get('after') == 'Power Button Pressed']):
                self.sys_shutdown = True

        if any([not self.led_shutdown, not self.sys_shutdown]):
            self.log.warning('Shutdown info cannot be found, need to check syslog.reboot')
        else:
            self.log.info('Get shutdown info successfully')

        '''
            I don't know why some Monarchs cannot be power up by power cycle. __Jason
        '''
        #self.log.info("Execute power cycle")
        #self.power_switch.power_cycle(self.env.power_switch_port)  

        self.log.info('Wait 15 secs to run power off by power switch')
        time.sleep(15)
        self.power_switch.power_off(self.env.power_switch_port)
        self.log.info("wait 30 seconds to power on by power switch")
        time.sleep(30)
        self.power_switch.power_on(self.env.power_switch_port)

        if not self.adb.wait_for_device_boot_completed(max_retries=3):
            self.log.error('Device seems down.')
            raise self.err.TestFailure('Device seems down, device boot not completed')

        self.log.info('Wait for 30 seconds to check LedServer messages because sometimes "Power up" and "Full Solid" will delay in Pelican.')
        time.sleep(30)

        led_list = self.adb.get_led_logs()
        self.adb.print_led_info(led_list)

        for led_info in led_list:
            if self.uut.get('model') in ('yodaplus', 'yoda'):
                if all([led_info.get('type') == 'SYS',
                        led_info.get('before') == 'Power up',
                        led_info.get('after') == 'BLE Started']):
                    self.sys_boot_complete = True
                elif all([led_info.get('type') == 'SYS',
                          led_info.get('after') == 'BLE Started']):
                    # When yoda connect wi-fi slower than we expected
                    self.sys_boot_complete = True
                elif all([led_info.get('type') == 'LED',
                          led_info.get('before') == 'Slow Breathing',
                          led_info.get('after') == 'Full Solid']):
                    # http://jira.wdmv.wdc.com/browse/KAM200-3948
                    self.led_boot_complete = True
                elif all([led_info.get('type') == 'LED',
                          led_info.get('before') == 'Fast Breathing',
                          led_info.get('after') == 'Full Solid']):
                    # When yoda connect wi-fi slower than we expected
                    # That means DUT doesn't connect to cloud yet, causing PROXY error)
                    # At that time, LED will be "Fast Breathing".
                    self.led_boot_complete = True
            else:
                if all([led_info.get('type') == 'LED',
                        led_info.get('before') == 'Slow Breathing',
                        led_info.get('after') == 'Full Solid']):
                    self.led_boot_complete = True
                elif all([led_info.get('type') == 'SYS',
                        led_info.get('before') == 'Power up',
                        led_info.get('after') == 'Ready']):
                    self.sys_boot_complete = True

    def after_test(self):
        if not self.led_boot_complete:
            raise self.err.TestFailure('logcat "LedServer" Check: "led change" message doesn\'t meet requirements !')
        if not self.sys_boot_complete:
            raise self.err.TestFailure('logcat "LedServer" Check: "sys change" message doesn\'t meet requirements !')



if __name__ == '__main__':
    parser = InputArgumentParser("""
        *** LED Check: Shutdown on Kamino Android ***
        """)
    test = LEDCheckShutdown(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)