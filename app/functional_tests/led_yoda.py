# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import re
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from bat_scripts_new.factory_reset import FactoryReset

class LEDYoda(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'LED_Yoda'
    SETTINGS = {'uut_owner':False}
    # Popcorn
    TEST_JIRA_ID = 'KAM-24678'

    def declare(self):
        self.timeout = 300

    
    def init(self):
        if 'yoda' not in self.uut.get('model'):
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(self.uut.get('model')))


    def test(self):
        if self.led_test_case == 'softap_mode':
            #raise self.err.TestSkipped('Due to http://jira.wdmv.wdc.com/browse/KAM200-2223, skipped the test !!'.format(self.uut.get('model')))
            self.softap_mode()
        elif self.led_test_case == 'ready_to_onboard':
            self.ready_to_onboard()
        elif self.led_test_case == 'power_up':
            self.power_up()


    # KAM-24656: [LED] YODA - Ready to onboard
    def ready_to_onboard(self):
        self.log.info('factory_reset by serial_client_write ...')
        self.serial_client.serial_write('busybox nohup reset_button.sh factory')
        time.sleep(60*2)  # Wait for factory_reset finished
        self.serial_client.wait_for_boot_complete(timeout=900)
        count = 0
        while True:  # Sometimes BLE won't be started as soon as device finished rebooting .
            try:
                self.serial_client.serial_write('logcat -d | grep LedServer && echo FINISHED')
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
                self.full_solid_check()
                break
            except:
                time.sleep(10)
                count += 1
                if count > 3:
                    raise
        # set wifi configuration
        if self.env.ap_ssid:
            ap_ssid = self.env.ap_ssid
            ap_password = self.env.ap_password
        else:
            raise self.err.StopTest('There is no ap_ssid or ap_passowrd')
        self.serial_client.setup_and_connect_WiFi(ssid=ap_ssid, password=ap_password)
        

    # KAM-24657: [LED] YODA - Powerup and Initializing
    def power_up(self):
        stdout, stderr = self.adb.executeShellCommand('logcat -c')
        self.serial_client.serial_write('busybox nohup reboot')
        self.serial_client.wait_for_boot_complete(timeout=60*10)
        time.sleep(20)
        self.led_list = self.adb.get_led_logs()
        if not self.led_list:
            raise self.err.StopTest('There are no LED info in logcat!')
        start_time = time.time()
        while not self.search_event(event_type='SYS', event_after='Wifi Connected'):
            self.led_list = self.adb.get_led_logs()
            time.sleep(3)
            if time.time() - start_time > 180:
                raise self.err.TestFailure("After 180 seconds, wifi still doesn't reconnect after device finished reboot!")
        self.full_solid_check()

    # KAM-24678: [LED] YODA - SoftAP mode
    def softap_mode(self):
        stdout, stderr = self.adb.executeShellCommand('logcat -c')

        stdout, stderr = self.adb.executeShellCommand('busybox nohup reset_button.sh short')
        time.sleep(210)  # According to current spec, softAP mode will change back to client mode after 3 minutes.

        self.led_list = self.adb.get_led_logs()
        if not self.led_list:
            raise self.err.StopTest('There are no LED info in logcat!')
        # check wifi client -> Soft AP mode
        sys_dict = self.search_event(event_type='SYS', event_after='SoftAP on')
        led_dict = self.search_event(event_type='LED', event_after='Slow Breathing')
        '''
        # Because sometimes the sequence is Full Solid -> Fast Breathing(due to Proxy Disconnected)  -> Slow Breathing, script cannot be sure the event_before.
        sys_dict = self.search_event(event_type='SYS', event_before='Wlan0_Up', event_after='SoftAP on')
        led_dict = self.search_event(event_type='LED', event_before='Full Solid', event_after='Slow Breathing')
        '''
        if self.led_list.index(led_dict) - self.led_list.index(sys_dict) < 10:  # 10 is just an approximate number.
            pass
        else:
            raise self.err.TestFailure('LED is not Slow Breathing after SoftAP on')
        # check Soft AP mode -> wifi client
        sys_dict = self.search_event(event_type='SYS', event_after='SoftAP Clear')
        full_solid_dict = self.search_event(event_type='LED', event_after='Full Solid')
        '''
            Sometimes the LED won't turn into Full Solid due to any unexpected behaviors.
        '''
        if not sys_dict:
            raise self.err.TestFailure('There is no "SoftAP Clear" in LedServer message of logcat')
        if not full_solid_dict:
            self.log.warning('There is no "FuLL Solid" in LedServer message of logcat. Will check if device is ready.')
            if not self.search_event(event_type='SYS', event_before='SoftAP Clear', event_after='Ready') and not self.search_event(event_type='SYS', event_before='Ready', event_after='SoftAP Clear'):
                raise self.err.TestFailure('DUT is not Ready after SoftAP Clear')
        if sys_dict and full_solid_dict:
            if self.led_list.index(full_solid_dict) - self.led_list.index(sys_dict) < 10:
                pass
            else:
                raise self.err.TestFailure('LED is not Full Solid after SoftAP Clear')


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
        led_dict = self.search_event(event_type='LED', event_before='Low Solid', event_after='Full Solid')
        
        if sys_dict and led_dict:
            if self.led_list.index(sys_dict) - self.led_list.index(led_dict) < 10:  # 10 is just an approximate number.
                pass
            else:
                raise self.err.TestFailure('LED is not Low Solid to Full Solid while rebooting.')
        else:  # Beacuse sometimes Yoda will have different LED event sequence
            #sys_dict = self.search_event(event_type='SYS', event_before='Ready', event_after='BLE Started')
            sys_dict = self.search_event(event_type='SYS', event_after='BLE Started')
            led_dict = self.search_event(event_type='LED', event_after='Full Solid')
            if sys_dict and led_dict:
                if self.led_list.index(sys_dict) - self.led_list.index(led_dict) < 10:  # 10 is just an approximate number.
                    pass
            else:
                raise self.err.TestFailure('LED is not Low Solid to Full Solid while rebooting.')


    def reboot_device(self):
        self.adb.executeShellCommand('busybox nohup reboot')
        self.log.info('busybox nohup reboot')
        self.adb.disconnect()
        time.sleep(30)

        # check device boot up
        while not self._is_timeout(self.timeout):
            stdout, stderr = self.adb.executeShellCommand('getprop sys.boot_completed', timeout=10)
            if '1' in stdout:
                break
            time.sleep(2)

        while not self._is_timeout(self.timeout):
            stdout, stderr = self.adb.executeShellCommand('ps | grep restsdk', timeout=10)
            if '/system/bin/restsdk/restsdk-server' in stdout:
                break
            time.sleep(2)

        if self._is_timeout(self.timeout):
            raise self.err.StopTest('Device is not ready, timeout for {} minutes'.format(self.timeout/60))
        else:
            self.log.info('Reboot finished.')


    def _is_timeout(self, timeout):
        return (time.time() - self.start_time) >= timeout


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/led_yoda.py --uut_ip 10.92.224.61 --cloud_env qa1 --dry_run --debug_middleware\
         --disable_clean_logcat_log  --led_test_case  softap_mode """)
    ''' 
    led_test_case includes
        softap_mode
        ready_to_onboard
    '''
    parser.add_argument('--led_test_case', help='For differenct test case of JIRA ticket', default=None)

    test = LEDYoda(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)