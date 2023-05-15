# -*- coding: utf-8 -*-
""" Test cases for KAM-27071
    Abnormal shutdown while device in SoftAP mode and has W-Fi setting before
"""
__author__ = "Fish Chiang <fish.chiang@wdc.com>"

# std modules
import sys
import time
import argparse

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from bat_scripts_new.factory_reset import FactoryReset
from bat_scripts_new.create_user_attach_user_check import CreateUserAttachUser
from platform_libraries.pyutils import retry

class AbnormalShutdownInSoftAP(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Abnormal shutdown while device in SoftAP mode and has W-Fi setting before'
    # Popcorn
    TEST_JIRA_ID = 'KAM-27071'

    SETTINGS = {
        'uut_owner': False
    }

    start = time.time()

    def init(self):
        self.wifi_cmd = 'wpa_cli -i wlan0 -p /data/misc/wifi/sockets '

    def declare(self):
        self.timeout = 300

    def test(self):
        # Make sure no attached user
        self.factory_reset()
        # Make sure in client mode
        self.serial_client.enable_client_mode()
        # Check LED is full solid when boot completed
        self.log.test_step('Check LED is "Full Solid" when boot completed.')
        retry(
            func=self.check_led_solid, led_status='Full Solid',
            excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=10, log=self.log.warning
        )
        # Config WIFI setting and do onboarding.
        self.connect_wifi()
        self.onboarding()
        # Switch to softap mode
        self.softap_mode()
        # simulate abnormal shutdown
        self.abnormal_shutdown()
        self.check_in_client_mode()
        # Expect device can connect original WIFI AP.
        retry( # Retry 30 mins.
            func=self.check_wifi, wifi_status='Wifi Connected',
            excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
        )
        # Expect LED status is 'Full Solid'
        self.log.test_step('Check LED is "Full Solid" after connect wifi.')
        retry(
            func=self.check_led_solid, led_status='Full Solid',
            excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=10, log=self.log.warning
        )

    def check_wifi(self, wifi_status, led_logs=None):
        led_logs = self.adb.get_led_logs()
        self.adb.print_led_info(led_logs)

        for i, led_info in enumerate(led_logs):
            if all([led_info.get('type') == 'SYS', led_info.get('after') == wifi_status]):
                return True
        return False

    def check_in_client_mode(self):
        ip = self.serial_client.get_ip()
        self.log.info('IP Address = {}'.format(ip))
        if ip == '192.168.43.1': # SoftAP mode
            raise self.err.TestFailure('Device in SoftAP mode: FAILED.')
        self.log.info('Device in Client mode.')

    def check_led_solid(self, led_status):
        led_state = self.serial_client.get_led_state()
        self.log.info('led_state: {}'.format(led_state))
        if led_state == led_status:
            return True
        self.log.warning('LED not "{}" retry...'.format(led_status))
        return False

    def abnormal_shutdown(self):
        time.sleep(30) 
        self.log.info("Powering off the device")
        self.power_switch.power_off(self.env.power_switch_port)
        self.adb.connected = False
        time.sleep(30)  # interval between power off and on
        self.log.info("Powering on the device")
        self.power_switch.power_on(self.env.power_switch_port)
        self.log.info("Wait for reboot process complete")
        time.sleep(90)  # Sleep 90 secs and then check the bootable flag

        if not self.adb.wait_for_device_boot_completed():
            self.log.error('Timeout({}secs) to wait device boot completed..'.format(self.timeout))
            raise self.err.TestFailure('Lost Power Test: FAILED')

    def softap_mode(self):
        stdout, stderr = self.adb.executeShellCommand('logcat -c')
        stdout, stderr = self.adb.executeShellCommand('busybox nohup reset_button.sh short')
        time.sleep(30)
        now_ip = self.serial_client.get_ip()
        self.log.info('now_ip = {}'.format(now_ip))
        if now_ip == '192.168.43.1': # Soft AP mode
            self.log.info('Device in Soft AP mode.')

    def connect_wifi(self):
        self.serial_client.connect_WiFi(ssid=self.env.ap_ssid, password=self.env.ap_password)
        time.sleep(10)
        wifi_status = self.adb.executeShellCommand(self.wifi_cmd+'status | grep wpa_state')[0]
        if 'COMPLETED' not in wifi_status:
            raise self.err.TestFailure('wpa state is not in COMPLETED !!')
        if not self.adb.is_device_pingable:
            raise self.err.TestFailure('Device is not pingable !!')

    def factory_reset(self):
        self.log.info('Start to do factory reset ...')
        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=False']
        factory_reset = FactoryReset(env_dict)
        factory_reset.no_rest_api = True
        factory_reset.disable_ota = False
        factory_reset.test()

    def onboarding(self):
        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=True']
        create_user = CreateUserAttachUser(env_dict)
        create_user.test()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Abnormal shutdown while device in SoftAP mode and has W-Fi setting before ***
        Examples: ./run.sh functional_tests/abnormal_shutdown_in_softap_mode.py --cloud_env qa1 --serial_server_ip 10.0.0.6 --serial_server_port 20000\
        """)

    test = AbnormalShutdownInSoftAP(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
