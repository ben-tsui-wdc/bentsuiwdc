# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import sys
# platform modules
from platform_libraries import common_utils
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class upload_fw_to_file_server(TestCase):
    TEST_SUITE = 'jenkins_scripts'
    TEST_NAME = 'upload_fw_to_file_server'

    SETTINGS = { # Disable all utilities.
        'disable_firmware_consistency': True,
        'adb': False, # Disable ADB and ignore any relevant input argument.
        'power_switch': False, # Disable Power Switch.
        'uut_owner' : False # Disable restAPI.
    }
        
    def init(self):
        self.env.disable_popcorn_report = True

    def test(self):
        if 800 > int(self.env.firmware_version.split('-')[0].replace('.', '')): # Old build
            if self.env.cloud_env == 'qa1' or self.env.cloud_env == 'prod':
                variant = 'user'
            else:
                variant = 'userdebug'

            result, msg = common_utils.upload_fw_to_server(model=self.env.model, fw=self.env.firmware_version, env=self.env.cloud_env, variant=variant, data_type=self.data_type, ftp_username=self.ftp_username, ftp_password=self.ftp_password, ftp_file_path=self.ftp_file_path, retry=3)
            if not result:  # result is a Boolean
                raise self.err.TestFailure(msg)

            result, msg = common_utils.upload_fw_to_server(model=self.env.model, fw=self.env.firmware_version, env=self.env.cloud_env, variant=variant, data_type='os', ftp_username=self.ftp_username, ftp_password=self.ftp_password, ftp_file_path=self.ftp_file_path, retry=3)
            if not result:  # result is a Boolean
                raise self.err.TestFailure(msg)

            result, msg = common_utils.upload_fw_to_server(model=self.env.model, fw=self.env.firmware_version, env=self.env.cloud_env, variant=variant, data_type='uboot', ftp_username=self.ftp_username, ftp_password=self.ftp_password, ftp_file_path=self.ftp_file_path, retry=3)
            if not result:  # result is a Boolean
                raise self.err.TestFailure(msg)

            # Because only debug build will upload log to Sumologic, download "user" and "userdebug" both for qa1
            if self.env.cloud_env == 'qa1':
                variant = 'userdebug'

                result, msg = common_utils.upload_fw_to_server(model=self.env.model, fw=self.env.firmware_version, env=self.env.cloud_env, variant=variant, data_type='ota', ftp_username=self.ftp_username, ftp_password=self.ftp_password, ftp_file_path=self.ftp_file_path, retry=3)
                if not result:  # result is a Boolean
                    raise self.err.TestFailure(msg)

                result, msg = common_utils.upload_fw_to_server(model=self.env.model, fw=self.env.firmware_version, env=self.env.cloud_env, variant=variant, data_type='os', ftp_username=self.ftp_username, ftp_password=self.ftp_password, ftp_file_path=self.ftp_file_path, retry=3)
                if not result:  # result is a Boolean
                    raise self.err.TestFailure(msg)
        else: # KDP
            result, msg = common_utils.upload_kdp_fw_to_server(model=self.env.model, fw=self.env.firmware_version, env=self.env.cloud_env, ver=self.tool_ver, data_type=self.data_type, ftp_username=self.ftp_username, ftp_password=self.ftp_password, ftp_file_path=self.ftp_file_path, retry=3)
            if not result:  # result is a Boolean
                raise self.err.TestFailure(msg)

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** upload_fw_to_file_server ***
        Examples: ./run.sh ./jenkins_scripts/upload_fw_to_file_server.py -model monarch -fw 4.1.0-724 --cloud_env dev1 -debug --dry_run\
        """)

    parser.add_argument('--data_type', help='the firmware installer type', default='ota')
    parser.add_argument('--tool_ver', help='the install tool version', default=None)
    parser.add_argument('--ftp_username', help='the username to login to ftp server', default='ftp')
    parser.add_argument('--ftp_password', help='the ftp_password to login to ftp server', default='ftppw')
    parser.add_argument('--ftp_file_path', help='where the fw will be uploaded to', default='fileserver.hgst.com/firmware')

    test = upload_fw_to_file_server(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)