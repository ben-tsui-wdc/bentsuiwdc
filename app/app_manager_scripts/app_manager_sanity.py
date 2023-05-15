# -*- coding: utf-8 -*-
""" App Manager Functional Sanity test.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
# Sub-tests
## Install App test cases
from app_manager_scripts.install_app import InstallApp
from app_manager_scripts.install_app_cpu_full_loaded import InstallAppCPUFullLoaded
from app_manager_scripts.install_app_reboot import InstallAppReboot
## Uninstall App test cases
from app_manager_scripts.uninstall_app import UninstallApp
from app_manager_scripts.uninstall_app_cpu_full_loaded import UninstallAppCPUFullLoaded
from app_manager_scripts.remove_user_who_installed_app import RemoveUserWhoInstalledApp
# App Update test case
from app_manager_scripts.app_update_check import AppUpdateCheck
## Concurrency Install test cases
from app_manager_scripts.concur_install_different_app_multiple_users import ConcurrentInstallDifferentAppMultipleUsers
from app_manager_scripts.concur_install_same_app_multiple_users import ConcurrentInstallSameAppMultipleUsers
from app_manager_scripts.concur_install_multiple_apps_admin_user import ConcurrentInstallMultipleAppAdminUser
from app_manager_scripts.concur_install_multiple_apps_second_user import ConcurrentInstallMultipleAppSecondUser
from app_manager_scripts.concur_reboot_install_app import RebootSystemDuringInstallApp
from app_manager_scripts.concur_usb_slurp_install_app import InstallAppDuringUSBSlurp
from app_manager_scripts.concur_upload_data_install_app import InstallAppDuringUploadData
from app_manager_scripts.concur_fw_flash_install_app import InstallAppDuringFWFlash
from app_manager_scripts.concur_upload_data_install_app_multiple_users import ConcurrentInstallSameAppDuringUploadDataMultipleUsers
## Concurrency Uninstall test cases
from app_manager_scripts.concur_uninstall_different_app_multiple_users import ConcurrentUninstallDifferentAppMultipleUsers
from app_manager_scripts.concur_uninstall_same_app_multiple_users import ConcurrentUninstallSameAppMultipleUsers
from app_manager_scripts.concur_uninstall_multiple_apps_admin_user import ConcurrentUninstallMultipleAppAdminUser
from app_manager_scripts.concur_uninstall_multiple_apps_second_user import ConcurrentUninstallMultipleAppSecondUser
from app_manager_scripts.concur_reboot_uninstall_app import RebootSystemDuringUninstallApp
from app_manager_scripts.concur_usb_slurp_uninstall_app import UninstallAppDuringUSBSlurp
from app_manager_scripts.concur_upload_data_uninstall_app import UninstallAppDuringUploadData
from app_manager_scripts.concur_fw_flash_uninstall_app import UninstallAppDuringFWFlash
## Concurrency Install & Uninstall test cases
from app_manager_scripts.concur_install_uninstall_different_app_admin_user import ConcurrentInstallUninstallDifferentAppAdminUser
from app_manager_scripts.concur_install_uninstall_different_app_second_user import ConcurrentInstallUninstallDifferentAppSecondUser
from app_manager_scripts.concur_install_uninstall_multiple_users_different_app import ConcurrentInstallUninstallAppMultipleUsersDifferentApp
from app_manager_scripts.concur_install_uninstall_multiple_users_same_app import ConcurrentInstallUninstallAppMultipleUsersSameApp

class AppManager_Sanity(IntegrationTest):

    TEST_SUITE = 'App_Manager_Sanity'
    TEST_NAME = 'App_Manager_Sanity'
    REPORT_NAME = 'Sanity'
    # Popcorn
    TEST_TYPE = 'Functional'
    PRIORITY = 'Critical'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):

        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            self.integration.add_testcases(testcases=[
                # Non-Concurrency test cases
                (InstallApp, {'app_id': self.app_id, 'check_app_install': True}),
                (UninstallApp, {'app_id': self.app_id, 'check_pm_list': True}),
                (InstallAppCPUFullLoaded, {'app_id': self.app_id, 'check_app_install': True}),
                (UninstallAppCPUFullLoaded, {'app_id': self.app_id, 'check_pm_list': True}),
                (InstallAppReboot, {'app_id': self.app_id, 'check_app_install': True, 'uninstall_app':True}),
                (RemoveUserWhoInstalledApp, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_pm_list': True}),
                (AppUpdateCheck, {'uninstall_app': True}),
                # Concurrency Install test cases
                (ConcurrentInstallDifferentAppMultipleUsers, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                (ConcurrentInstallSameAppMultipleUsers, {'app_id': self.app_id, 'check_app_install': True}),
                (ConcurrentInstallMultipleAppAdminUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                (ConcurrentInstallMultipleAppSecondUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                (ConcurrentInstallSameAppDuringUploadDataMultipleUsers, {'app_id': self.app_id, 'check_app_install': True}),
                # Concurrency Uninstall test cases
                (ConcurrentUninstallDifferentAppMultipleUsers, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_pm_list': True}),
                (ConcurrentUninstallSameAppMultipleUsers, {'app_id': self.app_id, 'check_pm_list': True}),
                (ConcurrentUninstallMultipleAppAdminUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_pm_list': True}),
                (ConcurrentUninstallMultipleAppSecondUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_pm_list': True}),
                # Concurrency Install & Uninstall test cases
                (ConcurrentInstallUninstallDifferentAppAdminUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                (ConcurrentInstallUninstallDifferentAppSecondUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                (ConcurrentInstallUninstallAppMultipleUsersDifferentApp, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                (ConcurrentInstallUninstallAppMultipleUsersSameApp, {'app_id': self.app_id, 'check_app_install': True}),
                # Concurrency with other process test cases
                (RebootSystemDuringInstallApp, {'app_id': self.app_id, 'check_app_install': True}),
                (RebootSystemDuringUninstallApp, {'app_id': self.app_id}),
                (InstallAppDuringUSBSlurp, {'app_id': self.app_id, 'check_app_install': True, 'download_usb_slurp_files':True}),
                (UninstallAppDuringUSBSlurp, {'app_id': self.app_id, 'check_pm_list': True, 
                    'download_usb_slurp_files':False, 'delete_download_files':True}),
                (InstallAppDuringUploadData, {'app_id': self.app_id, 'check_app_install': True}),
                (UninstallAppDuringUploadData, {'app_id': self.app_id, 'check_pm_list': True}),
                (InstallAppDuringFWFlash, {'app_id': self.app_id, 'check_app_install': True}),
                (UninstallAppDuringFWFlash, {'app_id': self.app_id, 'check_pm_list': True}),
            ])


if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** App Manager Sanity Test Running script ***
        Examples: ./start.sh app_manager_scripts/app_manager_sanity --uut_ip 10.92.224.68 -env qa1\
        """)
    # Test Arguments
    parser.add_argument('-sr', '--single_run', help='Run single case for App Manager Sanity Test')
    parser.add_argument('-appid', '--app_id', help='App ID to installed', required=True)
    parser.add_argument('-appid2', '--app_id_2', help='Second App ID to installed', required=True)

    test = AppManager_Sanity(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
