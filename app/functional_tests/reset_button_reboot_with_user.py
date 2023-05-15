# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import os
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.constants import Kamino


class ResetButtonRebootWithUser(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KAM-25754: MCH - Press Reset Button 1~29 secs : Device reboot - with user associated'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-25754'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {'uut_owner':True}


    def declare(self):
        self.TEST_FILE = 'DummyFileForRWCheck_KAM25754'


    def before_loop(self):
        pass


    def before_test(self):
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

        # Create dummy file used for upload/download and calculate checksum
        _create_random_file(self.TEST_FILE)
        LOCAL_DUMMY_MD5 = _local_md5_checksum(self.TEST_FILE)
        if not LOCAL_DUMMY_MD5:
            raise self.err.TestFailure('Failed to get the local dummy md5 checksum!')
        self.log.warning("Local dummyfile MD5 Checksum: {}".format(LOCAL_DUMMY_MD5))

        # Delete existing dummy file before upload new dummy file
        try:
            self.uut_owner.delete_file_by_name(self.TEST_FILE)
        except RuntimeError as ex:
            if 'Not Found' in str(ex):
                self.log.info('No dummy file exist, skip delete file step! Message: {}'.format(ex))
            else:
                raise self.err.TestFailure('Delete dummy file failed! Message: {}'.format(ex))

        self.log.info('Try to upload a dummy file by device owner.....')
        with open(self.TEST_FILE, 'rb') as f:
            self.uut_owner.chuck_upload_file(file_object=f, file_name=self.TEST_FILE)
            
        user_id = self.uut_owner.get_user_id(escape=True)
        nas_md5 = self.adb.executeShellCommand('busybox md5sum /data/wd/diskVolume0/restsdk/userRoots/{0}/{1}'.
                                                format(user_id, self.TEST_FILE), timeout=300, consoleOutput=False)[0].split()[0]
        self.log.warning("NAS MD5 Checksum: {}".format(nas_md5))

        if LOCAL_DUMMY_MD5 != nas_md5:
            raise self.err.TestFailure('After device rebooted and upload a dummyfile to device, MD5 checksum comparison failed!')

        # Preserve the value of LOCAL_DUMMY_MD5
        self.LOCAL_DUMMY_MD5 = LOCAL_DUMMY_MD5


    def test(self):

        user_number_before_reboot = self._check_user_root()

        # "reset_button.sh short" is equal to pressing reset_button for 1~29 seconds.
        stdout, stderr = self.adb.executeShellCommand('busybox nohup reset_button.sh short', timeout=120)
        self.log.info('Expect device do rebooting ...')
        if not self.adb.wait_for_device_to_shutdown():
            raise self.err.TestFailure('Device rebooting Failed !!')
        self.log.info('Device rebooting ...')
        if not self.adb.wait_for_device_boot_completed():
            raise self.err.TestFailure('Device bootup Failed !!')

        # Sometimes the userRoots is not mounted yet even if getprop sys.wd.disk.mounted=1.
        # Add sleep 20 seconds before check userRoots
        time.sleep(20)
        self._check_user_root(user_number_expected=user_number_before_reboot, err_msg='The number of users is different before and after rebooting.')

        self.test_file_check_after_reboot()


    def _check_user_root(self, user_number_expected=None, err_msg=None):
        stdout, stderr = self.adb.executeShellCommand('ls -al {} | wc -l'.format(Kamino.USER_ROOT_PATH))
        if type(user_number_expected) == int:
            if int(stdout.strip()) != user_number_expected:
                stdout, stderr = self.adb.executeShellCommand('df')
                raise self.err.TestFailure(err_msg)
        return int(stdout.strip())


    def test_file_check_after_reboot(self):
        self.log.info('Try to download the dummy file.....')
        result, elapsed = self.uut_owner.search_file_by_parent_and_name(name=self.TEST_FILE, parent_id='root')
        file_id = result['id']
        content = self.uut_owner.get_file_content_v3(file_id).content
        with open('{}_download'.format(self.TEST_FILE), 'wb') as f:
            f.write(content)

        response = os.popen('md5sum {}_download'.format(self.TEST_FILE))
        if response:
            download_md5 = response.read().strip().split()[0]
        else:
            raise self.err.TestFailure("Failed to get local dummy file md5 after downloaded from test device!")

        self.log.warning("Downloaded file MD5 Checksum: {}".format(download_md5))

        if self.LOCAL_DUMMY_MD5 != download_md5:
            raise self.err.TestFailure("After device rebooted and download a dummyfile from device, MD5 checksum comparison failed!")

        self.log.info("Cleanup the dummyfiles")
        self.uut_owner.delete_file(file_id)
        os.remove('{}_download'.format(self.TEST_FILE))


    def after_test(self):
        pass


    def after_loop(self):
        pass


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/reset_button_reboot_without_user.py --uut_ip 10.0.0.28 --cloud_env qa1 --dry_run --debug_middleware\
         --disable_clean_logcat_log """)

    test = ResetButtonRebootWithUser(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)