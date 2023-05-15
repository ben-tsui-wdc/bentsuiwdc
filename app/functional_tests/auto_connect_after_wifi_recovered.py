# -*- coding: utf-8 -*-
""" Wifi Functional Test: KAM-24658.
"""
__author__ = "Vodka Chen <Vodka.chen@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from platform_libraries.serial_client import SerialClient
from platform_libraries.pyutils import retry
from platform_libraries.powerswitchclient import PowerSwitchClient
# test case
from wifi.ap_connect import APConnect


class AutoConnectAfterWiFiRecovered(APConnect):

    TEST_SUITE = 'WIFI Functional Tests'
    TEST_NAME = 'Auto Connect After Wi-Fi Recovered'
    # Popcorn
    TEST_JIRA_ID = 'KAM-24658'

    def init(self):
        #Set first network , second network environment
        self.ddwrt_ssid = self.test_2_4G_ssid
        self.ddwrt_ssid_pw = self.test_2_4G_password
        self.check_wifi_status = True

    def before_test(self):
        #Check 2.4G or 5G ap device
        self.log.info('{0}: Check {1} AP device'.format(self.TEST_NAME, self.ddwrt_ssid))
        self.check_wifi_AP(timeout=300, filter_keyword=self.ddwrt_ssid)

    def test(self):
        #Connect to DD-WRT ssid
        self.serial_client.setup_and_connect_WiFi(ssid=self.ddwrt_ssid, password=self.ddwrt_ssid_pw, restart_wifi=True)
        #Check connection status
        wifi_list_1 = self.serial_client.list_network(filter_keyword=self.ddwrt_ssid)
        if not wifi_list_1:
            self.log.error('{0}: Connect to {1} AP fail !!'.format(self.TEST_NAME, self.ddwrt_ssid))
            raise self.err.TestFailure('{0}: Connect to First AP fail'.format(self.TEST_NAME))
        self.log.info('{0}: Network Settings => {1}'.format(self.TEST_NAME, self.serial_client.list_network()))

        self.reset_logcat_start_line()
        self.log.info('{0}: Power off AP, AP ip={1}, AP port={2}'.format(self.TEST_NAME, self.ap_power_switch_ip, self.ap_power_port))
        power_switch = PowerSwitchClient(self.ap_power_switch_ip)
        power_switch.power_off(self.ap_power_port)

        self.log.info('{0}: Test device disconnect from Wi-Fi'.format(self.TEST_NAME))
        self.log.info('{0}: Here we use devcice shutdown check as Wi-Fi disconnect check...'.format(self.TEST_NAME))
        if not self.adb.wait_for_device_to_shutdown():
            raise self.err.TestFailure('{0}: AP Wi-Fi disable failed'.format(self.TEST_NAME))

        if self.check_wifi_status: # Logcat logs may missing.
            self.log.info('{0}: Check system log: "Wifi Disconnected"'.format(self.TEST_NAME))
            retry( # Retry 30 mins.
                func=self.check_serial_wifi, wifi_status='Wifi Disconnected',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )

        self.log.info('{0}: Power on AP'.format(self.TEST_NAME))
        power_switch.power_on(self.ap_power_port)

        self.log.info('{0}: Test device connect to Wi-Fi'.format(self.TEST_NAME))
        self.adb.disconnect()
        self.serial_client.restart_adbd()
        self.adb.connect(timeout=60*5)

        if self.check_wifi_status: # Logcat logs may missing.
            self.log.test_step('{0}: Check system log: "Wifi Connected"'.format(self.TEST_NAME))
            retry( # Retry 30 mins.
                func=self.check_wifi, wifi_status='Wifi Connected',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )

    def after_test(self):
        #Recover network to original
        self.serial_client.setup_and_connect_WiFi(ssid=self.env.ap_ssid, password=self.env.ap_password, restart_wifi=True)

    def check_wifi_AP(self, timeout, filter_keyword=None):
        start = time.time()
        self.serial_client.scan_wifi_ap()
        wifi_scan = self.serial_client.list_wifi_ap(filter_keyword)
        while not wifi_scan:
            if time.time() - start > timeout:
                raise self.err.TestSkipped('{0}: Wi-Fi {1} AP is not ready, Skipped the test'.format(self.TEST_NAME, filter_keyword))
            self.serial_client.scan_wifi_ap()
            wifi_scan = self.serial_client.list_wifi_ap(filter_keyword)
            time.sleep(1)

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** AutoConnectAfterWiFiRecovered test on Kamino Android ***
        Examples: ./run.sh functional_tests/auto_connect_after_wifi_recovered.py --uut_ip 10.136.137.159\
        """)
    # Test Arguments
    parser.add_argument('--ap_power_port', help='AP port on power switch', metavar='PORT', type=int, default=1)
    parser.add_argument('--ap_power_switch_ip', help='Power Switch IP Address', metavar='IP', default='10.92.234.106')
    parser.add_argument('--test_2_4G_ssid', help='AP SSID for 2.4G test', metavar='SSID', default='A1-2.4G-dd-wrt')
    parser.add_argument('--test_2_4G_password', help='AP password for 2.4G test', metavar='PWD', default='1qaz2wsx')
    parser.add_argument('--test_2_4G_security_mode', help='Security mode for 2.4G test', metavar='MODE', default='psk2')

    test = AutoConnectAfterWiFiRecovered(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
