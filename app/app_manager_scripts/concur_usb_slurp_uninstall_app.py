# -*- coding: utf-8 -*-
""" Test case to test uninstall app while USB slurp is running in parallel.
    https://jira.wdmv.wdc.com/browse/KAM-32498
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import os
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.uninstall_app import UninstallApp
from platform_libraries.test_thread import MultipleThreadExecutor


class UninstallAppDuringUSBSlurp(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32498 - Uninstall app while USB slurp is running in parallel'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32498'
    PRIORITY = 'Major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.file_server_ip = 'fileserver.hgst.com'
        self.dir_in_file_server = '/test/5G_Standard/Audio1GB'
        self.download_usb_slurp_files = False
        self.delete_download_files = False
        self.app_id = None
        self.check_pm_list = False

    def init(self):
        env_dict = self.env.dump_to_dict()
        env_dict['app_id'] = self.app_id
        env_dict['check_pm_list'] = self.check_pm_list
        self.uninstall_app = UninstallApp(env_dict)

    def before_test(self):
        self.uninstall_app.before_test()
        self.log.info('Start to cleanup owners folder data before start the test ...')
        self.uut_owner.clean_user_root()
        usb_mount_path = '/mnt/media_rw'
        usb_dir = self.adb.executeShellCommand('ls {}'.format(usb_mount_path))[0].strip()
        if not usb_dir:
            raise self.err.TestSkipped('USB is not mounted, Skipped the test !')
        self.usb_dir_path = '{0}/{1}/{2}'.format(usb_mount_path, usb_dir, self.dir_in_file_server.split('/')[-1])
        self.adb.executeShellCommand('mount -o remount,rw {0}/{1}'.format(usb_mount_path, usb_dir))
        if self.download_usb_slurp_files:
            self.log.info('Download 1GB data files to USB drive from file server ...')
            download_path = '{0}{1}'.format('http://{}/'.format(self.file_server_ip), self.dir_in_file_server)
            cur_dir = self.dir_in_file_server.count('/')
            cmd = "wget -q -N -nH --no-parent --reject='index.html*' --no-host-directories --cut-dirs={0} -r {1}/".format(cur_dir, download_path)
            self.log.info("Download files from server:'{0}' to usb_folder:'{1}' and push to device usb folder ..."
                .format(download_path, self.usb_dir_path))
            self.log.info('Execute command: {}'.format(cmd))
            os.popen(cmd)
            self.log.info('Download successfully, start to adb push files ...')
            self.adb.push(local=self.dir_in_file_server.split('/')[-1], remote=self.usb_dir_path, timeout=60*30)
            self.log.info('adb push done.')

    def test(self):
        self.concurrent_uninstall_app_w_usb_slurp()
        self.log.info('App({}) has been uninstalled during USB slurp. Test PASSED !!!'.format(self.app_id))

    def concurrent_uninstall_app_w_usb_slurp(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.uninstall_app.test)
        mte.append_thread_by_func(target=self.uut_owner.usb_slurp)
        mte.run_threads()

    def after_test(self):
        if self.delete_download_files:
            self.log.info('Delete {}'.format(self.usb_dir_path))
            self.adb.executeCommand('rm -rf {}'.format(self.dir_in_file_server.split('/')[-1]))
            self.adb.executeShellCommand('rm -rf {}'.format(self.usb_dir_path))


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Uninstall app while USB slurp is running in parallel Test Script ***
        Examples: ./run.sh app_manager_scripts/concur_usb_slurp_uninstall_app.py --uut_ip 10.92.224.68 -appid com.wdc.importapp.ibi -chkapp\
        """)

    parser.add_argument('--file_server_ip', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--dir_in_file_server', help='The data set dir in file server', default='/test/5G_Standard/Audio1GB')
    parser.add_argument('-dusf', '--download_usb_slurp_files', action='store_true', default=False, 
                        help='Download usb slurp files from file server')
    parser.add_argument('-ddf', '--delete_download_files', action='store_true', default=False, 
                        help='Delete download usb slurp files for both local machine and test device')
    parser.add_argument('-appid', '--app_id', help='App ID to uninstalled')
    parser.add_argument('-chkpl', '--check_pm_list', help='Check pm list of app package', action='store_true')

    test = UninstallAppDuringUSBSlurp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
