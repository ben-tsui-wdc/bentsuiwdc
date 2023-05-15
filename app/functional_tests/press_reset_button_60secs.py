# -*- coding: utf-8 -*-
""" Test cases to check [Factory reset] Press Reset Button >= 60 secs : Factory reset.
"""
__author__ = "Ben Lin <ben.lin@wdc.com>"

# std modules
import sys
import time
import argparse
import os

# platform modules
from pprint import pformat
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.restAPI import RestAPI
from platform_libraries.pyutils import retry

class PressResetButton60secs(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = '[Factory reset] Press Reset Button >= 60 secs : Factory reset'
    # Popcorn
    TEST_JIRA_ID = 'KAM-14703'

    SETTINGS = {
        'uut_owner': True
    }
    TEST_FILE = 'TEST_DB_LOCK.png'

    start = time.time()

    def init(self):
        self.model = self.uut.get('model')
        self.new_account = ["wdcautotwtest200+qawdc@gmail.com", "wdcautotwtest201+qawdc@gmail.com"]
        self.new_password = ["Auto1234", "Auto1234"]
        self.owner = self.uut_owner

    def declare(self):
        self.timeout = 300

    def before_test(self):
        if os.path.isfile(self.TEST_FILE):
            os.remove(self.TEST_FILE)

    def test(self):
        # Get firmware version.
        firmware = self.uut.get('firmware')

        # verify DUT associate with an user
        self.attach_user()

        # Upload files
        self.log.info('Try to upload a new file by device owner')
        self._create_random_file(self.TEST_FILE)
        with open(self.TEST_FILE, 'rb') as f:
            self.uut_owner.chuck_upload_file(file_object=f, file_name=self.TEST_FILE)
        user_id = self.owner.get_user_id(escape=True)
        if self.adb.check_file_exist_in_nas("{}".format(self.TEST_FILE), user_id):
            self.log.info('Upload test file to device successfully!')
        else:
            raise self.err.TestFailure('Upload test file to device failed!')

        # Install APPs
        self.owner.install_app(app_id='com.elephantdrive.ibi')
        self.owner.install_app(app_id='com.wdc.importapp.ibi')

        # Invite(Attach) a new user
        self.owner.create_user(self.new_account[0], self.new_password[0])
        # Wait for connection after URL updated.
        if self.owner.retry_attach_user: # retry 20 times.
            retry(func=self.owner.attach_user_to_device, delay=10, max_retry=20, log=self.log.warning)
        else:
            self.owner.attach_user_to_device()
        self.attach_user()
        new_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.new_account[0], password=self.new_password[0])
        self.check_cloud_connected(new_owner)

        # Add new files under /data
        self.adb.executeShellCommand('touch /data/wd/diskVolume0/check_reset.txt')

        # Do factory reset
        self.factory_reset()

        # Verify user can not access DUT
        self.owner.wait_until_cloud_connected(60, as_admin=True)
        users, next_page_token = self.owner.get_users(limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(users)))
        if users:
            raise self.err.TestFailure('Check owner is not empty.')

        # Onboard and associate DUT with a new email account
        self.owner.create_user(self.new_account[1], self.new_password[1])
        if self.owner.retry_attach_user: # retry 20 times.
            retry(func=self.owner.attach_user_to_device, delay=10, max_retry=20, log=self.log.warning)
        else:
            self.owner.attach_user_to_device()
        self.attach_user()
        new_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.new_account[1], password=self.new_password[1])
        self.check_cloud_connected(new_owner)

        # Check users data by user uploaded
        abs_file_path = "/data/wd/diskVolume0/restsdk/userRoots/"
        files = self.adb.executeShellCommand('find {} -type file'.format(abs_file_path), consoleOutput=False)[0].strip()
        if files:
            raise self.err.TestFailure('Found files: {}'.format(files))

        # Check installed APPs
        installed_app = self.owner.get_installed_apps()
        if installed_app:
            raise self.err.TestFailure('Found installed APPs: {}'.format(installed_app))

        # Check firmware version.
        if firmware != self.uut.get('firmware'):
            raise self.err.TestFailure('Firmware version is not match')

    def after_test(self):
        if os.path.isfile(self.TEST_FILE):
            os.remove(self.TEST_FILE)

    def _create_random_file(self, file_name, local_path='', file_size='1048576'):
        # Default 1MB dummy file
        self.log.info('Creating file: {}'.format(file_name))
        try:
            with open(os.path.join(local_path, file_name), 'wb') as f:
                f.write(os.urandom(int(file_size)))
        except Exception as e:
            self.log.error('Failed to create file: {0}, error message: {1}'.format(local_path, repr(e)))
            raise

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

    def check_cloud_connected(self, rest_conn=None):
        device_info = rest_conn.get_device_info()
        self.log.info(device_info)

        cloud_connected_value = None

        for k, v in device_info.items():
            if k == 'cloudConnected':
                cloud_connected_value = str(v)

        if cloud_connected_value == 'True':
            self.log.info('*** PASS: cloudConnected: {}'.format(cloud_connected_value))
        else:
            raise self.err.TestFailure('*** FAIL: cloudConnected: {}'.format(cloud_connected_value))

    def attach_user(self):
        self.owner.wait_until_cloud_connected(60, as_admin=True)
        users, next_page_token = self.owner.get_users(limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(users)))
        self.verify_result(users)

    def verify_result(self, users):
        # Check owner in list
        owner_id = self.owner.get_user_id()
        for user in users:
            if user['id'] == owner_id:
                self.log.info('Check owner in list: PASSED')
                return
        self.log.error('Check owner in list: FAILED')
        raise self.err.TestFailure('Check owner in list failed.')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** [Factory reset] Press Reset Button >= 60 secs : Factory reset Check Script ***
        Examples: ./run.sh functional_tests/press_reset_button_60secs.py --uut_ip 10.92.224.68\
        """)

    test = PressResetButton60secs(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
