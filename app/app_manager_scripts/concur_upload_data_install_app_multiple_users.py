# -*- coding: utf-8 -*-
""" Test case to install app while upload data is running in parallel - multiple users
    https://jira.wdmv.wdc.com/browse/KAM-32861
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import os
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.install_app import InstallApp
from platform_libraries.test_thread import MultipleThreadExecutor


class ConcurrentInstallSameAppDuringUploadDataMultipleUsers(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32861 - Install app while upload data is running in parallel with multiple users'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32861'
    PRIORITY = 'Critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.file_server_ip = 'fileserver.hgst.com'
        self.dir_in_file_server = '/test/IOStress'
        self.check_app_install = False
        self.app_id = None

    def init(self):
        env_dict = self.env.dump_to_dict()
        env_dict.pop('_testcase')
        env_dict['Settings'] = ['serial_client=False']
        
        # For admin user import
        env_dict['app_id'] = self.app_id
        env_dict['check_app_install'] = self.check_app_install
        self.install_app = InstallApp(env_dict)
        # For Second user import
        replace_username = self.env.username.rsplit('@')[0]
        username = self.env.username.replace(replace_username, replace_username + '+1')
        self.log.info("Second user email = '{}'".format(username))
        env_dict['username'] = username
        self.install_app1 = InstallApp(env_dict)

        # Upload data init
        self.LOCAL_UPLOAD_FOLDER = os.path.join(os.getcwd(), '{}'.format(self.dir_in_file_server.split('/')[-1]))
        self.FILE_LIST = []

    def before_test(self):
        self.install_app.before_test()
        self.install_app1.before_test()

        self.log.info('Start to cleanup owners folder data before start the test ...')
        self.install_app.uut_owner.clean_user_root()
        self.install_app1.uut_owner.clean_user_root()
        # Upload folder prepare
        self.log.info('Download more than 100 image files from file server to {}...'.format(self.LOCAL_UPLOAD_FOLDER))
        download_path = '{0}{1}'.format('http://{}/'.format(self.file_server_ip), self.dir_in_file_server)
        cur_dir = self.dir_in_file_server.count('/')
        cmd = "wget -q -N -nH --no-parent --reject='index.html*' --no-host-directories --cut-dirs={0} -r {1}/".format(cur_dir, download_path)
        self.log.info("Download files from server:'{0}'".format(download_path))
        self.log.info('Execute command: {}'.format(cmd))
        os.popen(cmd)
        self.log.info('Download successfully.')
        for (dirpath, dirnames, filenames) in os.walk(self.LOCAL_UPLOAD_FOLDER):
            self.FILE_LIST.extend(filenames)
            break
        self.log.info('DATA_SIZE={}'.format(len(self.FILE_LIST)))
        self.log.info('Local upload test folders are ready')

    def test(self):
        self.log.info('Start to install app({}) by admin user and second user at the same time'
            .format(self.app_id))
        self.concurrent_install_app()
        self.log.info("*** Install same app while upload data is running in parallel with multiple users, Test PASSED !!!")

    def concurrent_install_app(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.install_app.test)
        mte.append_thread_by_func(target=self.install_app1.test)
        mte.append_thread_by_func(target=self.upload_data_admin_user)
        mte.append_thread_by_func(target=self.upload_data_second_user)
        mte.run_threads()

    def upload_data_admin_user(self):
        self.log.info('Start to upload test files to device ...')
        for index, file in enumerate(self.FILE_LIST):
            with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file), 'rb') as f:
                self.log.info('Uploading file: {0} to device.'.format(file))
                self.install_app.uut_owner.chuck_upload_file(file_object=f, file_name=file)
        self.log.info('Admin user upload files finished')

    def upload_data_second_user(self):
        self.log.info('Start to upload test files to device ...')
        for index, file in enumerate(self.FILE_LIST):
            with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file), 'rb') as f:
                self.log.info('Uploading file: {0} to device.'.format(file))
                self.install_app1.uut_owner.chuck_upload_file(file_object=f, file_name=file)
        self.log.info('Second user upload files finished')

    def after_test(self):
        self.install_app.uninstall_app = True
        self.install_app.after_test()
        self.install_app1.uninstall_app = True
        self.install_app1.after_test()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Install app while upload data is running in parallel with multiple users Test Script ***
        Examples: ./start.sh app_manager_scripts/concur_upload_data_install_app_multiple_users.py -ip 10.92.234.16 -env qa1
        --app_id com.wdc.importapp.ibi
        """)

    parser.add_argument('--file_server_ip', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--dir_in_file_server', help='The data set dir in file server', default='/test/IOStress')
    parser.add_argument('-appid', '--app_id', help='First App ID to installed')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    
    test = ConcurrentInstallSameAppDuringUploadDataMultipleUsers(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)