# -*- coding: utf-8 -*-
""" Platform WiFi Functional Tests.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
# Sub-tests
from functional_tests.wifi.ap_connect import APConnect
from functional_tests.wifi.auto_connect_after_device_reboot import AutoConnectAfterDeviceReboot
from functional_tests.wifi.auto_connect_after_wifi_recovered import AutoConnectAfterWiFiRecovered
from functional_tests.wifi.auto_connect_after_wifi_recovered_and_device_reboot import AutoConnectAfterWiFiRecoveredAndDeviceReboot
from functional_tests.wifi.led_blinking_after_pw_changed import LedBlinkingAfterPasswordChanged
from functional_tests.wifi.led_blinking_after_ssid_changed import LedBlinkingAfterSSIDChanged
from functional_tests.wifi.scan_new_ssid_after_ssid_changed import ScanNewSSIDAfterSSIDChanged


class WiFiFunctionalTest(IntegrationTest):

    TEST_SUITE = 'WiFi Functional Test'
    TEST_NAME = 'WiFi Functional Test'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.test_2_4G_ssid = '1A-2.4G-dd-wrt'
        self.test_2_4G_password = '1qaz2wsx'
        self.test_2_4G_security_mode = 'psk2'
        self.test_5G_ssid = '1A-5G-dd-wrt'
        self.test_5G_password = '1qaz2wsx'
        self.test_5G_security_mode = 'psk2'

    def init(self):
        self.integration.add_testcases(testcases=[
            # 2.4G
            # SSID: Original -> 2.4G
            (
                APConnect, {
                'TEST_NAME': 'KAM-25239: 2.4G Verify Yoda connectivity in WPA2 Personal to AP',
                'test_ssid': self.test_2_4G_ssid, 'test_password': self.test_2_4G_password, 'test_security_mode': self.test_2_4G_security_mode,
                'test_wifi_type': '2.4G', 'ap_power_port': self.ap_power_port, 'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus']
            }),
            (
                AutoConnectAfterDeviceReboot, {
                'TEST_NAME': 'KAM-25274: 2.4G Verify Yoda connects to AP automatically with already configured SSID upon hard reboot of Yoda device',
                'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus'],
            }),
            (
                AutoConnectAfterWiFiRecovered, {
                'TEST_NAME': 'KAM-25272: 2.4G Verify Yoda connects to AP automatically with already configured SSID when SSID goes off and available again',
                'ap_power_port': self.ap_power_port, 'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus'],
            }),
            (
                AutoConnectAfterWiFiRecoveredAndDeviceReboot, {
                'TEST_NAME': 'KAM-25774: 2.4G Verify Yoda connects to AP automatically with already configured SSID upon hard reboot of Yoda device as well as AP',
                'ap_power_port': self.ap_power_port, 'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus'],
            }),
            (
                LedBlinkingAfterSSIDChanged, {
                'TEST_NAME': 'KAM-25286: 2.4G Verify LED starts blinking after changing the SSID name of connected SSID in AP',
                'test_ssid': self.test_2_4G_ssid, 'test_password': self.test_2_4G_password, 'test_security_mode': self.test_2_4G_security_mode, 'test_wifi_type': '2.4G',
                'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus'],
            }),
            (
                LedBlinkingAfterPasswordChanged, {
                'TEST_NAME': 'KAM-25284: 2.4G Verify LED starts blinking after changing the password for the connected SSID in AP',
                'test_ssid': self.test_2_4G_ssid, 'test_password': self.test_2_4G_password, 'test_security_mode': self.test_2_4G_security_mode, 'test_wifi_type': '2.4G',
                'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus'],
            }),
            (
                ScanNewSSIDAfterSSIDChanged, {
                'TEST_NAME': 'KAM-25276: 2.4G Verify Yoda scans the new SSID when the connected SSID is changed in the AP',
                'test_ssid': self.test_2_4G_ssid, 'test_password': self.test_2_4G_password, 'test_security_mode': self.test_2_4G_security_mode,
                'test_wifi_type': '2.4G', 'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus']
            }),
            # SSID: 2.4G -> 2.4G_BGN
            ( # This test need SSID change to make sure status changes.
                APConnect, {
                'TEST_NAME': 'KAM-25231: 2.4G Verify Yoda connectivity to AP configured with BGN mode',
                'test_ssid': self.test_2_4G_ssid + '_BGN', 'test_password': self.test_2_4G_password, 'test_security_mode': self.test_2_4G_security_mode,
                'test_wifi_type': '2.4G', 'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus']
            }),
            # 5G
            # SSID: Original -> 2.4G
            (
                APConnect, {
                'TEST_NAME': 'KAM-25240: 5G Verify Yoda connectivity in WPA2 Personal to AP',
                'test_ssid': self.test_5G_ssid, 'test_password': self.test_5G_password, 'test_security_mode': self.test_5G_security_mode,
                'test_wifi_type': '5G', 'ap_power_port': self.ap_power_port, 'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus']
            }),
            (
                AutoConnectAfterDeviceReboot, {
                'TEST_NAME': 'KAM-25275: 5G Verify Yoda connects to AP automatically with already configured SSID upon hard reboot of Yoda device',
                'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus'],
            }),
            (
                AutoConnectAfterWiFiRecovered, {
                'TEST_NAME': 'KAM-25273: 5G Verify Yoda connects to AP automatically with already configured SSID when SSID goes off and available again',
                'ap_power_port': self.ap_power_port, 'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus'],
            }),
            (
                AutoConnectAfterWiFiRecoveredAndDeviceReboot, {
                'TEST_NAME': 'KAM-25775: 5G Verify Yoda connects to AP automatically with already configured SSID upon hard reboot of Yoda device as well as AP',
                'ap_power_port': self.ap_power_port, 'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus'],
            }),
            (
                LedBlinkingAfterSSIDChanged, {
                'TEST_NAME': 'KAM-25287: 5G Verify LED starts blinking after changing the SSID name of connected SSID in AP',
                'test_ssid': self.test_5G_ssid, 'test_password': self.test_5G_password, 'test_security_mode': self.test_5G_security_mode, 'test_wifi_type': '5G',
                'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus']
            }),
            (
                LedBlinkingAfterPasswordChanged, {
                'TEST_NAME': 'KAM-25285: 5G Verify LED starts blinking after changing the password for the connected SSID in AP',
                'test_ssid': self.test_5G_ssid, 'test_password': self.test_5G_password, 'test_security_mode': self.test_5G_security_mode, 'test_wifi_type': '5G',
                'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus']
            }),
            (
                ScanNewSSIDAfterSSIDChanged, {
                'TEST_NAME': 'KAM-25277: 5G Verify Yoda scans the new SSID when the connected SSID is changed in the AP',
                'test_ssid': self.test_5G_ssid, 'test_password': self.test_5G_password, 'test_security_mode': self.test_5G_security_mode,
                'test_wifi_type': '5G', 'run_with_on_boarding': True, 'run_models': ['yoda', 'yodaplus']
            })
        ])


    def after_test(self):
        # Recover AP setting.
        ut = APConnect(self)
        ut.recover_wifi_changes = True
        ut.recover_ap = False
        ut.original_ssid = self.env.ap_ssid
        ut.original_password = self.env.ap_password
        ut.original_security_mode = 'psk'
        ut.original_wifi_type = '5G'
        self.log.warning('Use sub-test as a tool to recovery Wi-Fi/AP settings to make sure test device is good for next test runs...')
        ut.after_test()


if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** WiFiFunctionalTest Running script ***
        Examples: ./start.sh functional_tests/wifi/wifi_functional --uut_ip 10.92.224.68 -env dev1\
        """)

    # Test Arguments
    parser.add_argument('-app', '--ap_power_port', help='AP port on power switch', metavar='PORT', type=int)
    parser.add_argument('-24Gssid', '--test_2_4G_ssid', help='AP SSID for 2.4G test', metavar='SSID')
    parser.add_argument('-24Gpw', '--test_2_4G_password', help='AP password for 2.4G test', metavar='PWD')
    parser.add_argument('-24Gsm', '--test_2_4G_security_mode', help='Security mode for 2.4G test', metavar='MODE', default='psk2')
    parser.add_argument('-5Gssid', '--test_5G_ssid', help='AP SSID for 5G test', metavar='SSID')
    parser.add_argument('-5Gpw', '--test_5G_password', help='AP password for 5G test', metavar='PWD')
    parser.add_argument('-5Gsm', '--test_5G_security_mode', help='Security mode for 5G test', metavar='MODE', default='psk2')

    test = WiFiFunctionalTest(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
