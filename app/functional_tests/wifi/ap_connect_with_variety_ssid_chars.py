# -*- coding: utf-8 -*-
""" Wifi Functional Test: KAM-25246, KAM-25247.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.pyutils import retry


class APConnectWithVarietySSIDChars(TestCase):

    TEST_SUITE = 'WIFI Functional Tests'
    TEST_NAME = 'AP Connect With Variety SSID Chars'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        for ssid in [''';:'",<.>/?''', 'abc  def', '$$$$&&&&&###  __(`gg`)', '  conexión', 'réseau français', '連接如']:
            self.clean_logcat()
            self.log.test_step('Configure AP (SSID:{}, Password:{}, Security Mode:{}({}))'.format(
                ssid, self.test_password, self.test_security_mode, self.ap.security_key_mapping(self.test_security_mode))
            )
            self.set_ap(
                ssid=ssid, password=self.test_password, security_mode=self.test_security_mode, wifi_type=self.test_wifi_type
            )

            self.log.test_step('Test device connect AP & Reconnect ADB')
            self.connect_ap(
                ssid=ssid, password=self.test_password, security_mode=self.test_security_mode
            )

            self.log.test_step('Check system log: "Wifi Connected"')
            retry( # Retry 30 mins.
                func=self.check_wifi, wifi_status='Wifi Connected',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )

            # NEED BTLE ONBOADING
            if self.run_with_on_boarding:
                self.log.test_step('Check system log: LED is "Full Solid"')
                retry( # Retry 30 mins.
                    func=self.check_led, light_pattern='Full Solid',
                    excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
                )

    def after_test(self):
        self.log.test_step('Recover AP (SSID:{}, Password:{}, Security Mode:{}({}))'.format(
            self.original_ssid, self.original_password, self.original_security_mode, self.ap.security_key_mapping(self.original_security_mode))
        )
        self.set_ap(
            ssid=self.original_ssid, password=self.original_password, security_mode=self.original_security_mode, wifi_type=self.original_wifi_type
        )

        self.log.test_step('Test device connect AP & Reconnect ADB')
        self.connect_ap(
            ssid=self.original_ssid, password=self.original_password, security_mode=self.original_security_mode
        )

        self.log.test_step('Check system log: "Wifi Connected"')
        retry( # Retry 30 mins.
            func=self.check_wifi, wifi_status='Wifi Connected',
            excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
        )

        # NEED BTLE ONBOADING
        if self.run_with_on_boarding:
            self.log.test_step('Check system log: LED is "Full Solid"')
            retry( # Retry 30 mins.
                func=self.check_led, light_pattern='Full Solid',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** APConnectWithVarietySSIDChars test on Kamino Android ***
        Examples: ./run.sh functional_tests/ap_connect_with_variety_ssid_chars.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-app', '--ap_power_port', help='AP port on power switch', metavar='PORT', type=int)
    parser.add_argument('-original_wifi_type', '--original_wifi_type', help='Original Wi-Fi type', default='5G', choices=['2.4G', '5G'])
    parser.add_argument('-test_ssid', '--test_ssid', help='AP SSID for test', metavar='SSID')
    parser.add_argument('-test_password', '--test_password', help='AP password for test', metavar='PWD')
    parser.add_argument('-test_security_mode', '--test_security_mode', help='Security mode for test', metavar='MODE', default='psk2')
    parser.add_argument('-test_wifi_type', '--test_wifi_type', help='Wi-Fi type for test', default='5G', choices=['2.4G', '5G'])
    parser.add_argument('-rwob', '--run_with_on_boarding', help='Test device has already on setting up AP with BLTE', action='store_true', default=False)

    test = APConnectWithVarietySSIDChars(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
