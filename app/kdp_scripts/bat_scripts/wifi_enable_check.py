# -*- coding: utf-8 -*-
""" Test cases to check Wi-Fi 2.4/5 GHz enabled.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class WiFiEnableCheck(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'Wi-Fi Enable Check'
    TEST_JIRA_ID = 'KDP-293,KDP-294,KDP-289,KDP-287'

    SETTINGS = {
        'uut_owner': False,
        'serial_client': True
    }

    def before_test(self):
        model = self.uut.get('model')
        if model == 'monarch2' or model == 'pelican2':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(model))

    def test(self):
        # self.check_wifi_AP_ssid_exist(timeout=60*2)
        current_ip = self.serial_client.retry_for_connect_WiFi_kdp(ssid=self.env.ap_ssid, password=self.env.ap_password)
        if not current_ip:
            raise self.err.TestFailure("Failed to connect to ssid {}".format(self.env.ap_ssid))

    def check_wifi_AP_ssid_exist(self, timeout):
        start = time.time()
        wifi_scan = self.serial_client.scan_wifi_ap_and_list_kdp(filter_keyword=self.env.ap_ssid)
        while not wifi_scan:
            if time.time() - start > timeout:
                raise self.err.TestSkipped('Wi-Fi AP is not ready, Skipped the test !!')
            self.log.warning('Wi-Fi AP is not ready !!')
            wifi_scan = self.serial_client.scan_wifi_ap_and_list_kdp(filter_keyword=self.env.ap_ssid)
            time.sleep(1)

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Wi-Fi Enable Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/wifi_enable_check.py --uut_ip 10.92.224.68
                    --ap_ssid private_5G --ap_password automation --ss_ip 10.92.235.234 --ss_port 20048\
        """)

    test = WiFiEnableCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
