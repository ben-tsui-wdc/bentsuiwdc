# -*- coding: utf-8 -*-
""" Test cases to auto connect Wi-Fi AP 5G after device abnormal shutdown [KDP-298]
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
import time
import threading
# platform modules
from middleware.arguments import KDPInputArgumentParser
# test case
from wifi_change_5G_to_2G import WifiChange5GTo2G


class AutoConnect5GAfterShutdown(WifiChange5GTo2G):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'KDP-298: Auto connect Wi-Fi AP 5G after device abnormal shutdown'
    # Popcorn
    TEST_JIRA_ID = 'KDP-298'
    REPORT_NAME = 'Functional'


    def test(self):
        self.log.info("Connecting 5G Wi-Fi")
        self.serial_client.retry_for_connect_WiFi_kdp(ssid=self.wifi_ssid_5g, password=self.wifi_password_5g)
        self.env.check_ip_change_by_console()
        self.log.info("Simulating abnormal shutdown")
        self.power_switch.power_off(self.env.power_switch_port)
        # run it in other thread in case of losing boot up message
        time.sleep(5)
        threading.Thread(target=lambda: self.power_switch.power_on(self.env.power_switch_port)).start()
        self.serial_client.wait_for_boot_complete_kdp()
        self.log.info("Updating device IP")
        self.env.check_ip_change_by_console()
        self.log.info('Trying to upload a file')
        self._verify_upload_files()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Auto connect Wi-Fi AP 5G after device abnormal shutdown test ***
        """)
    parser.add_argument('--wifi_ssid_5g', help="", default='R7000_50')
    parser.add_argument('--wifi_password_5g', help="", default='fituser99')
    test = AutoConnect5GAfterShutdown(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
