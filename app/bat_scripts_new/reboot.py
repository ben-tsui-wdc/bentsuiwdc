# -*- coding: utf-8 -*-
""" Test cases to test device reboot (send request by restAPI).
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
import os

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class Reboot(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Device Reboot Test'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13971, KAM-27550,KAM-14131'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'Single_run'

    def declare(self):
        self.wait_device = True
        self.no_rest_api = True
        self.disable_ota = False
        self.no_read_write_check = False
        self.check_ota_image_path = True

    def init(self):
        self.timeout = 60*30

    def test(self):
        if not self.no_rest_api:
            self.log.info('Start to use REST API to reboot device.')
            self.deviceid_before = self.uut_owner.get_local_code_and_security_code()[0]
            self.log.info('Print out Device ID before reboot: {}'.format(self.deviceid_before))
            try:
                self.uut_owner.reboot_device()
                self.log.info('Device rebooting..')
            except:
                raise self.err.TestFailure('Reboot device via restapi failed!!')
        else:
            self.log.info('Use ADB command to reboot device.')
            self.adb.executeShellCommand('busybox nohup reboot')

        self.log.info('Expect device do reboot in {}s.'.format(self.timeout))
        if not self.adb.wait_for_device_to_shutdown(timeout=self.timeout):
            self.log.error('Reboot device: FAILED.')
            raise self.err.TestFailure('Reboot device failed')
        self.log.info('Reboot device: PASSED.')
        try:
            if self.wait_device:
                self.log.info('Wait for device boot completede...')
                if not self.adb.wait_for_device_boot_completed(timeout=self.timeout, disable_ota=self.disable_ota):
                    self.log.error('Device seems down.')
                    raise self.err.TestFailure('Timeout({}secs) to wait device boot completed..'.format(self.timeout))
        except Exception as ex:
            self.log.exception('Exception occurred during waiting. Err: {}'.format(ex))
        time.sleep(10)
        self.check_restsdk_service()
        self.check_ota_download_path()
        if not self.no_read_write_check:
            if getattr(self, 'uut_owner', False):
                self.read_write_check_after_reboot()
        if not self.no_rest_api:
            self.check_device_id_after_reboot()
            self.uut_owner.wait_until_cloud_connected(timeout=60*3)

    def read_write_check_after_reboot(self):
        def _local_md5_checksum(path):
            # Only use when the data set is downloaded from file server
            response = os.popen('md5sum {}'.format(path))
            if response:
                result = response.read().strip().split()[0]
                return result
            else:
                self.log.error("There's no response from md5 checksum")
                return None
        
        def _create_random_file(file_name, local_path='', file_size='1048576'):
            # Default 1MB dummy file
            self.log.info('Creating file: {}'.format(file_name))
            try:
                with open(os.path.join(local_path, file_name), 'wb') as f:
                    f.write(os.urandom(int(file_size)))
            except Exception as e:
                self.log.error('Failed to create file: {0}, error message: {1}'.format(local_path, repr(e)))
                raise
        
        TEST_FILE = 'DummyFileForRWCheck'

        # Create dummy file used for upload/download and calculate checksum
        _create_random_file(TEST_FILE)
        LOCAL_DUMMY_MD5 = _local_md5_checksum(TEST_FILE)
        if not LOCAL_DUMMY_MD5:
            raise self.err.TestFailure('Failed to get the local dummy md5 checksum!')
        self.log.warning("Local dummyfile MD5 Checksum: {}".format(LOCAL_DUMMY_MD5))

        # Delete existing dummy file before upload new dummy file
        try:
            self.uut_owner.delete_file_by_name(TEST_FILE)
        except RuntimeError as ex:
            if 'Not Found' in str(ex):
                self.log.info('No dummy file exist, skip delete file step! Message: {}'.format(ex))
            else:
                raise self.err.TestFailure('Delete dummy file failed! Message: {}'.format(ex))

        self.log.info('Try to upload a dummy file by device owner.....')
        with open(TEST_FILE, 'rb') as f:
            self.uut_owner.chuck_upload_file(file_object=f, file_name=TEST_FILE)
            
        user_id = self.uut_owner.get_user_id(escape=True)
        nas_md5 = self.adb.executeShellCommand('busybox md5sum /data/wd/diskVolume0/restsdk/userRoots/{0}/{1}'.
                                                format(user_id, TEST_FILE), timeout=300, consoleOutput=False)[0].split()[0]
        self.log.warning("NAS MD5 Checksum: {}".format(nas_md5))

        if LOCAL_DUMMY_MD5 != nas_md5:
            raise self.err.TestFailure('After device rebooted and upload a dummyfile to device, MD5 checksum comparison failed!')
        
        self.log.info('Try to download the dummy file.....')
        result, elapsed = self.uut_owner.search_file_by_parent_and_name(name=TEST_FILE, parent_id='root')
        file_id = result['id']
        content = self.uut_owner.get_file_content_v3(file_id).content
        with open('{}_download'.format(TEST_FILE), 'wb') as f:
            f.write(content)

        response = os.popen('md5sum {}_download'.format(TEST_FILE))
        if response:
            download_md5 = response.read().strip().split()[0]
        else:
            raise self.err.TestFailure("Failed to get local dummy file md5 after downloaded from test device!")

        self.log.warning("Downloaded file MD5 Checksum: {}".format(download_md5))

        if LOCAL_DUMMY_MD5 != download_md5:
            raise self.err.TestFailure("After device rebooted and download a dummyfile from device, MD5 checksum comparison failed!")

        self.log.info("Cleanup the dummyfiles")
        self.uut_owner.delete_file(file_id)
        os.remove('{}_download'.format(TEST_FILE))

    def check_device_id_after_reboot(self):
        self.deviceid_after = self.uut_owner.get_local_code_and_security_code()[0]
        self.log.info('Print out Device ID after reboot: {}'.format(self.deviceid_after))
        if self.deviceid_before == self.deviceid_after:
            self.log.info('Device ID is match.')
        else:
            raise self.err.TestFailure('Device ID is not match, reboot test failed !!!')

    def check_restsdk_service(self):
        self.start = time.time()
        while not self.is_timeout(60*3):
            # Execute command to check restsdk is running
            grepRest = self.adb.executeShellCommand('ps | grep restsdk')[0]
            if 'restsdk-server' in grepRest:
                self.log.info('Restsdk-server is running\n')
                break
            time.sleep(3)
        else:
            raise self.err.TestFailure("Restsdk-server is not running after wait for 3 mins")

        # Sometimes following error occurred if making REST call immediately after restsdk is running.
        # ("stdout: curl: (7) Failed to connect to localhost port 80: Connection refused)
        # Add retry mechanism for get device info check
        self.start = time.time()
        while not self.is_timeout(60*2):
            # Execute sdk/v1/device command to check device info to confirm restsdk service running properly
            curl_localHost = self.adb.executeShellCommand('curl localhost/sdk/v1/device?pretty=true')[0]
            if 'Connection refused' in curl_localHost:
                self.log.warning('Connection refused happened, wait for 5 secs and try again...')
                time.sleep(5)
            else:
                break
        else:
            raise self.err.TestFailure("Connected to localhost failed after retry for 2 mins ...")

    def check_ota_download_path(self):
        check_path = self.adb.executeShellCommand('logcat -d -s otaclient | grep ota_start')[0]
        if '/tmp/otaclient/fwupdate' not in check_path:
            self.log.warning('logs: {}'.format(check_path))
            self.log.warning('ota imagePath has been changed, not original downloadDir')
            if self.check_ota_image_path:
                raise self.err.TestFailure("ota imagePath has been changed, not original downloadDir !!")

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

    def after_test(self):
        pass


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Device Reboot Script ***
        Examples: ./run.sh bat_scripts/reboot.py --uut_ip 10.92.224.68\
        """)

    parser.add_argument('-wait', '--wait_device', help='Wait for device boot completed', action='store_true')
    parser.add_argument('-noapi', '--no_rest_api', help='Not use restapi to reboot device', action='store_true')
    parser.add_argument('-disableota', '--disable_ota', help='Disabled OTA client after test', action='store_true')
    parser.add_argument('-chkotapath', '--check_ota_image_path', help='raise error if ota download path changed', action='store_true')
    parser.add_argument('-norwchk', '--no_read_write_check', help='Do not run read write check after reboot', action='store_true')

    test = Reboot(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
