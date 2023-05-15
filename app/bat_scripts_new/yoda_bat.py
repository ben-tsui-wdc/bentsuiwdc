# -*- coding: utf-8 -*-
""" Yoda BAT test.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
# Sub-tests
from bat_scripts_new.adb_connect_check import ADBConnectCheck
from bat_scripts_new.cloud_environment_check import CloudEnvCheck
from bat_scripts_new.reboot import Reboot
from bat_scripts_new.uboot_memory_check import UbootMemoryCheck
from bat_scripts_new.wifi_enable_check import WiFiEnableCheck
from bat_scripts_new.wifi_switch_check import WiFiSwitchCheck
from bat_scripts_new.factory_reset import FactoryReset
from bat_scripts_new.load_restsdk_module import LoadRestsdkmodule
from bat_scripts_new.load_otaclient import LoadOTAClient
from bat_scripts_new.load_app_manager import LoadAPPManager
from bat_scripts_new.fw_update_pass_check import FWUpdatePASSCheck
from bat_scripts_new.samba_service_check import SambaServiceCheck
from bat_scripts_new.afp_service_check import AFPServiceCheck
from bat_scripts_new.userroots_mount_check import UserRootsMountOnDevice
from bat_scripts_new.create_user_attach_user_check import CreateUserAttachUser
from bat_scripts_new.check_cloud_service import CheckCloudService
from bat_scripts_new.wifi_rw_check import WiFiRWCheck
from bat_scripts_new.usb_auto_mount import UsbAutoMount
from bat_scripts_new.usb_slurp_backup_file import UsbSlurpBackupFile
from bat_scripts_new.usb_slurp_delete_file import UsbSlurpDeleteFile
from bat_scripts_new.avahi_service_check import AvahiServiceCheck
from bat_scripts_new.samba_rw_check import SambaRW
from bat_scripts_new.transcoding_disable_check import TranscodingDisableCheck
from bat_scripts_new.basic_transcoding import BasicTranscoding
from bat_scripts_new.ble_service_check import BLEServiceCheck
from bat_scripts_new.lighttpd_service_check import LighttpdServiceCheck
from bat_scripts_new.data_loss_check import DataLossCheck
from bat_scripts_new.timesync_http_fallback import TimeSyncHTTPFallback
from bat_scripts_new.unauthenticated_ports_check import UnauthenticatedPortsCheck
from bat_scripts_new.default_ota_bucket_check import DefaultOTABucketCheck
from bat_scripts_new.ota_proxy_check import OTAProxyCheck
from bat_scripts_new.ibi_5g_wifi_channel_check import ibi5GWiFiChannelCheck
from app_manager_scripts.install_app import InstallApp
from app_manager_scripts.uninstall_app import UninstallApp
from bat_scripts_new.restsdk_toml_m2m_check import RestsdkConfigM2MCheck
from bat_scripts_new.otaclient_toml_m2m_check import OtaclientConfigM2MCheck
from bat_scripts_new.restsdk_toml_iot_enabled import RestsdkConfigIoTEnabledCheck

class YODA_BAT(IntegrationTest):

    TEST_SUITE = 'ibi_platform_sanity'
    TEST_NAME = 'ibi_platform_sanity'
    # Popcorn
    PROJECT = 'ibi'
    TEST_TYPE = 'Functional'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'BAT'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):

        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            self.integration.add_testcases(testcases=[
                (FWUpdatePASSCheck, {'version_check': self.version_check}),
                ADBConnectCheck,
                LoadRestsdkmodule,
                LoadOTAClient,
                LoadAPPManager,
                RestsdkConfigM2MCheck,
                OtaclientConfigM2MCheck,
                RestsdkConfigIoTEnabledCheck,
                UserRootsMountOnDevice,
                TranscodingDisableCheck,
                (CloudEnvCheck, {'cloud_env': self.env.cloud_env}),
                CheckCloudService,
                CreateUserAttachUser,
                BLEServiceCheck,
                ibi5GWiFiChannelCheck,
                (Reboot, {'no_rest_api': True, 'wait_device': True}),
                (Reboot, {'no_rest_api': False, 'wait_device': True, 'TEST_NAME': 'Device Reboot Test with RESTAPI'}),
                TimeSyncHTTPFallback,
                UnauthenticatedPortsCheck,
                UbootMemoryCheck,
                UsbAutoMount,
                UsbSlurpBackupFile,
                UsbSlurpDeleteFile,
                DataLossCheck,
                OTAProxyCheck,
                BasicTranscoding,
                (InstallApp, {'app_id': self.app_id}),
                (UninstallApp, {'app_id': self.app_id}),
                (WiFiEnableCheck, {'ap_ssid': self.test_ap_ssid_2_4G, 'ap_password': self.test_ap_password_2_4G, 'TEST_NAME': 'Wi-Fi 2.4GHz Enabled Check'}),
                (WiFiRWCheck, {'ap_ssid': self.test_ap_ssid_2_4G, 'TEST_NAME': 'Wi-Fi 2.4GHz Read&Write Check'}),
                (WiFiEnableCheck, {'ap_ssid': self.test_ap_ssid_5G, 'ap_password': self.test_ap_password_5G, 'TEST_NAME': 'Wi-Fi 5GHz Enabled Check'}),
                (WiFiRWCheck, {'ap_ssid': self.test_ap_ssid_5G, 'TEST_NAME': 'Wi-Fi 5GHz Read&Write Check'}),
                (FactoryReset, {'no_rest_api': True})
            ])

if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** Yoda BAT Running script ***
        Examples: ./start.sh bat_scripts_new/yoda_bat --uut_ip 10.92.224.68 -env dev1\
        """)

    # Test Arguments
    parser.add_argument('--version_check', help='Firmware version to compare')
    parser.add_argument('--single_run', help='Run single case for Yoda BAT')
    parser.add_argument('--app_id', help='App ID for install and uninstall app test', default='com.wdc.importapp.ibi')
    parser.add_argument('--test_ap_ssid_2_4G', help='Wi-Fi SSID for 2.4G Wi-Fi test', default='stability_public')
    parser.add_argument('--test_ap_password_2_4G', help='Wi-Fi password for 2.4G Wi-Fi test', default='automation')
    parser.add_argument('--test_ap_ssid_5G', help='Wi-Fi SSID for 5G Wi-Fi test', default='stability_public_5G')
    parser.add_argument('--test_ap_password_5G', help='Wi-Fi password for 5G Wi-Fi test', default='automation') 

    test = YODA_BAT(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
