# -*- coding: utf-8 -*-
""" Test cases to check 5G wifi change [KAM-23835]
"""
__author__ = "Vodka Chen <vodka.chen@wdc.com>"

# std modules
import sys
import time
import os
import subprocess

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.serial_client import SerialClient
from platform_libraries.restAPI import RestAPI

class WifiChange5GVerify(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Change 5G wifi and Verify'
    # Popcorn
    TEST_JIRA_ID = 'KAM-23835'

    def init(self):
        #Set ssid
        self.ssid_2G = self.wifi_ssid_2g
        self.ssid_2G_password = self.wifi_2g_password
        self.ssid_5G = self.wifi_ssid_5g
        self.ssid_5G_password = self.wifi_5g_password
        #Set rest-api
        self.REST_API = RestAPI(self.env.uut_ip, self.env.cloud_env, self.env.username, self.env.password, root_log='wifi_change_5g_verify_')
        self.user_id = self.REST_API.get_user_id()
        self.user_new_id = self.user_id.replace('|', '_')
        self.test_file = ''
        self.root_folder = '/data/wd/diskVolume0/restsdk/userRoots/'
        #Set count
        self.MaxCount = 4
        #Set first network , second network environment
        self.firstEnv = self.ssid_5G
        self.firstPW = self.ssid_5G_password
        self.secondEnv = self.ssid_2G
        self.secondPW = self.ssid_2G_password
        

    def before_test(self):
        # do reboot
        self.timeout = 60*5
        self.uut_owner.reboot_device()
        # Wait for reboot.
        self.log.info('Expect device do reboot in {} secs...'.format(self.timeout))
        if not self.adb.wait_for_device_to_shutdown(timeout=self.timeout):
            self.log.error('Reboot device: FAILED.')
            raise self.err.TestFailure('Reboot device failed')
        # Wait for boot up.
        self.log.info('Wait for device boot completed...')
        if not self.adb.wait_for_device_boot_completed(timeout=self.timeout):
            self.log.error('Device seems down.')
            raise self.err.TestFailure('Device seems down, device boot not completed')
        self.log.info('Device reboot completed.')
        #Check 2.4G & 5G ap device
        self.log.info('Change wifi and Verify: Check 2.4G and 5G ap device')
        self.check_wifi_AP(timeout=300, filter_keyword=self.firstEnv)
        self.check_wifi_AP(timeout=300, filter_keyword=self.secondEnv)

    def test(self):
        self.log.info('Change wifi and Verify: Upload files in First environment')
        #Connect First ap device
        self.serial_client.setup_and_connect_WiFi(ssid=self.firstEnv, password=self.firstPW, restart_wifi=True)
        #Check First ap connection
        wifi_list_1 = self.serial_client.list_network(filter_keyword=self.firstEnv)
        if not wifi_list_1:
            self.log.error('Change wifi and Verify: Connect to {} AP fail !!'.format(self.firstEnv))
            raise self.err.TestFailure('Change wifi and Verify: Connect to First AP fail')
        self.log.info('Change wifi and Verify: Network Settings => {}'.format(self.serial_client.list_network()))

        #Upload files and check
        self.verify_upload_files()

        self.log.info('Change wifi and Verify: Upload files in Second environment')
        #Connect Second ap device
        self.serial_client.setup_and_connect_WiFi(ssid=self.secondEnv, password=self.secondPW, restart_wifi=True)
        #Check Second connection
        wifi_list_2 = self.serial_client.list_network(filter_keyword=self.secondEnv)
        if not wifi_list_2:
            self.log.error('Change wifi and Verify: Connect to {} AP fail !!'.format(self.secondEnv))
            raise self.err.TestFailure('Change wifi and Verify: Connect to Second AP fail')
        self.log.info('Change wifi and Verify: Network Settings => {}'.format(self.serial_client.list_network()))

        #Upload files and check
        self.verify_upload_files()

        #End the main function

    def after_test(self):
        #Connect to Original network
        self.log.info('Change wifi and Verify: do recover network')
        self.serial_client.setup_and_connect_WiFi(ssid=self.env.ap_ssid, password=self.env.ap_password, restart_wifi=True)
        self.log.info('Change wifi and Verify: Network Settings => {}'.format(self.serial_client.list_network()))

    def verify_upload_files(self):
        #Create file
        self.log.info('Change wifi and Verify: User new id => {}'.format(self.user_new_id))
        for i in range(self.MaxCount):
            self.test_file = self.user_new_id + "_" + str(i)
            self._create_random_file(self.test_file)

            checksum_original = self._md5_checksum(file_path='local')
            self._delete_remote_file()
            self._upload_data()

            checksum_upload = self._md5_checksum(file_path='remote')
            self.log.info('Change wifi and Verify: Local file md5:({0}) Remote file md5:({1})'.format(checksum_original, checksum_upload))

            if checksum_upload != checksum_original:
                self.log.error('Change wifi and Verify: user({0}) -> md5checksum of test_file({1}) failed after uploading to DUT!'.format(self.env.username, self.test_file))
                self._delete_all_file()
                raise self.err.TestFailure('Change wifi and Verify: File md5 checksum fail')
            #Delete local and remote file
            self._delete_all_file()

    def check_wifi_AP(self, timeout, filter_keyword=None):
        start = time.time()
        self.serial_client.scan_wifi_ap()
        wifi_scan = self.serial_client.list_wifi_ap(filter_keyword)
        while not wifi_scan:
            if time.time() - start > timeout:
                raise self.err.TestSkipped('Change wifi and Verify: Wi-Fi {} AP is not ready, Skipped the test'.format(filter_keyword))
            self.serial_client.scan_wifi_ap()
            wifi_scan = self.serial_client.list_wifi_ap(filter_keyword)
            time.sleep(1)

    def _create_random_file(self, file_name, local_path='', file_size='20971520'):
        # Default 20MB dummy file
        self.log.info('Change wifi and Verify: Creating file: {}'.format(file_name))

        if os.path.isfile(self.test_file):
            self.log.info('Change wifi and Verify: Local file {} exist, delete it'.format(file_name))
            os.remove(self.test_file)
        try:
            with open(os.path.join(local_path, file_name), 'wb') as f:
                f.write(os.urandom(int(file_size)))
        except Exception as e:
            raise self.err.TestFailure('Change wifi and Verify: Failed to create file: {0}, error message: {1}'.format(file_name, repr(e)))

    def _md5_checksum(self, file_path=None):
        if file_path == 'local':
            process = subprocess.Popen('md5sum {}'.format(self.test_file), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            stdout = process.communicate()[0]
            return stdout.split()[0]
        elif file_path == 'remote':
            file_path = os.path.join(self.root_folder, "'{}'".format(self.user_id))
            result = self.adb.executeShellCommand('md5sum {0}/{1}'.format(file_path, self.test_file), timeout=600)
            if 'No such file or directory' in result[0]:
                self.log.error("Change wifi and Verify: {0} -> The tested file: {1}/{2} disappeared".format(self.env.username, file_path, self.test_file))
                return ""
            else:
                result = result[0].strip().split()[0]
                return result

    def _delete_remote_file(self):
        try:
            if self.adb.check_file_exist_in_nas("{}".format(self.test_file), self.user_id.replace('auth0|', 'auth0\|')):
                self.log.info("Change wifi and Verify: {} exist in NAS, delete it".format(self.test_file))
                data_id = self.REST_API.get_data_id_list(type='file', data_name=self.test_file)
                self.REST_API.delete_file(data_id)
            else:
                self.log.info("Change wifi and Verify: {} doesn't exist in NAS".format(self.test_file))
        except:
            pass

    def _delete_all_file(self):
        if os.path.isfile(self.test_file):
            os.remove(self.test_file)
        self._delete_remote_file()

    def _upload_data(self):
        try:
            with open(self.test_file, 'rb') as f:
                read_data = f.read()
                self.log.info("Change wifi and Verify: {0} -> Uploading file to test device".format(self.env.username))
                self.REST_API.upload_data(data_name=self.test_file, file_content=read_data, suffix=self.test_file, cleanup=True)
        except Exception as e:
            self.log.error("Change wifi and Verify: {0} -> _upload_data({1}):{2}".format(self.env.username, self.test_file, repr(e)))
            raise self.err.TestFailure('Change wifi and Verify: Upload file fail')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** change wifi and verify ***
        Examples: ./run.sh functional_tests/wifi_change_verify.py --uut_ip 10.92.224.68 \
        """)
    # Test Arguments
    parser.add_argument('--wifi_ssid_5g', help="", default='integration_5G')
    parser.add_argument('--wifi_ssid_2g', help="", default='integration_2.4G')
    parser.add_argument('--wifi_5g_password', help="", default='automation')
    parser.add_argument('--wifi_2g_password', help="", default='automation')

    test = WifiChange5GVerify(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
