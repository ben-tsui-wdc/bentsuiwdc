# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class LEDYodaPowerup(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-888 - LED_Yoda_Powerup_Initializing'
    SETTINGS = {'uut_owner':False}
    # Popcorn
    TEST_JIRA_ID = 'KDP-888'

    def declare(self):
        self.timeout = 300

    
    def init(self):
        if 'yoda' not in self.uut.get('model'):
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(self.uut.get('model')))

    def before_test(self):
        self.ssh_client.clean_device_logs()
        self.reboot_device()


    def test(self):
        self.log.info('Wait for 60 seconds to check LedServer messages because sometimes "Power up" or "Full Solid" will delay.')
        time.sleep(90)
        self.led_list = self.ssh_client.get_led_logs(cmd='cat /var/log/analyticpublic.log*  | grep led_ctrl_server | sort')
        self.ssh_client.print_led_info(self.led_list)
        if not self.led_list:
            raise self.err.StopTest('There is no LED info in logcat!')
        start_time = time.time()
        while all([not self.search_event(event_type='SYS', event_after='Wifi Connected'), not self.search_event(event_type='SYS', event_after='Proxy Connected')]):
            self.led_list = self.ssh_client.get_led_logs(command='cat /var/log/analyticpublic.log*  | grep led_ctrl_server | sort')
            time.sleep(3)
            if time.time() - start_time > 180:
                raise self.err.TestFailure("After 180 seconds, wifi still doesn't reconnect after device finished reboot!")
        self.full_solid_check()


    def search_event(self, event_type=None, event_before=None, event_after=None):
        count = 0
        dict_list = []
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


    def full_solid_check(self):
        sys_dict = self.search_event(event_type='SYS', event_before='Power up', event_after='BLE Started')
        led_dict = self.search_event(event_type='LED', event_before='Fast Breathing', event_after='Full Solid')
        if sys_dict and led_dict:
            self.log.warning('index(Power up -> BLE Started):{}'.format(self.led_list.index(sys_dict)))
            self.log.warning('index(Fast Breathing -> Full Solid):{}'.format(self.led_list.index(led_dict)))
            if self.led_list.index(led_dict) - self.led_list.index(sys_dict) > 0:  # 10 is just an approximate number.
                pass
            else:
                raise self.err.TestFailure('LED is not from Fast Breathing to Full Solid while rebooting.')
        else:  # Beacuse sometimes Yoda will have different LED event sequence
            #sys_dict = self.search_event(event_type='SYS', event_before='Ready', event_after='BLE Started')
            self.log.warning("The sys_dict or led_dict doesn't show.")
            sys_dict = self.search_event(event_type='SYS', event_after='BLE Started')
            led_dict = self.search_event(event_type='LED', event_after='Full Solid')
            if sys_dict and led_dict:
                if self.led_list.index(led_dict) - self.led_list.index(sys_dict) > 0:  # 10 is just an approximate number..
                    pass
            else:
                raise self.err.TestFailure('LED is not from Fast Breathing to Full Solid while rebooting.')


    def reboot_device(self):
        self.ssh_client.reboot_device()
        start_time = time.time()
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=self.timeout):
            raise self.err.TestFailure('Device was not shut down successfully!')
        if not self.ssh_client.wait_for_device_boot_completed(timeout=self.timeout):
            raise self.err.TestFailure('Device was not boot up successfully!')
        self.log.warning("Reboot complete in {} seconds".format(time.time() - start_time))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/led_yoda.py --uut_ip 10.92.224.61 --cloud_env qa1 --dry_run --debug_middleware\
         --disable_clean_logcat_log """)

    test = LEDYodaPowerup(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)