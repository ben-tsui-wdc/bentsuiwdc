# -*- coding: utf-8 -*-
""" Test cases to check Wi-Fi 2.4/5 GHz enabled.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class WiFiEnableCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Wi-Fi Enable Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-23756,KAM-23757,KAM-23830'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.wifi_cmd = 'wpa_cli -i wlan0 -p /data/misc/wifi/sockets '

    def test(self):
        model = self.uut.get('model')
        if model == 'monarch' or model == 'pelican':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(model))
        self.check_wifi_AP(timeout=30)
        self.serial_client.setup_and_connect_WiFi(ssid=self.env.ap_ssid, password=self.env.ap_password)
        time.sleep(10)
        wifi_status = self.adb.executeShellCommand(self.wifi_cmd+'status | grep wpa_state')[0]
        if 'COMPLETED' not in wifi_status:
            raise self.err.TestFailure('wpa state is not in COMPLETED !!')
        if not self.adb.is_device_pingable:
            raise self.err.TestFailure('Device is not pingable !!')

    def check_wifi_AP(self, timeout):
        start = time.time()
        self.serial_client.scan_wifi_ap()
        wifi_scan = self.serial_client.list_wifi_ap(filter_keyword=self.env.ap_ssid)
        while not wifi_scan:
            if time.time() - start > timeout:
                raise self.err.TestSkipped('Wi-Fi AP is not ready, Skipped the test !!')
            self.log.warning('Wi-Fi AP is not ready !!')
            self.serial_client.scan_wifi_ap()
            wifi_scan = self.serial_client.list_wifi_ap(filter_keyword=self.env.ap_ssid)
            time.sleep(1)

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Wi-Fi Enable Check Script ***
        Examples: ./run.sh bat_scripts_new/wifi_enable_check.py --uut_ip 10.92.224.68\
        """)

    test = WiFiEnableCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
