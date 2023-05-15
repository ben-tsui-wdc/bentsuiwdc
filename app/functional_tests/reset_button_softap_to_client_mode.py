# -*- coding: utf-8 -*-
""" Test cases for KAM-24051: Reset button - SoftAP mode.
    Press reset button 0-30 seconds for SoftAP mode
"""
__author__ = "Fish Chiang <fish.chiang@wdc.com>"

# std modules
import sys
import time
import argparse

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.ssh_client import SSHClient


class SoftAPToClientMode(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Press reset button 0-30 seconds for SoftAP mode'
    # Popcorn
    TEST_JIRA_ID = 'KAM-24051'

    SETTINGS = {
        'uut_owner': False
    }

    start = time.time()

    def init(self):
        self.wifi_cmd = 'wpa_cli -i wlan0 -p /data/misc/wifi/sockets '
        self.model = self.uut.get('model')

    def declare(self):
        self.timeout = 300

    def test(self):
        self.check_device_bootup()
        self.connect_wifi()
        self.softap_mode()
        self.ssid_check()
        self.back_to_client_mode()
        self.connect_wifi()

    def ssid_check(self):
        mac_ssh = SSHClient(self.mac_server_ip, self.mac_username, self.mac_password)
        mac_ssh.connect()
        search_ssid = mac_ssh.execute('/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -s | grep ibi')[1]
        self.log.info('ssid found: {}'.format(search_ssid))
        if self.uut.get('mac_address').lower() not in search_ssid:
            raise self.err.TestFailure('Failed to get ibi SSID !!')
        mac_ssh.close()

    def softap_mode(self):
        stdout, stderr = self.adb.executeShellCommand('logcat -c')
        stdout, stderr = self.adb.executeShellCommand('busybox nohup reset_button.sh short')
        time.sleep(60)
        now_ip = self.serial_client.get_ip()
        self.log.info('now_ip = {}'.format(now_ip))
        if now_ip == '192.168.43.1': # Soft AP mode
            self.log.info('Device in Soft AP mode.')
        else:
            raise self.err.TestError("Device is not in Soft AP mode.")

    def back_to_client_mode(self):
        # Idle softAP mode over 3 minutes.
        self.log.info('Idle softAP mode over 3 minutes...')
        time.sleep(3*60)  # According to current spec, softAP mode will change back to client mode after 3 minutes.
        # Check Soft AP mode -> wifi client mode
        sys_dict = self.search_event(event_type='SYS', event_after='SoftAP Clear')
        if not sys_dict:
            raise self.err.TestFailure('Back to Client mode: FAILED')
        self.log.info('Device in Client mode.')

    def search_event(self, event_type=None, event_before=None, event_after=None):
        count = 0
        dict_list = []
        self.led_list = self.adb.get_led_logs()
        for item in self.led_list:
            if event_type and event_before and event_after:
                if item.get('type')==event_type and item.get('before')==event_before and item.get('after')==event_after:
                    dict_list.append(item)
                    count+=1
            elif event_type and event_after:
                if item.get('type')==event_type and item.get('after')==event_after:
                    dict_list.append(item)
                    count+=1
        if count == 0:
            return None
        elif count > 0:
            if count > 1:
                self.log.warning('The LedServer item occurred many times({})! [type] {} [before] {} [after] {}'.format(count, event_type, event_before, event_after))
                self.log.warning('{}'.format(dict_list))
            return dict_list[0]

    def connect_wifi(self):
        self.serial_client.setup_and_connect_WiFi(ssid=self.env.ap_ssid, password=self.env.ap_password)
        time.sleep(10)
        wifi_status = self.adb.executeShellCommand(self.wifi_cmd+'status | grep wpa_state')[0]
        if 'COMPLETED' not in wifi_status:
            raise self.err.TestFailure('wpa state is not in COMPLETED !!')
        if not self.adb.is_device_pingable:
            raise self.err.TestFailure('Device is not pingable !!')

    def check_device_bootup(self):
        # check device boot up
        while not self.is_timeout(self.timeout):
            if self.adb.check_platform_bootable():
                self.log.info('Boot completed')
                break
            time.sleep(5)

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Press reset button 0-30 seconds while device in SoftAP mode ***
        Examples: ./run.sh functional_tests/reset_button_softap_to_client_mode.py --cloud_env qa1 --serial_server_ip 10.0.0.6 --serial_server_port 20000\
        """)

    parser.add_argument('--mac_server_ip', help='mac_server_ip which is used to be as client.' , default='10.200.140.243')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='root')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac clientt', default='`1q')

    test = SoftAPToClientMode(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
