# -*- coding: utf-8 -*-
""" Test case to test uninstall app while upload data is running in parallel
    https://jira.wdmv.wdc.com/browse/KAM-32499
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import os
import sys
import time
import shutil

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.uninstall_app import UninstallApp
from platform_libraries.test_thread import MultipleThreadExecutor


class UninstallAppDuringUploadData(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32499 - Uninstall app while upload data is running in parallel'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32499'
    PRIORITY = 'Critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.file_server_ip = 'fileserver.hgst.com'
        self.dir_in_file_server = '/test/IOStress'
        self.app_id = None
        self.check_pm_list = False

    def init(self):
        env_dict = self.env.dump_to_dict()
        env_dict['app_id'] = self.app_id
        env_dict['check_pm_list'] = self.check_pm_list
        self.uninstall_app = UninstallApp(env_dict)
        # Upload data init
        self.LOCAL_UPLOAD_FOLDER = os.path.join(os.getcwd(), '{}'.format(self.dir_in_file_server.split('/')[-1]))
        self.FILE_LIST = []

    def before_test(self):
        self.uninstall_app.before_test()
        self.log.info('Start to cleanup owners folder data before start the test ...')
        self.uut_owner.clean_user_root()
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
        self.concurrent_uninstall_app_w_upload_data()
        self.log.info('App({}) has been uninstalled during data uploading. Test PASSED !!!'.format(self.app_id))

    def concurrent_uninstall_app_w_upload_data(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.uninstall_app.test)
        mte.append_thread_by_func(target=self.upload_data)
        mte.run_threads()

    def upload_data(self):
        self.log.info('Start to upload test files to device ...')
        for index, file in enumerate(self.FILE_LIST):
            with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file), 'rb') as f:
                self.log.info('Uploading file: {0} to device.'.format(file))
                self.uut_owner.chuck_upload_file(file_object=f, file_name=file)
        self.log.info('Upload files finished')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Uninstall app while upload data is running in parallel Test Script ***
        Examples: ./run.sh app_manager_scripts/concur_upload_data_uninstall_app.py --uut_ip 10.92.224.68 -appid com.wdc.importapp.ibi -chkapp\
        """)

    parser.add_argument('--file_server_ip', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--dir_in_file_server', help='The data set dir in file server', default='/test/IOStress')
    parser.add_argument('-appid', '--app_id', help='App ID to uninstalled')
    parser.add_argument('-chkpl', '--check_pm_list', help='Check pm list of app package', action='store_true')

    test = UninstallAppDuringUploadData(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
