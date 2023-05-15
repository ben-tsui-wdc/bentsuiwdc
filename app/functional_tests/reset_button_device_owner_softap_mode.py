# -*- coding: utf-8 -*-
""" Test cases to check  Do demote device owner while device in SoftAP mode.
"""
__author__ = "Ben Lin <ben.lin@wdc.com>"

# std modules
import sys
import time
import argparse

# platform modules
from pprint import pformat
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.ssh_client import SSHClient


class FactoryResetDemoteSoftAPMode(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Do demote device owner while device in SoftAP mode'
    # Popcorn
    TEST_JIRA_ID = 'KAM-25155'

    SETTINGS = {
        'uut_owner': True
    }

    start = time.time()

    def init(self):
        self.wifi_cmd = 'wpa_cli -i wlan0 -p /data/misc/wifi/sockets '

    def declare(self):
        self.timeout = 300

    def test(self):
        self.check_device_bootup()
        # self.connect_wifi()
        self.softap_mode()
        self.ssid_check()
        self.factory_reset_40secs()
        self.log.info('Wait 3 mins for back to client mode ...')
        time.sleep(3*60)
        self.verify_result()

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

    def factory_reset_40secs(self):
        self.log.info('Reset button press 40 secs and start ...')
        self.adb.executeShellCommand('busybox nohup reset_button.sh middle')

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
            boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed', timeout=10)[0]
            if '1' in boot_completed:
                self.log.info('Boot completed')
                break
            time.sleep(2)

    def verify_result(self):
        self.uut_owner.wait_until_cloud_connected(60, as_admin=True)
        users, next_page_token = self.uut_owner.get_users(limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(users)))

        # Check owner in list
        owner_id = self.uut_owner.get_user_id()
        for user in users:
            if user['id'] == owner_id:
                self.log.info('Check owner in list: PASSED')
                return
        self.log.error('Check owner in list: FAILED')
        raise self.err.TestFailure('Check owner in list failed.')

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Do demote device owner while device in SoftAP mode Check Script ***
        Examples: ./run.sh functional_tests/reset_button_device_owner_softap_mode.py\
        """)

    parser.add_argument('--mac_server_ip', help='mac_server_ip which is used to be as client.' , default='10.200.140.243')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='root')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac clientt', default='`1q')

    test = FactoryResetDemoteSoftAPMode(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
