# -*- coding: utf-8 -*-
""" Test cases to validates dB migrations.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import os
import shutil
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from bat_scripts.fwUpdateUtility import fwUpdateUtility
from platform_libraries.restAPI import RestAPI


class DBMigration(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'DB_Migration_Test'

    def init(self):
        if not self.startfw:
            self.startfw = '4.0.1-611'
        self.timeout = 7200
        self.user = self.uut_owner
        self.FILE_SERVER_PATH = '/test/IOStress'
        self.LOCAL_UPLOAD_FOLDER = os.path.join(os.getcwd(), 'upload_folder')
        self.FILE_LIST = []

    def before_test(self):
        self.log.info('Update starting firmware if needed..')
        currfw = self.adb.getFirmwareVersion()
        if currfw != self.startfw:
            self.log.warning('Current firmware version is {}, start to update starting firmware...'.format(currfw))
            updatefw = fwUpdateUtility(adb=self.adb, version=self.startfw, env=self.env.cloud_env, noreset=False,
                                       variant=self.env.cloud_variant, local_image=self.local_image, file_server_ip=self.file_server)
            updatefw.run()
            self.timing.reset_start_time()
            while not self.timing.is_timeout(60):
                curl_localHost = self.adb.executeShellCommand('curl localhost/sdk/v1/device', timeout=10)[0]
                time.sleep(1)
                if 'Connection refused' not in curl_localHost:
                    self.log.info("Successfully connected to localhost")
                    break
            time.sleep(30)
            try:
                self.user = RestAPI(self.env.uut_ip, self.env.cloud_env, self.env.username, self.env.password)
            except:
                self.log.exception('Exception occurred during import RestAPI, try again..')
                time.sleep(30)
                self.user = RestAPI(self.env.uut_ip, self.env.cloud_env, self.env.username, self.env.password)
        # self.adb.stop_otaclient()

    def test(self):
        self.log.info('*****Start to run DB migration test*****')
        self.log.info('Upload media files')
        self.upload_data()
        if self.dofactoryreset:
            self.do_factory_reset()
        updatefw = fwUpdateUtility(adb=self.adb, version=self.testfw, env=self.env.cloud_env, noreset=True,
                                   variant=self.env.cloud_variant, local_image=self.local_image, file_server_ip=self.file_server)
        updatefw.run()

        # Check DB migration Start
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60*3):
            migration = self.adb.executeShellCommand("logcat -d | grep 'begin migration'")[0]
            if 'begin migration' in migration:
                self.log.info('DB migration started')
                break
        if self.timing.is_timeout(60*3):
            raise self.err.TestFailure('begin migration not started, failed the case')

        # Check DB migration finished
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60*5):
            migrated = self.adb.executeShellCommand('logcat -d | grep "migrated"')[0]
            if 'migrated' in migrated:
                self.log.info('DB migration finished')
                break
            time.sleep(2)
        if self.timing.is_timeout(60*5):
            raise self.err.TestFailure('DB migration not finished, timeout for 5 minutes')

    def after_test(self):
        self.log.info('Run after_test step......')
        self.log.info('Clean up the test environment')
        self.log.info('Removing local folders')
        if os.path.exists(self.LOCAL_UPLOAD_FOLDER):
            shutil.rmtree(self.LOCAL_UPLOAD_FOLDER)
        self.log.info('Removing DUT test files')
        self.user.clean_user_root()
        self.adb.start_otaclient()

    def upload_data(self):
        self.log.info("Create upload folder")
        if os.path.exists(self.LOCAL_UPLOAD_FOLDER):
            shutil.rmtree(self.LOCAL_UPLOAD_FOLDER)
        os.mkdir(self.LOCAL_UPLOAD_FOLDER)
        self.log.info("Download test files from file server to upload folder")
        download_path = '{0}{1}'.format('ftp://ftp:ftppw@{}'.format(self.file_server), self.FILE_SERVER_PATH)
        cur_dir = self.FILE_SERVER_PATH.count('/')
        url = 'wget --no-host-directories --cut-dirs={0} -r {1} -P {2}'.format(cur_dir, download_path, self.LOCAL_UPLOAD_FOLDER)
        os.popen(url)

        for (dirpath, dirnames, filenames) in os.walk(self.LOCAL_UPLOAD_FOLDER):
            self.FILE_LIST.extend(filenames)
            break

        self.log.info('Local test folders are ready')
        self.log.info('Upload test files to device')
        for index, file in enumerate(self.FILE_LIST):
            with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file), 'rb') as f:
                self.log.info('Uploading file: {0} to device.'.format(file))
                read_data = f.read()
                self.user.upload_data(data_name=file, file_content=read_data,
                                      parent_folder=None, suffix=index, cleanup=True)
        self.log.info('Upload files finished')

    def do_factory_reset(self):
        # Factory reset
        self.timing.reset_start_time()
        self.adb.executeShellCommand('busybox nohup factory_reset.sh')
        self.log.info('Expect device do reboot in {}s.'.format(self.timeout))
        if not self.adb.wait_for_device_to_shutdown(timeout=self.timeout):
            self.log.error('Reboot device: FAILED. Device not shutdown.')
            raise self.err.TestFailure('Reboot device failed. Device not shutdown.')
        self.log.info('Wait for device boot completed...')
        if not self.adb.wait_for_device_boot_completed(timeout=self.timeout):
            self.log.error('Device seems down.')
            raise self.err.TestFailure('Device seems down, device boot not completed')
        self.log.info('Factory Reset is finished.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** DB migration Test ***
        Examples: ./run.sh functional_tests/db_migration.py --uut_ip 10.92.224.68 --startfw 4.0.1-611 --testfw 4.1.0-716\
        """)
    # Test Arguments
    parser.add_argument('--testfw', help='Update test firmware version, ex. 4.1.0-716')
    parser.add_argument('--startfw', help='Start firmware version, ex. 4.0.1-611')
    parser.add_argument('--file_server', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('-dfr', '--dofactoryreset', help='Do factory Reset', action='store_true', default=None)
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')

    test = DBMigration(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
