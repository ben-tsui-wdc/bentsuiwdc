# -*- coding: utf-8 -*-
""" Test cases to check Wi-Fi 2.4/5 GHz switched.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.serial_client import SerialClient


class WiFiSwitchCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Wi-Fi Switch Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-23758'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.server_ip = 'fileserver.hgst.com'
        self.serial_port = '20012'

    def init(self):
        self.result = True
        self.wifi_cmd = 'wpa_cli -i wlan0 -p /data/misc/wifi/sockets '
        self.wifi_psk = 'automation'
        self.ssid_2G = 'private_2.4G'
        self.ssid_5G = 'private_5G'

    def test(self):
        self.check_wifi_AP()
        wifi_list_2G = self.serial_client.list_network(filter_keyword=self.ssid_2G)
        if not wifi_list_2G:
            self.log.warning('Setup 2.4GHz Wi-Fi configuration')
            self.serial_client.add_wifi(ssid=self.ssid_2G, password=self.wifi_psk, enable_wifi=False, connect_wifi=False)
            time.sleep(3)
        wifi_list_5G = self.serial_client.list_network(filter_keyword=self.ssid_5G)
        if not wifi_list_5G:
            self.log.warning('Setup 5GHz Wi-Fi configuration')
            self.serial_client.add_wifi(ssid=self.ssid_5G, password=self.wifi_psk, enable_wifi=False, connect_wifi=False)
            time.sleep(3)
        list_status = self.serial_client.list_network(filter_keyword='[CURRENT]')
        if not list_status:
            self.log.info('Enable network 0 first ...')
            self.serial_client.connect_network(network_id=0)
            time.sleep(8)
        wifi_2G_state = self.serial_client.get_network(self.ssid_2G)
        wifi_5G_state = self.serial_client.get_network(self.ssid_5G)

        # Start Switch
        if '[CURRENT]' in wifi_2G_state:
            wifi_num_5G = wifi_5G_state[0]
            self.log.info('Start to switch 2.4GHz to 5GHz ...')
            self.enable_network_and_check(wifi_num_5G, self.ssid_5G)
        elif '[CURRENT]' in wifi_5G_state:
            wifi_num_2G = wifi_2G_state[0]
            self.log.info('Start to switch 5GHz to 2.4GHz ...')
            self.enable_network_and_check(wifi_num_2G, self.ssid_2G)
        else:
            raise self.err.TestFailure('No network for {0} and {1} was connect'.format(self.ssid_2G, self.ssid_5G))

        wifi_2G_state = self.serial_client.get_network(self.ssid_2G)
        wifi_5G_state = self.serial_client.get_network(self.ssid_5G)

        # Switch back
        self.log.info('*** Start to switch back ***')
        if '[CURRENT]' in wifi_2G_state:
            wifi_num_5G = wifi_5G_state[0]
            self.log.info('Start to switch back from 2.4GHz to 5GHz ...')
            self.enable_network_and_check(wifi_num_5G, self.ssid_5G)
        elif '[CURRENT]' in wifi_5G_state:
            wifi_num_2G = wifi_2G_state[0]
            self.log.info('Start to switch back from 5GHz to 2.4GHz ...')
            self.enable_network_and_check(wifi_num_2G, self.ssid_2G)
        else:
            raise self.err.TestFailure('No network for {0} and {1} was switch back'.format(self.ssid_2G, self.ssid_5G))

    def check_wifi_AP(self):
        wifi_scan_2G = self.serial_client.list_wifi_ap(filter_keyword=self.ssid_2G)
        wifi_scan_5G = self.serial_client.list_wifi_ap(filter_keyword=self.ssid_5G)
        if not wifi_scan_2G or not wifi_scan_5G:
            self.log.warning('Wi-Fi AP is not ready !!')
            self.result = 'skip'
            raise

    def enable_network_and_check(self, network_num, ssid):
        self.adb.disconnect()
        self.serial_client.disconnect_WiFi()
        time.sleep(3)
        self.serial_client.connect_network(network_id=network_num)
        time.sleep(8)
        status = self.serial_client.get_network(ssid)
        if '[CURRENT]' not in status:
            self.result = False
            raise
        wifi_state = self.adb.executeShellCommand(self.wifi_cmd+'status | grep wpa_state')[0]
        if 'COMPLETED' not in wifi_state:
            self.result = False
            raise

    def after_test(self):
        if not self.result:
            raise self.err.TestFailure('Wi-Fi Switch Check Failed !!')
        elif self.result == 'skip':
            raise self.err.TestSkipped('Wi-Fi AP is not ready, Skipped the test !!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Wi-Fi Switch Check Script ***
        Examples: ./run.sh bat_scripts_new/wifi_switch_check.py --uut_ip 10.92.224.68\
        """)

    test = WiFiSwitchCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
