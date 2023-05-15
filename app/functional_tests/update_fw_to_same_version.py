# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import os
from subprocess import check_output
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from bat_scripts_new.fw_update_utility import FWUpdateUtility

class UpdateFWToSameVersion(FWUpdateUtility):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'update_fw_to_same_version'
    # Popcorn
    TEST_JIRA_ID = 'KAM-7138'
    SETTINGS = {'uut_owner':True, 'power_switch': False}


    def init(self):

        self.fw_temp = self.adb.getFirmwareVersion()
        stdout, stderr = self.adb.executeShellCommand('cat /etc/restsdk-server.toml | grep "configURL"')
        self.env_temp = stdout.strip()
        stdout, stderr = self.adb.executeShellCommand('getprop | grep ro.build.type')
        self.variant_temp = stdout.strip()


    def before_test(self):
        self._create_random_file('testfile_before_fwupdate')
        with open ('testfile_before_fwupdate', 'r') as f:
            self.uut_owner.upload_data('testfile_before_fwupdate', file_content=f.read(), cleanup=True)
        self.user_id = self.uut_owner.get_user_id(escape=True)
        self.checksum_dict_before = self.adb.MD5_checksum(self.user_id, "")



    def test(self):
        # Update firmware
        super(UpdateFWToSameVersion, self).init()
        super(UpdateFWToSameVersion, self).before_test()    
        super(UpdateFWToSameVersion, self).test()
  
        self._fw_compare(fw_temp=self.fw_temp, env_temp=self.env_temp, variant_temp=self.variant_temp)

        # Check checksum before and after updating fw.
        self.checksum_dict_after = self.adb.MD5_checksum(self.user_id, "")
        if self.checksum_dict_before != self.checksum_dict_after:
            raise self.err.TestFailure('checksum is different between before and after updating fw. {0} vs {1}'.format(self.checksum_dict_before, self.checksum_dict_after))

        # Check if DB is locked
        db_lock = self.adb.executeShellCommand("logcat -d | grep 'database table is locked'")[0]
        self.log.debug(db_lock)
        if db_lock:
            raise self.err.TestFailure('OTA stress test failed! Find database locked messages in logcat!')

        # Test if the file can be uploaded to NAS after updating fw 
        self._create_random_file('testfile_after_fwupdate')
        temp = check_output('md5sum testfile_after_fwupdate', shell=True)
        checksum_local = temp.split()[0]
        with open ('testfile_after_fwupdate', 'r') as f:
            self.uut_owner.upload_data('testfile_after_fwupdate', file_content=f.read(), cleanup=True)
        checksum_NAS = self.adb.MD5_checksum(self.user_id, "").get('testfile_after_fwupdate')
        if checksum_local != checksum_NAS:
            raise self.err.TestFailure('After updating fw, re-upload testfile by REST API. But the checksum is different between local and NAS. {0} vs {1}'.format(checksum_local, checksum_NAS))

        # Delete testing file
        self._delete_testing_file('testfile_before_fwupdate')
        self._delete_testing_file('testfile_after_fwupdate')

        # Add keyword 'pass' to the result that will be uploaded to logstash
        self.data.test_result['result'] = 'pass'  


    def _delete_testing_file(self, file_name):
        try:
            file_info, search_time = self.uut_owner.search_file_by_parent_and_name(parent_id='root', name=file_name)       
            result, delete_time = self.uut_owner.delete_file(file_info['id'])
        except Exception as e:
            if 'Not Found' in str(e):
                pass
            else:
                raise


    def _create_random_file(self, file_name, file_size='10485760'):
        # Default 10MB dummy file
        self.log.info('Creating file: {}'.format(file_name))
        try:
            with open(file_name, 'wb') as f:
                f.write(os.urandom(int(file_size)))
        except Exception as e:
            self.log.error('Failed to create file: {0}, error message: {1}'.format(file_name, repr(e)))
            raise


    def _fw_compare(self, fw_temp=None, env_temp=None, variant_temp=None):
        temp = self.adb.getFirmwareVersion()
        if fw_temp != temp:
            raise self.err.TestFailure('fw version comparison failed: {0} vs {1}'.format(fw_temp, temp))
        stdout, stderr = self.adb.executeShellCommand('cat /etc/restsdk-server.toml | grep "configURL"')
        if env_temp != stdout.strip():
            raise self.err.TestFailure('environment comparison failed: {0} vs {1}'.format(env_temp, stdout.strip()))
        stdout, stderr = self.adb.executeShellCommand('getprop | grep ro.build.type')
        if variant_temp != stdout.strip():
            raise self.err.TestFailure('variant comparison failed: {0} vs {1}'.format(variant_temp, stdout.strip()))

    def get_serial_led(self):
        return self.led_state

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/update_fw_to_same_version.py --uut_ip 10.92.224.61 --dry_run --debug_middleware --local_image\
        """)
    parser.add_argument('--file_server', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    #parser.add_argument('--ota_timeout', help='The maximum ota timeout value', type=int, default=3600)
    #parser.add_argument('--keep_fw_img', action='store_true', default=True, help='Keep downloaded firmware')

    test = UpdateFWToSameVersion(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)