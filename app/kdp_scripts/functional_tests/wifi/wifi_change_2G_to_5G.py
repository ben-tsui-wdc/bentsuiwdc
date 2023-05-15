# -*- coding: utf-8 -*-
""" Test cases to connect 2G from 5G [KDP-288]
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import KDPInputArgumentParser
# test case
from wifi_change_5G_to_2G import WifiChange5GTo2G


class WifiChange2GTo5G(WifiChange5GTo2G):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'KDP-288: Change connect Wi-Fi AP 2.4G to 5G'
    # Popcorn
    TEST_JIRA_ID = 'KDP-288'
    REPORT_NAME = 'Functional'


    def test(self):
        self.log.info("Change to connect 2G Wi-Fi")
        self.serial_client.retry_for_connect_WiFi_kdp(ssid=self.wifi_ssid_2g, password=self.wifi_password_2g)
        self.env.check_ip_change_by_console()

        self.log.info('Create a dummy file and upload to test device')
        self._verify_upload_files()

        self.log.info("Connect 5G Wi-Fi")
        self.serial_client.retry_for_connect_WiFi_kdp(ssid=self.wifi_ssid_5g, password=self.wifi_password_5g)
        self.env.check_ip_change_by_console()

        self.log.info('Try to upload a file after Wi-Fi change')
        self._verify_upload_files()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** change wifi and verify ***
        Examples: ./run.sh functional_tests/wifi_change_2G_to_5G.py --uut_ip 10.92.224.68 \
        """)
    parser.add_argument('--wifi_ssid_2g', help="", default='R7000_24')
    parser.add_argument('--wifi_password_2g', help="", default='fituser99')
    parser.add_argument('--wifi_ssid_5g', help="", default='R7000_50')
    parser.add_argument('--wifi_password_5g', help="", default='fituser99')
    test = WifiChange2GTo5G(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
