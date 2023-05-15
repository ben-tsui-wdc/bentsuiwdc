# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import re
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.bat_scripts.factory_reset import FactoryReset
from platform_libraries.constants import KDP
from platform_libraries.restAPI import RestAPI

class LEDDeviceReset(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-900 - [LED] Devcie reset'
    SETTINGS = {'uut_owner':True}
    # Popcorn
    TEST_JIRA_ID = 'KDP-900'

    def declare(self):
        pass

    def init(self):
        # Please note that the seq_expect below are based on the testing device(MCH) which is connected to internet.
        if self.uut['model'] in ['monarch2', 'pelican2']:
            # For monarch2/pelican2
            # long: Press reset button for 30~60 seconds -> LED 100% light and slow breathing, device starts "device reset(demote user)"
            self.reset_button_cmd = ['long']
            self.reset_button_check_list = ['"msgid":"hardware_reset","reason":"Perform Hardware Reset"']
            self.notify_cloud_check_list = ['sender = reset_button, notification id=', 'Sending delete owner']
            # Because there is no way to know what is the original Led state. 
            self.led_ctrl_server_check_list = ['->(Slow Breathing)', ' -> (Device Reset)', 'Switching Led state (Slow Breathing)->', 'sys state change: (Device Reset) -> (Device Reset Completed)']
        elif self.uut['model'] in ['yodaplus2']:
            # For yodaplus2
            # middle_start: Press and hold reset button for 30~35 seconds -> LED start fast breathing to inform user that 30 seconds has been reached.
            # long_start: Press and hold reset button after 35 seconds -> LED full solid 
            # long: Press and hold reset button more than 35 seconds then release reset button -> LED slow breathing and devices starts "device reset (demote user)"
            self.reset_button_cmd = ['middle_start', 'long_start', 'long']
            self.reset_button_check_list = ['"msgid":"reset_button","reason":"middle start"', '"msgid":"reset_button","reason":"long start"', '"msgid":"reset_button","reason":"long press"']
            self.notify_cloud_check_list = ['sender = reset_button, notification id=', 'Sending delete owner']
            # Because there is no way to know what is the original Led state. 
            self.led_ctrl_server_check_list = ['"sys_state received Reset Button Middle, led_state turns to Fast Breathing"', '"Switching Led state (Full Solid)->(Fast Breathing)"', '-> (Reset Button Middle)', '"sys_state received Reset Button Long, led_state turns to Full Solid"', '->(Full Solid)', '"sys state change: (Reset Button Middle) -> (Reset Button Long)"','"sys_state received Demote User, led_state turns to Slow Breathing"', '->(Slow Breathing)', '"sys state change: (Reset Button Long) -> (Demote User)"', 'sys_state received Demote User Clear', 'Switching Led state (Slow Breathing)->', 'sys state change: (Demote User) -> (Demote User Clear )']

    def before_test(self):
        time_stamp = time.time()
        self.ssh_client.execute_cmd('analyticlog -l INFO -s led_ctrl_server -m test_automation "string:test:start_{}"'.format(time_stamp))
        for item in self.reset_button_cmd:
            self.ssh_client.execute_cmd('reset_button.sh {}'.format(item))
        self.ssh_client.execute_cmd('analyticlog -l INFO -s led_ctrl_server -m test_automation "string:test:end_{}"'.format(time_stamp))
        stdout, stderr = self.ssh_client.execute_cmd('cat /var/log/analyticpublic.log')
        temp = stdout.splitlines()
        self.led_log_list = []
        led_record_flag = False
        for line in temp:
            if 'test_automation' in line:
                if '"test":"start_{}"'.format(time_stamp) in line:
                    led_record_flag = True
                    continue
                elif '"test":"end_{}"'.format(time_stamp) in line:
                    led_record_flag = False
            if led_record_flag: 
                self.led_log_list.append(line)
        self.log.warning(self.led_log_list)

    def test(self):
        temp = self.led_log_list.pop(0)
        if 'info reset_button.sh' in temp:
            check_item = self.reset_button_check_list.pop(0)
            if check_item not in temp:
                raise self.err.TestFailure('Expect: "{}", Actual: "{}"'.format(check_item, temp))
        while self.led_log_list:
            temp = self.led_log_list.pop(0)
            if 'info led_ctrl_server' in temp:
                check_item = self.led_ctrl_server_check_list.pop(0)
            elif 'Notify' in temp and 'Cloud' in temp:
                check_item = self.notify_cloud_check_list.pop(0)
            else:
                continue
            # To get the led origianl state
            if check_item == '->(Slow Breathing)' and check_item in temp:
                led_original_state = re.search("\((.+)\)->\((.+)\)", temp).group(1)
            elif check_item == 'Switching Led state (Slow Breathing)->':
                check_item = 'Switching Led state (Slow Breathing)->({})'.format(led_original_state)
                self.log.warning('final check_item for led state: {}'.format(check_item))
            if check_item in temp:
                pass
            else:
                raise self.err.TestFailure('Expect: "{}", Actual: "{}"'.format(check_item, temp))

    def after_test(self):
        # factory_reset device to restore testing environment
        env_dict = self.env.dump_to_dict()
        self.log.info('Start factory_reset to restore tesing envieonment ...')
        factory_reset = FactoryReset(env_dict)
        factory_reset.run_rest_api = False
        factory_reset.test()
        self.ssh_client.lock_otaclient_service_kdp()
        # Re-attach the original owener
        self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
        self.uut_owner.id = 0  # Reset uut_owner.id
        self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']})


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/led/led_device_reset.py --uut_ip 10.92.224.61 --cloud_env qa1 --dry_run --debug_middleware\
         --disable_clean_logcat_log """)

    test = LEDDeviceReset(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)