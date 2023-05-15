# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import re
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class LEDYodaReadyToOnboard(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-893 - LED_Yoda'
    SETTINGS = {'uut_owner':False}
    # Popcorn
    TEST_JIRA_ID = 'KDP-893'

    def declare(self):
        self.timeout = 300

    
    def init(self):
        if 'yoda' not in self.uut.get('model'):
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(self.uut.get('model')))


    def before_test(self):
        self.log.warning('factory_reset by serial_client_write ...')
        self.serial_client.serial_write('reset_button.sh factory')
        #time.sleep(60*2)  # Wait for factory_reset finished
        self.serial_client.wait_for_boot_complete_kdp(timeout=300)


    def test(self):
        count = 0
        while True:  # Sometimes BLE won't be started as soon as device finished rebooting .
            try:
                self.serial_client.serial_write('cat /var/log/analyticpublic.log*  | grep led_ctrl_server | sort && echo FINISHED')
                self.serial_client.serial_wait_for_string('FINISHED')
                logcat_list = self.serial_client.serial_filter_read_all(re_pattern="\((.+)\) ?-> ?\((.+)\)")
                # parse the led_list from raw format to dictionary format
                self.led_list = []
                for line in logcat_list:
                    if 'sys state change' in line:
                        led_re = re.compile("\((.+)\).->.\((.+)\)")
                        type = 'SYS'
                    elif 'Switching Led state' in line:
                        led_re = re.compile("\((.+)\)->\((.+)\)")
                        type = 'LED'
                    else:
                        continue
                    results = led_re.search(line)
                    if results:
                        string_split = line.split()
                        led_dict = {
                            'date': string_split[0],
                            'time': string_split[1],
                            'type': type,
                            'before': results.group(1),
                            'after': results.group(2)
                        }
                        self.led_list.append(led_dict)
                self.ssh_client.print_led_info(self.led_list)
                self.full_solid_check()
                break
            except:
                time.sleep(10)
                count += 1
                if count > 3:
                    raise


    def after_test(self):
        # set wifi configuration
        if self.env.ap_ssid and self.env.ap_password:
            self.serial_client.retry_for_connect_WiFi_kdp(self.env.ap_ssid, self.env.ap_password)
        else:
            raise self.err.StopTest('There is no ap_ssid or ap_passowrd')

        
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
        sys_dict = self.search_event(event_type='SYS', event_before='Power up', event_after='Wlan0_Up')
        led_dict = self.search_event(event_type='LED', event_before='Fast Breathing', event_after='Full Solid')
        if sys_dict and led_dict:
            self.log.warning('index(Power up -> Wlan0_Up):{}'.format(self.led_list.index(sys_dict)))
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


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/led_yoda.py --uut_ip 10.92.224.61 --cloud_env qa1 --dry_run --debug_middleware\
         --disable_clean_logcat_log """)

    test = LEDYodaReadyToOnboard(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)