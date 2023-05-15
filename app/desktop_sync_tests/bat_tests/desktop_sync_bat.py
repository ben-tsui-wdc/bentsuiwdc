# -*- coding: utf-8 -*-
""" Desktop Sync BAT test.
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
from platform_libraries.desktop_sync import DESKTOP_SYNC
# Sub-tests
from desktop_sync_tests.subtests.install_app import InstallApp
from desktop_sync_tests.subtests.start_kdd_wdsync_process import StartKDDWDSyncProcess
from desktop_sync_tests.subtests.kdd_login import KDDLogin
from desktop_sync_tests.subtests.get_kdd_http_port import Get_KDD_HTTP_Port
from desktop_sync_tests.subtests.get_wdsync_http_port import Get_WDSync_HTTP_Port
from desktop_sync_tests.subtests.sync_local_to_nas import SyncLocalToNas
from desktop_sync_tests.subtests.sync_nas_to_local import SyncNasToLocal
from desktop_sync_tests.subtests.unsync import Unsync
from desktop_sync_tests.subtests.offline_unsync import OfflineUnsync
from desktop_sync_tests.subtests.kdd_logout import KDDLogout
from desktop_sync_tests.subtests.stop_kdd_wdsync_process import StopKddWdsyncProcess
from desktop_sync_tests.subtests.uninstall_app import UninstallApp


class DesktopSyncBAT(IntegrationTest):

    TEST_SUITE = 'Desktop_Sync_BAT'
    TEST_NAME = 'Desktop_Sync_BAT'

    def init(self):
        self.share['desktop_sync_obj'] = DESKTOP_SYNC(client_os=self.client_os,
                                                      client_ip=self.client_ip,
                                                      client_username=self.client_username,
                                                      client_password=self.client_password,
                                                      rest_obj=self.uut_owner)

        self.share['cloud_env'] = self.env.cloud_env
        self.share['dst_folder_name'] = self.dst_folder_name
        self.share['src_path'] = self.src_path
        self.share['app_version'] = self.app_version
        self.share['file_server_ip'] = self.file_server_ip
        # Add sub-tests.
        self.integration.add_testcases(testcases=[
            InstallApp,
            StartKDDWDSyncProcess,
            Get_KDD_HTTP_Port,
            Get_WDSync_HTTP_Port,
            KDDLogin,
            SyncLocalToNas,
            SyncNasToLocal,
            Unsync,
            OfflineUnsync,
            KDDLogout,
            StopKddWdsyncProcess,
            UninstallApp
        ])
        """
        # Add sub-tests.
        self.integration.add_testcases(testcases=[
            InstallApp,
            UninstallApp
        ])
        """

    def before_test(self):
        self.share['desktop_sync_obj'].connect()

        self.log.info('Setup NAS environment')
        self.uut_owner.clean_user_root()
        self.uut_owner.upload_data(data_name=self.dst_folder_name, cleanup=True)

        self.log.info('Setup Client environment')
        if self.share['desktop_sync_obj'].check_local_folder_exist(self.src_path):
            self.share['desktop_sync_obj'].delete_folder(self.src_path)
        self.share['desktop_sync_obj'].create_folder(self.src_path)

    def after_test(self):
        self.share['desktop_sync_obj'].disconnect()

if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** Desktop_Sync_BAT on Kamino Android ***
        Examples: ./run.sh desktop_sync_tests/integration_tests/desktop_sync_bat.py\
                  --uut_ip 10.136.137.159 -u "nas_user" -p "nas_pass"\
                  --client_os "MAC" --client_ip 10.92.234.61 --client_username "user" --client_password "pass"\
                  --app_version 1.1.0.14 --dry_run
        """)
    parser.add_argument('--dst_folder_name', help='name of sync folder on nas', default='desktop_sync_nas_folder')
    parser.add_argument('--client_os', help='Client OS type', default='MAC', choices=['WIN', 'MAC'])
    parser.add_argument('--client_ip', help='Client OS ip address')
    parser.add_argument('--client_username', help='Username to login client OS')
    parser.add_argument('--client_password', help='The password os client user')
    parser.add_argument('--src_path', help='ablosute path of sync folder on client')
    parser.add_argument('--app_version', help='Desktop Sync tool version')
    parser.add_argument('--file_server_ip', help='File server IP Address', default='fileserver.hgst.com')

    test = DesktopSyncBAT(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
