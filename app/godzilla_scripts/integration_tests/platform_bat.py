# -*- coding: utf-8 -*-
""" Godzilla integration test for Platform BAT
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
from datetime import datetime, timedelta
# platform modules
from middleware.arguments import GodzillaIntegrationTestArgument
from middleware.godzilla_integration_test import GodzillaIntegrationTest
# Sub-tests

from godzilla_scripts.bat_scripts.firmware_update import FirmwareUpdate
from godzilla_scripts.bat_scripts.device_name_check import DeviceNameCheck
from godzilla_scripts.bat_scripts.load_restsdk_module import LoadRestsdkModule
from godzilla_scripts.bat_scripts.load_otaclient import LoadOTAClient
from godzilla_scripts.bat_scripts.load_app_manager import LoadAPPManager
from godzilla_scripts.bat_scripts.install_apkg_check import InstallAPKGCheck
from godzilla_scripts.bat_scripts.cloud_environment_check import CloudEnvCheck
from godzilla_scripts.bat_scripts.samba_service_check import SambaServiceCheck
from godzilla_scripts.bat_scripts.afp_service_check import AFPServiceCheck
from godzilla_scripts.bat_scripts.nfs_service_check import NFSServiceCheck
from godzilla_scripts.bat_scripts.ftp_service_check import FTPServiceCheck
from godzilla_scripts.bat_scripts.iscsi_service_check import iSCSIServiceCheck
from godzilla_scripts.bat_scripts.raid_and_disk_check import RaidAndDiskCheck
from godzilla_scripts.bat_scripts.usb_auto_mount import USBAutoMount
from godzilla_scripts.bat_scripts.ota_proxy_check import OTAProxyCheck
from godzilla_scripts.bat_scripts.admin_share_permission_check import AdminSharePermissionCheck
from godzilla_scripts.bat_scripts.second_user_share_permission_check import SecondUserSharePermissionCheck
from godzilla_scripts.bat_scripts.create_user_attach_user_check import CreateUserAttachUser
from godzilla_scripts.bat_scripts.user_roots_mount_check import UserRootsMountOnDevice
from godzilla_scripts.bat_scripts.samba_rw_check import SambaRW
from godzilla_scripts.bat_scripts.afp_rw_check import AFPRW
from godzilla_scripts.bat_scripts.nfs_rw_check import NFSRW
from godzilla_scripts.bat_scripts.ftp_rw_check import FTPRW
from godzilla_scripts.bat_scripts.reboot import Reboot
from godzilla_scripts.bat_scripts.restsdk_auto_restart import RestSDKAutoRestart
from godzilla_scripts.bat_scripts.factory_reset import FactoryReset
from godzilla_scripts.bat_scripts.nasadmin_service_check import NasAdminServiceCheck
from godzilla_scripts.bat_scripts.nasadmin_get_token import NasAdminGetToken
from godzilla_scripts.bat_scripts.nasadmin_check_system import NasAdminCheckSystemStatus
from godzilla_scripts.bat_scripts.nasadmin_same_subnet_access import NasAdminSameSubnetAccess
from godzilla_scripts.bat_scripts.restsdk_m2m_token_check import M2MTokenCheckInRestSDK
from godzilla_scripts.bat_scripts.otaclient_m2m_token_check import M2MTokenCheckInOTAcLient
from godzilla_scripts.bat_scripts.restsdk_iot_check import IoTCheckInRestSDK


class PLATFORM_BAT(GodzillaIntegrationTest):

    TEST_SUITE = 'GODZILLA PLATFORM BAT'
    TEST_NAME = 'GODZILLA PLATFORM BAT'
    # Popcorn
    PROJECT = 'godzilla'
    TEST_TYPE = 'functional'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'BAT'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        if self.single_run:
            for test_case in self.single_run:
                self.integration.add_testcases(testcases=[eval(test_case)])
        else:
            if self.env.model:
                self.model = self.env.model
            else:
                self.model = self.ssh_client.get_model_name()

            self.integration.add_testcases(testcases=[
                (FirmwareUpdate, {'force_update': True, 'local_image': self.local_image,
                                  'factory_reset_after_upgrade': self.factory_reset_after_upgrade,
                                  'local_image_path': self.local_image_path}),
                DeviceNameCheck,
                LoadRestsdkModule,
                LoadOTAClient,
                # LoadAPPManager,  # Removed in 3.10 fw
                (CloudEnvCheck, {'cloud_env': self.env.cloud_env}),
                SambaServiceCheck,
                AFPServiceCheck,
                NFSServiceCheck,
                FTPServiceCheck,
                NasAdminServiceCheck,
                NasAdminGetToken,
                # NasAdminCheckSystemStatus,
                NasAdminSameSubnetAccess,
                M2MTokenCheckInRestSDK,
                M2MTokenCheckInOTAcLient,
                IoTCheckInRestSDK
            ])

            self.integration.add_testcases(testcases=[
                (USBAutoMount, {'usb_file_system': 'fat32',
                                'TEST_NAME': 'GZA USB Auto mount on Device and SAMBA IO Test - FAT32',
                                'TEST_JIRA_ID': 'GZA-1314'}),
                (USBAutoMount, {'usb_file_system': 'ntfs',
                                'TEST_NAME': 'GZA USB Auto mount on Device and SAMBA IO Test - NTFS',
                                'TEST_JIRA_ID': 'GZA-7194'})
            ])

            # These devices only have 1 USB port and cannot test multiple file systems
            if self.model not in ['Glacier', 'Mirrorman']:
                self.integration.add_testcases(testcases=[
                    (USBAutoMount, {'usb_file_system': 'hfs+',
                                    'TEST_NAME': 'GZA USB Auto mount on Device and SAMBA IO Test - HFS+',
                                    'TEST_JIRA_ID': 'GZA-7196'})
                ])

            # Mirror didn't support exFAT
            # Glacier/Mirrorman only have 1 USB port and cannot test multiple file systems
            if self.model not in ['Mirror', 'Glacier', 'Mirrorman']:
                self.integration.add_testcases(testcases=[
                    (USBAutoMount, {'usb_file_system': 'exfat',
                                    'TEST_NAME': 'GZA USB Auto mount on Device and SAMBA IO Test - EXFAT',
                                    'TEST_JIRA_ID': 'GZA-7195'}),
                    iSCSIServiceCheck
                ])

            if self.env.cloud_env not in ['prod']:
                self.integration.add_testcases(testcases=[
                    OTAProxyCheck
                ])

            self.integration.add_testcases(testcases=[
                RaidAndDiskCheck,
                AdminSharePermissionCheck,
                SecondUserSharePermissionCheck,
                CreateUserAttachUser,
                SambaRW,
                # (AFPRW, {'mac_server_ip': self.mac_server_ip, 'mac_username': self.mac_username,
                #          'mac_password': self.mac_password}),  # Removed in 5.19.105 FW
                NFSRW,
                FTPRW,
                (Reboot, {'no_rest_api': True}),
                (Reboot, {'TEST_NAME': 'Device Reboot Test with RestSDK API'}),
                RestSDKAutoRestart
            ])
            """
            if self.env.cloud_env == 'dev1' and self.model not in ['EX4100', 'Mirror', 'EX2Ultra']:
                # Todo: Enable test when we have RestSDK 2.0.0-999 images for these models and qa1/prod env
                self.integration.add_testcases(testcases=[InstallAPKGCheck])
            """
            self.integration.add_testcases(testcases=[
                FactoryReset
            ])


if __name__ == '__main__':
    parser = GodzillaIntegrationTestArgument("""\
        *** RESTSDK_BAT on Kamino Android ***
        Examples: ./run.sh godzilla_scripts/integration_tests/platform_bat.py --uut_ip 10.136.137.159\
        """)
    # Test Arguments
    parser.add_argument('--single_run', nargs='+', help='Run single case for BAT')
    parser.add_argument('--mac_server_ip', help='Mac server IP Address', default="10.6.160.218")
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='fitlab')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac client', default='fituser')
    parser.add_argument('--local_image', help='Download firmware image from local file server', action="store_true", default=False)
    parser.add_argument('--factory_reset_after_upgrade', action='store_true', default=False,
                        help='If we already know restsdk will be downgraded after fw update, clean the db directly')
    parser.add_argument('--local_image_path', default=None, help='Specify the absolute path of local firmware image')

    test = PLATFORM_BAT(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
