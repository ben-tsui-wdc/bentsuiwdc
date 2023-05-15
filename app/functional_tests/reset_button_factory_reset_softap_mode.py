# -*- coding: utf-8 -*-
""" Test cases to check Do Factory reset while device in SoftAP mode.
"""
__author__ = "Ben Lin <ben.lin@wdc.com>"

# std modules
import sys
import time
import argparse

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.ssh_client import SSHClient


class FactoryResetSoftAPMode(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Do Factory reset while device in SoftAP mode'
    # Popcorn
    TEST_JIRA_ID = 'KAM-24052'

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
        # self.connect_wifi()
        self.softap_mode()
        self.ssid_check()
        self.factory_reset()

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

    def factory_reset(self):
        self.log.info('Reset button press 60 secs and start to do factory reset ...')
        self.adb.executeShellCommand('busybox nohup reset_button.sh factory')

        self.log.info('Expect device do rebooting ...')
        if not self.adb.wait_for_device_to_shutdown():
            raise self.err.TestFailure('Device rebooting Failed !!')
        self.log.info('Device rebooting ...')
        if self.model == 'yodaplus' or self.model == 'yoda':
            self.serial_client.serial_wait_for_string('Hardware name: Realtek_RTD1295', timeout=60*10, raise_error=False)
            self.serial_client.wait_for_boot_complete(timeout=self.timeout)
            if self.env.ap_ssid:
                ap_ssid = self.env.ap_ssid
                ap_password = self.env.ap_password
            else:
                ap_ssid = 'private_5G'
                ap_password = 'automation'
            self.serial_client.setup_and_connect_WiFi(ssid=ap_ssid, password=ap_password, restart_wifi=True)
        else:
            time.sleep(60*3)  # For Monarch/Pelican, wait for golden mode reboot
        if not self.adb.wait_for_device_boot_completed(self.timeout):
            raise self.err.TestFailure('Device bootup Failed in {}s !!'.format(self.timeout))
        self.log.info('Device bootup completed.')

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

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Do Factory reset while device in SoftAP mode Check Script ***
        Examples: ./run.sh functional_tests/reset_button_factory_reset_softap_mode.py --cloud_env qa1 --serial_server_ip 10.0.0.6 --serial_server_port 20000\
        """)

    parser.add_argument('--mac_server_ip', help='mac_server_ip which is used to be as client.' , default='10.200.140.243')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='root')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac clientt', default='`1q')

    test = FactoryResetSoftAPMode(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
