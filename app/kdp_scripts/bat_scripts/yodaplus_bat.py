# -*- coding: utf-8 -*-
""" KDP ibi Platform BAT test.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPIntegrationTestArgument
from middleware.kdp_integration_test import KDPIntegrationTest
# Sub-tests
from kdp_scripts.bat_scripts.basic_transcoding import BasicTranscoding
from kdp_scripts.bat_scripts.check_cloud_service import CheckCloudService
from kdp_scripts.bat_scripts.cloud_environment_check import CloudEnvCheck
from kdp_scripts.bat_scripts.create_user_attach_user_check import CreateUserAttachUser
from kdp_scripts.bat_scripts.load_otaclient import LoadOTAClient
from kdp_scripts.bat_scripts.load_restsdk_module import LoadRestsdkmodule
from kdp_scripts.bat_scripts.otaclient_toml_m2m_check import OtaclientConfigM2MCheck
from kdp_scripts.bat_scripts.restsdk_toml_m2m_check import RestsdkConfigM2MCheck
from kdp_scripts.bat_scripts.restsdk_toml_iot_enabled import RestsdkConfigIoTEnabledCheck
from kdp_scripts.bat_scripts.userroots_mount_check import UserRootsMountOnDevice
from kdp_scripts.bat_scripts.check_docker_service import CheckDockerService
from kdp_scripts.bat_scripts.reboot import Reboot
from kdp_scripts.bat_scripts.check_dbus_daemon import CheckDbusDaemon
from kdp_scripts.bat_scripts.ota_proxy_check import OTAProxyCheck
from kdp_scripts.bat_scripts.restsdk_auto_restart import RestSDKAutoRestart
from kdp_scripts.bat_scripts.unauthenticated_ports_check import UnauthenticatedPortsCheck
from kdp_scripts.bat_scripts.firmware_update import FirmwareUpdate
from kdp_scripts.bat_scripts.factory_reset import FactoryReset
from kdp_scripts.bat_scripts.check_appmgr_service import CheckAppManagerService
from kdp_scripts.bat_scripts.afp_service_disable_check import AFPServiceDisableCheck
from kdp_scripts.bat_scripts.transcoding_flag_check import TranscodingFlagCheck
from kdp_scripts.bat_scripts.timesync_http_fallback import TimeSyncHTTPFallback
from kdp_scripts.bat_scripts.bluetooth_service_check import BluetoothServiceCheck
from kdp_scripts.bat_scripts.wifi_enable_check import WiFiEnableCheck
from kdp_scripts.bat_scripts.wifi_rw_check import WiFiRWCheck
from kdp_scripts.functional_tests.app_manager.install_app import InstallApp
from kdp_scripts.functional_tests.app_manager.uninstall_app import UninstallApp
from kdp_scripts.bat_scripts.usb_auto_mount import UsbAutoMount
from kdp_scripts.bat_scripts.usb_slurp_backup_file import UsbSlurpBackupFile
from kdp_scripts.bat_scripts.usb_slurp_delete_file import UsbSlurpDeleteFile
from kdp_scripts.bat_scripts.restsdk_time_out_of_sync import RestsdkProxyConnectTimeOutOfSync
from kdp_scripts.bat_scripts.samba_service_check import SambaServiceCheck
from kdp_scripts.bat_scripts.samba_rw_check import SambaRW
from kdp_scripts.bat_scripts.check_device_hostname import CheckDeviceHostname
from kdp_scripts.bat_scripts.check_nasadmin_daemon import CheckNasAdminDaemon
from kdp_scripts.bat_scripts.nasadmin_owner_access import NasAdminOwnerAccess
from kdp_scripts.bat_scripts.nasadmin_users_test import NasAdminUsersTest
from kdp_scripts.bat_scripts.nasadmin_samba_read_write import NasAdminSambaRW


class Platform_BAT(KDPIntegrationTest):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP - Platform BAT'
    REPORT_NAME = 'BAT'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):

        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            self.integration.add_testcases(testcases=[
                (FirmwareUpdate, {'force_update': True, 'include_gpkg': self.include_gpkg,
                                  'local_image_path': self.local_image_path}),
                CheckCloudService,
                CheckDeviceHostname,
                BluetoothServiceCheck,
                AFPServiceDisableCheck,
                CloudEnvCheck,
                CheckDockerService,
                CheckDbusDaemon,
                CheckAppManagerService,
                UserRootsMountOnDevice,
                LoadOTAClient,
                LoadRestsdkmodule,
                TranscodingFlagCheck,
                BasicTranscoding,
                CreateUserAttachUser,
                OtaclientConfigM2MCheck,
                RestsdkConfigM2MCheck,
                # RestsdkConfigIoTEnabledCheck,
                (InstallApp, {'app_id': self.app_id, 'TEST_NAME': 'KDP-203 - Install App Elephantdrive'}),
                (UninstallApp, {'app_id': self.app_id, 'container_clean_check': True, 'TEST_NAME': 'KDP-208 - Uninstall App Elephantdrive'}),
                (Reboot, {'TEST_NAME': 'KDP-200 - Device Reboot Test with ssh command', 
                    'TEST_JIRA_ID': 'KDP-200,KDP-897,KDP-1009,KDP-1010,KDP-214,KDP-1011,KDP-1015,KDP-204,KDP-194,KDP-193'}),
                (Reboot, {'no_rest_api': False, 'TEST_NAME': 'KDP-1008 - Device Reboot Test via restapi request', 
                    'TEST_JIRA_ID': 'KDP-1008,KDP-897,KDP-1009,KDP-1010,KDP-214,KDP-1011,KDP-1015,KDP-204,KDP-194,KDP-193,KDP-192'}),
                OTAProxyCheck,
                UnauthenticatedPortsCheck,
                UsbAutoMount,
                UsbSlurpBackupFile,
                UsbSlurpDeleteFile,
                TimeSyncHTTPFallback,
                RestsdkProxyConnectTimeOutOfSync,
                RestSDKAutoRestart,
                (WiFiEnableCheck, {'ap_ssid': self.test_ap_ssid_2_4G, 'ap_password': self.test_ap_password_2_4G, 'TEST_NAME': 'KDP-293 - Wi-Fi 2.4GHz Enabled Check'}),
                (WiFiRWCheck, {'ap_ssid': self.test_ap_ssid_2_4G, 'TEST_NAME': 'KDP-292 - Wi-Fi 2.4GHz Read&Write Check'}),
                (WiFiEnableCheck, {'ap_ssid': self.test_ap_ssid_5G, 'ap_password': self.test_ap_password_5G, 'TEST_NAME': 'KDP-294 - Wi-Fi 5GHz Enabled Check'}),
                (WiFiRWCheck, {'ap_ssid': self.test_ap_ssid_5G, 'TEST_NAME': 'KDP-295 - Wi-Fi 5GHz Read&Write Check'})
            ])

            if self.env.is_nasadmin_supported():
                self.integration.add_testcases(testcases=[
                    SambaServiceCheck,
                    SambaRW,
                    CheckNasAdminDaemon,
                    (NasAdminOwnerAccess, {'lite_mode': True, 'TEST_JIRA_ID': 'KDP-5626 ', 'TEST_NAME': 'KDP-5626 - nasAdmin - User Access Test'}),
                    (NasAdminUsersTest, {'lite_mode': True, 'TEST_JIRA_ID': 'KDP-5626 ', 'TEST_NAME': 'KDP-5627 - nasAdmin - Users Management Test'}),
                    (NasAdminSambaRW, {'lite_mode': True, 'TEST_JIRA_ID': 'KDP-5632 ', 'TEST_NAME': 'KDP-5632 - nasAdmin - Samba R/W Test'})
                ])

            self.integration.add_testcases(testcases=[
                FactoryReset
            ])


if __name__ == '__main__':
    parser = KDPIntegrationTestArgument("""\
        *** ibi BAT Running script ***
        Examples: ./start.sh kdp_scripts/bat_scripts/yodaplus_bat.py --uut_ip 10.200.141.103 -env qa1\
        """)

    # Test Arguments
    parser.add_argument('--single_run', help='Run single case for Platform BAT')
    parser.add_argument('--app_id', help='App ID for install and uninstall app test', default='com.elephantdrive.elephantdrive')
    parser.add_argument('--test_ap_ssid_2_4G', help='Wi-Fi SSID for 2.4G Wi-Fi test', default='stability')
    parser.add_argument('--test_ap_password_2_4G', help='Wi-Fi password for 2.4G Wi-Fi test', default='automation')
    parser.add_argument('--test_ap_ssid_5G', help='Wi-Fi SSID for 5G Wi-Fi test', default='stability_5G-1')
    parser.add_argument('--test_ap_password_5G', help='Wi-Fi password for 5G Wi-Fi test', default='automation')
    parser.add_argument('--include_gpkg', action='store_true', default=False, help='Update firmware with gpkg build')
    parser.add_argument('--local_image_path', default=None, help='Specify the absolute path of local firmware image')

    test = Platform_BAT(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
