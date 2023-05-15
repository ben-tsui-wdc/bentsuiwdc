# -*- coding: utf-8 -*-
""" Wifi Functional Test: KAM-25276, KAM-25277.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from platform_libraries.pyutils import retry
# test case
from ap_connect import APConnect


class ScanNewSSIDAfterSSIDChanged(APConnect):

    TEST_SUITE = 'WIFI Functional Tests'
    TEST_NAME = 'Scan New SSID After SSID Changed'

    def test(self):
        temp_ssid = 'TEMP_SSID'

        self.reset_logcat_start_line()
        try:
            self.log.test_step('Configure AP (SSID:{}, Password:{}, Security Mode:{}({}))'.format(
                temp_ssid, self.test_password, self.test_security_mode, self.ap.security_key_mapping(self.test_security_mode))
            )
            self.set_ap(
                ssid=temp_ssid, password=self.test_password, security_mode=self.test_security_mode, wifi_type=self.test_wifi_type
            )

            self.log.test_step('Scan and check SSID: {} in list'.format(temp_ssid))
            retry( # Retry 5 mins.
                    func=self.check_ssid_scan, ssid=temp_ssid,
                    excepts=(self.err.TestFailure), delay=10, max_retry=6*5, log=self.log.warning
                )
            self.log.info('SSID found.')

            self.log.test_step('Test device connect AP & Reconnect ADB')
            self.connect_ap(
                ssid=temp_ssid, password=self.test_password, security_mode=self.test_security_mode
            )

            if self.check_wifi_status: # Logcat logs may missing.
                self.log.test_step('Check system log: "Wifi Connected"')
                retry( # Retry 30 mins.
                    func=self.check_wifi, wifi_status='Wifi Connected',
                    excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
                )

            # NEED BTLE ONBOADING
            if self.run_with_on_boarding:
                self.log.test_step('Check system log: LED is "Full Solid"')
                retry( # Retry 30 mins.
                    func=self.check_serial_led, light_pattern='Full Solid',
                    excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
                )

        finally: # Even previous steps failed, it still recovery AP setting to make sure next test can run, and AVOID export logcat via ADB.
            # Target test is findished, then recover AP settings
            self.log.test_step('Recover AP (SSID:{}, Password:{}, Security Mode:{}({}))'.format(
                self.test_ssid, self.test_password, self.test_security_mode, self.ap.security_key_mapping(self.test_security_mode))
            )
            self.set_ap(
                ssid=self.test_ssid, password=self.test_password, security_mode=self.test_security_mode, wifi_type=self.test_wifi_type
            )

            self.log.test_step('Test device connect AP & Reconnect ADB')
            self.connect_ap(
                ssid=self.test_ssid, password=self.test_password, security_mode=self.test_security_mode
            )

            if self.check_wifi_status: # Logcat logs may missing.
                self.log.test_step('Check system log: "Wifi Connected"')
                retry( # Retry 30 mins.
                    func=self.check_wifi, wifi_status='Wifi Connected',
                    excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
                )

            # NEED BTLE ONBOADING
            if self.run_with_on_boarding:
                self.log.test_step('Check system log: LED is "Full Solid"')
                retry( # Retry 30 mins.
                    func=self.check_serial_led, light_pattern='Full Solid',
                    excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
                )

    def check_ssid_scan(self, ssid):
        self.serial_client.scan_wifi_ap()
        if not self.serial_client.list_wifi_ap(filter_keyword=ssid, wait_timeout=60, raise_error=True):
            self.log.error('SSID not found.')
            raise self.err.TestFailure('SSID not found in list.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** ScanNewSSIDAfterSSIDChanged test on Kamino Android ***
        Examples: ./run.sh functional_tests/scan_new_ssid_after_ssid_changed.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-rwob', '--run_with_on_boarding', help='Test device has already on setting up AP with BLTE', action='store_true', default=False)

    test = ScanNewSSIDAfterSSIDChanged(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
