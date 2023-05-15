# -*- coding: utf-8 -*-

__author1__ = "Ben Tsui <ben.tsui@wdc.com>"
__author2__ = "Jason Chiang <jason.chiang@wdc.com>"
__compatible__ = 'KDP,RnD'

# std modules
import sys
import time


# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.bat_scripts.usb_slurp_backup_file import UsbSlurpBackupFile


class LEDCheckUSBSlurp(UsbSlurpBackupFile):

    TEST_SUITE = "Led Test"
    TEST_NAME = "KDP-901 - [LED] Data transfer via USB Slurp"
    # Popcorn
    TEST_JIRA_ID = 'KDP-901'


    def init(self):
        self.usb_slurp_start_index = ''
        self.usb_slurp_finish_index = ''


    def before_test(self):
        #stdout, stderr = self.ssh_client.execute_cmd('rm -r /var/log/analyticpublic.log*')
        super(LEDCheckUSBSlurp, self).test()


    def test(self):
        self.log.info('Wait for 5 seconds to check LedServer messages because sometimes "Power up" and "Full Solid" will delay.')
        time.sleep(5)
        led_list = self.ssh_client.get_led_logs(cmd='cat /var/log/analyticpublic.log  | grep led_ctrl_server')
        self.ssh_client.print_led_info(led_list)
        if self.uut['model'] in ['rocket', 'drax']:
            self.led_state_change = False
            self.sys_state_change = False
            if all([led_list[-2].get('type') == 'LED',
                led_list[-2].get('before') == 'Slow Breathing',
                led_list[-2].get('after') == 'Full Solid']):
                self.led_state_change = True
            if all([led_list[-1].get('type') == 'SYS',
                          led_list[-1].get('before') == 'Data Transfer',
                          led_list[-1].get('after') == 'Data Transfer Completed']):
                self.sys_state_change = True
            if not self.led_state_change:
                raise self.err.TestFailure('The LED change is not "Full Solid"!')
            if not self.sys_state_change:
                raise self.err.TestFailure('The SYS change is not "Data Transfer Completed"!')
        elif self.uut['model'] in ['monarch2', 'pelican2']:
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
        if self.uut['model'] in ['rocket', 'drax']:
            pass
        else:
            if any([self.usb_slurp_start_index == '',
                    self.usb_slurp_finish_index == '',
                    int(self.usb_slurp_finish_index) < int(self.usb_slurp_start_index)]):
                raise self.err.TestFailure('LED Check: USB Slurp Failed!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""
        *** LED Check: USB Slurp on Kamino Android ***
        """)
    test = LEDCheckUSBSlurp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)