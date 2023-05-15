# -*- coding: utf-8 -*-
""" Mean Time Between Failure test.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"
__author2__ = "Ben Tsui <ben.tsui@wdc.com"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPIntegrationTestArgument
from middleware.kdp_integration_test import KDPIntegrationTest
# BAT
from kdp_scripts.bat_scripts.check_cloud_service import CheckCloudService
from kdp_scripts.bat_scripts.avahi_service_check import AvahiServiceCheck
from kdp_scripts.bat_scripts.cloud_environment_check import CloudEnvCheck
from kdp_scripts.bat_scripts.create_user_attach_user_check import CreateUserAttachUser
from kdp_scripts.bat_scripts.load_otaclient import LoadOTAClient
from kdp_scripts.bat_scripts.load_restsdk_module import LoadRestsdkmodule
from kdp_scripts.bat_scripts.otaclient_toml_m2m_check import OtaclientConfigM2MCheck
from kdp_scripts.bat_scripts.restsdk_toml_m2m_check import RestsdkConfigM2MCheck
from kdp_scripts.bat_scripts.restsdk_toml_iot_enabled import RestsdkConfigIoTEnabledCheck
from kdp_scripts.bat_scripts.samba_service_check import SambaServiceCheck
from kdp_scripts.bat_scripts.userroots_mount_check import UserRootsMountOnDevice
from kdp_scripts.bat_scripts.check_docker_service import CheckDockerService
from kdp_scripts.bat_scripts.reboot import Reboot
from kdp_scripts.bat_scripts.check_dbus_daemon import CheckDbusDaemon
from kdp_scripts.bat_scripts.ota_proxy_check import OTAProxyCheck
from kdp_scripts.bat_scripts.restsdk_auto_restart import RestSDKAutoRestart
from kdp_scripts.bat_scripts.unauthenticated_ports_check import UnauthenticatedPortsCheck
from kdp_scripts.bat_scripts.samba_rw_check import SambaRW
from kdp_scripts.bat_scripts.firmware_update import FirmwareUpdate
from kdp_scripts.bat_scripts.check_appmgr_service import CheckAppManagerService
from kdp_scripts.bat_scripts.afp_service_disable_check import AFPServiceDisableCheck
from kdp_scripts.bat_scripts.transcoding_flag_check import TranscodingFlagCheck
from kdp_scripts.bat_scripts.timesync_http_fallback import TimeSyncHTTPFallback
from kdp_scripts.bat_scripts.usb_auto_mount import UsbAutoMount
from kdp_scripts.bat_scripts.usb_slurp_backup_file import UsbSlurpBackupFile
from kdp_scripts.bat_scripts.usb_slurp_delete_file import UsbSlurpDeleteFile
from kdp_scripts.bat_scripts.factory_reset import FactoryReset
# functional tests
from kdp_scripts.functional_tests.app_manager.app_mgr_stop_start_test import AppMgrStopStartTest
from kdp_scripts.functional_tests.app_manager.app_update import AppUpdateCheck
from kdp_scripts.functional_tests.app_manager.app_update_multiple_user import AppUpdateCheckMultipleUser
from kdp_scripts.functional_tests.app_manager.auto_relaunch_when_crash import AutoReLaunchWhenCrash
from kdp_scripts.functional_tests.app_manager.default_s3_url_check import DefaultS3BucketUrlCheck
from kdp_scripts.functional_tests.app_manager.get_app_list import GetAppList
from kdp_scripts.functional_tests.app_manager.install_app import InstallApp
from kdp_scripts.functional_tests.app_manager.install_unistall_app_with_worng_token import InstallUnistallAppWithWorngToken
from kdp_scripts.functional_tests.app_manager.local_install_app import LocalInstallApp
from kdp_scripts.functional_tests.app_manager.log_generate_verify import LogGenerateVerify
from kdp_scripts.functional_tests.app_manager.uninstall_app import UninstallApp
from kdp_scripts.functional_tests.ssh.ssh_with_wrong_pw import SshWithWrongPassword
from kdp_scripts.functional_tests.ssh.ssh_signature_check_with_cert import SshSignatureCheckWithCert
from kdp_scripts.functional_tests.ssh.ssh_signature_check_with_enable_root import SshSignatureCheckWithEnableRoot
from kdp_scripts.functional_tests.ssh.ssh_with_password import SshAccessWithPassword
from kdp_scripts.functional_tests.ssh.ssh_with_no_password import SshAccessWithNoPassword
from kdp_scripts.functional_tests.wifi.auto_connect_2G_after_shutdown import AutoConnect2GAfterShutdown
from kdp_scripts.functional_tests.wifi.auto_connect_5G_after_shutdown import AutoConnect5GAfterShutdown
from kdp_scripts.functional_tests.wifi.connect_2G_after_reboot import Connect2GAfterReboot
from kdp_scripts.functional_tests.wifi.connect_5G_after_reboot import Connect5GAfterReboot
from kdp_scripts.functional_tests.wifi.connect_with_worng_pw import ConnectWithIncorrectPW
from kdp_scripts.functional_tests.wifi.wifi_channel_plan import WiFiChannelPlan
from kdp_scripts.functional_tests.analytics.check_force_log_rotate import CheckForceLogRotate
from kdp_scripts.functional_tests.analytics.check_force_log_rotate_negative import CheckForceLogRotateNegative
from kdp_scripts.functional_tests.analytics.check_max_rotate_log_number import CheckMaxRotateLogNumber
from kdp_scripts.functional_tests.analytics.check_normal_log_rotate import CheckNormalLogRotate
from kdp_scripts.functional_tests.analytics.check_normal_log_rotate_negative import CheckNormalLogRotateNegative
from kdp_scripts.functional_tests.analytics.local_endpoint_export_debug_logs import LocalEndpointCanExportDebugLogs
from kdp_scripts.functional_tests.analytics.check_log_cleaner_start_when_bootup import CheckLogCleanerStartWhenBootUp
from kdp_scripts.functional_tests.analytics.check_log_policy_updater_start_when_bootup import CheckLogPolicyUpdaterStartWhenBootUp
from kdp_scripts.functional_tests.analytics.check_default_url_exist_in_properties import CheckDefaultUrlExistInProperties
from kdp_scripts.functional_tests.analytics.check_log_package_contains_syslog import CheckDebugLogPackageContainsSyslog
from kdp_scripts.functional_tests.analytics.check_log_upload_frequency import CheckLogUploadFrequency
from kdp_scripts.functional_tests.analytics.log_include_blacklist_keywords_will_not_upload import LogIncludeBlacklistKeywordsWillNotUpload
from kdp_scripts.functional_tests.analytics.log_include_whitelist_keywords_will_upload_only import LogIncludeWhitelistKeywordsWillUploadOnly
from kdp_scripts.functional_tests.analytics.log_include_both_blacklist_and_whitelist_keywords_will_not_upload import LogIncludeBothBlacklistAndWhitelistKeywordsWillNotUpload
from kdp_scripts.functional_tests.analytics.check_docker_log_exist import CheckDockerLogExist
from kdp_scripts.functional_tests.analytics.check_app_log_reserve_space import CheckAppLogReserveSpace
from kdp_scripts.functional_tests.analytics.check_debug_mode_and_upload_log_list import CheckDebugModeAndUploadLogList
from kdp_scripts.functional_tests.analytics.log_will_upload_when_pip_is_on import LogWillUploadWhenPipIsOn
from kdp_scripts.functional_tests.analytics.log_will_not_upload_when_pip_is_off import LogWillNotUploadWhenPipIsOff
from kdp_scripts.functional_tests.analytics.log_will_upload_when_pip_is_on_with_three_users import LogWillUploadWhenPipIsOnWithThreeUsers
from kdp_scripts.functional_tests.usb_slurp.usb_fs import USBFormat
from kdp_scripts.functional_tests.wifi.wifi_change_5G_to_2G import WifiChange5GTo2G
from kdp_scripts.functional_tests.wifi.wifi_change_2G_to_5G import WifiChange2GTo5G
from kdp_scripts.functional_tests.config.check_yodaplus_uboot_memory import CheckYodaplusUbootMemory
from kdp_scripts.functional_tests.config.no_java_exception_check import JavaExceptionCheck
from kdp_scripts.functional_tests.config.no_p2p0_check import NoP2p0Check
from kdp_scripts.functional_tests.storage.raid_conversion import RaidConversion
from kdp_scripts.functional_tests.led.led_power_ready import LEDPowerStateReady
from kdp_scripts.functional_tests.led.led_usb_slurp_test import LEDCheckUSBSlurp
from kdp_scripts.functional_tests.led.led_yoda_powerup_initializing import LEDYodaPowerup
from kdp_scripts.functional_tests.led.led_yoda_ready_to_onboard import LEDYodaReadyToOnboard
from kdp_scripts.functional_tests.led.led_boot_sequence import LEDCheckBootSequence
from kdp_scripts.functional_tests.led.led_device_reset import LEDDeviceReset
from kdp_scripts.stress_tests.ota_daily_stress import OTA_Daily_Stress
from kdp_scripts.functional_tests.device.reset_button_reboot_without_user import ResetButtonRebootWithoutUser
from kdp_scripts.functional_tests.device.press_reset_button_60secs import PressResetButton60secs
from kdp_scripts.functional_tests.device.check_network_recovery import CheckNetworkRecovery
from kdp_scripts.functional_tests.docker.docker_auto_restart import DockerAutoRestart
from kdp_scripts.functional_tests.docker.docker_cgroup_mount import DockerCgroupMount
from kdp_scripts.functional_tests.docker.docker_container_service import DockerContainerService
from kdp_scripts.functional_tests.docker.docker_mount import DockerRootDirMountVerify
from kdp_scripts.functional_tests.docker.docker_monit import DockerMonit
from kdp_scripts.functional_tests.docker.docker_network_verify import DockerNetworkVerify
from kdp_scripts.functional_tests.file_transfers.ibi_no_timemachine_folder import Yodaplus2TimeMachineVerify
from kdp_scripts.functional_tests.config.device_type import DeviceType


class MTBF(KDPIntegrationTest):

    TEST_SUITE = 'MTBF'
    TEST_NAME = 'MTBF_p1'
    REPORT_NAME = 'MTBF'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.test_result_list = []

    def init(self):
        # For OTA_Daily_Stress
        current_fw = self.uut.get('firmware')
        start_fw = '{}-{}'.format(current_fw.split('-')[0], int(current_fw.split('-')[1])-1)
        self.log.warning(start_fw)
        if self.uut.get('model') == 'monarch2':
            ota_bucket_id = '4070eb10-d982-11eb-9f5f-2550310614e5'
        elif self.uut.get('model') == 'pelican2':
            ota_bucket_id = '73d58100-d982-11eb-9f5f-2550310614e5'
        elif self.uut.get('model') == 'yodaplus2':
            ota_bucket_id = 'a99bd4b0-d982-11eb-9f5f-2550310614e5'

        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        elif self.sanity_test:
            if self.execute_test_group('device'):
                self.integration.add_testcases(testcases=[
                    (FirmwareUpdate, {'force_update': True, 'check_enable_root': True}),
                    (Reboot, {'TEST_NAME': 'KDP-200 - Device Reboot Test with ssh command',
                              'TEST_JIRA_ID': 'KDP-200,KDP-1009,KDP-1010,KDP-3296,KDP-1015,KDP-1178,KDP-1936,KDP-3293,KDP-3294,KDP-3295'}),
                    (Reboot, {'no_rest_api': False, 'TEST_NAME': 'KDP-1008 - Device Reboot Test via restapi request',
                              'TEST_JIRA_ID': 'KDP-1008,KDP-1009,KDP-1010,KDP-3296,KDP-1015,KDP-1178,KDP-1936,KDP-3293,KDP-3294,KDP-3295,KDP-3297,KDP-3298'})
                ])
            if self.execute_test_group('config'):
                self.integration.add_testcases(testcases=[
                    DeviceType,
                    JavaExceptionCheck,
                    NoP2p0Check
                ])
            if self.execute_test_group('anayltics'):
                self.integration.add_testcases(testcases=[
                    CheckForceLogRotate,
                    CheckForceLogRotateNegative,
                    CheckMaxRotateLogNumber,
                    CheckNormalLogRotate,
                    CheckNormalLogRotateNegative,
                    LogWillUploadWhenPipIsOn,
                    LogWillNotUploadWhenPipIsOff,
                    LocalEndpointCanExportDebugLogs,
                    CheckLogCleanerStartWhenBootUp,
                    CheckLogPolicyUpdaterStartWhenBootUp,
                    CheckDefaultUrlExistInProperties,
                    CheckDebugLogPackageContainsSyslog,
                    CheckLogUploadFrequency,
                    LogIncludeBlacklistKeywordsWillNotUpload,
                    LogIncludeWhitelistKeywordsWillUploadOnly,
                    LogIncludeBothBlacklistAndWhitelistKeywordsWillNotUpload,
                    CheckDockerLogExist,
                    CheckAppLogReserveSpace,
                    CheckDebugModeAndUploadLogList,
                    LogWillUploadWhenPipIsOnWithThreeUsers
                ])
            if self.execute_test_group('usb'):
                self.integration.add_testcases(testcases=[
                    (USBFormat, {'TEST_NAME': 'KDP-284 - [USB Slurp] USB 3.0 - MBR_NTFS', 'usb_fs': 'ntfs', 
                                 'TEST_JIRA_ID': 'KDP-284,KDP-246', 'file_server_ip': self.file_server}),
                    (USBFormat, {'TEST_NAME': 'KDP-261 - [USB Slurp] USB 3.0 - MBR_exFAT', 'usb_fs': 'exfat', 
                                 'TEST_JIRA_ID': 'KDP-261,KDP-283', 'file_server_ip': self.file_server}),
                    (USBFormat, {'TEST_NAME': 'KDP-257 - [USB Slurp] USB 2.0_3.0 - MBR_HFS+', 'usb_fs': 'hfs', 
                                 'TEST_JIRA_ID': 'KDP-257', 'file_server_ip': self.file_server}),
                    (USBFormat, {'TEST_NAME': 'KDP-281 - [USB Slurp] USB 3.0 - MBR_FAT32', 'usb_fs': 'fat', 
                                'TEST_JIRA_ID': 'KDP-281,KDP-245', 'file_server_ip': self.file_server}),
                    (USBFormat, {'TEST_NAME': 'KDP-5037 - [USB Export] USB 2.0_3.0 - MBR_NTFS', 'usb_fs': 'ntfs', 
                                 'TEST_JIRA_ID': 'KDP-5037', 'file_server_ip': self.file_server, 'usb_export':True}),
                    (USBFormat, {'TEST_NAME': 'KDP-5039 - [USB Export] USB 2.0_3.0 - MBR_exFAT', 'usb_fs': 'exfat', 
                                 'TEST_JIRA_ID': 'KDP-5039', 'file_server_ip': self.file_server, 'usb_export':True}),
                    (USBFormat, {'TEST_NAME': 'KDP-5040 - [USB Export] USB 2.0_3.0 - MBR_HFS+', 'usb_fs': 'hfs', 
                                 'TEST_JIRA_ID': 'KDP-5040', 'file_server_ip': self.file_server, 'usb_export':True}),
                    (USBFormat, {'TEST_NAME': 'KDP-5038 - [USB Export] USB 2.0_3.0 - MBR_FAT32', 'usb_fs': 'fat',       
                                 'TEST_JIRA_ID': 'KDP-5038', 'file_server_ip': self.file_server, 'usb_export':True}),
                ])
            if self.execute_test_group('app'):
                self.integration.add_testcases(testcases=[
                    GetAppList,
                    AppMgrStopStartTest,
                    (AppUpdateCheck, {'check_app_install': True, 'uninstall_app': True}),
                    (AppUpdateCheckMultipleUser,
                     {'check_app_install': True, 'uninstall_app': True, 'detach_2nd_user': True}),
                    AutoReLaunchWhenCrash,
                    DefaultS3BucketUrlCheck,
                    LogGenerateVerify,
                    (InstallApp, {
                        'app_id': 'com.wdc.filebrowser', 'check_app_install': True, 'check_internal_port_to_app': True,
                        'uninstall_app': True,
                    }),
                    (InstallApp, {
                        'app_id': 'com.elephantdrive.elephantdrive', 'check_app_install': True,
                        'check_mount_points': True,
                        'check_container_env': True, 'install_again_during_installation': True,
                        'install_again_after_installed': True,
                    }),
                    InstallUnistallAppWithWorngToken,
                    (LocalInstallApp, {'file_server_ip': self.file_server}),
                    (UninstallApp, {'app_id': 'com.elephantdrive.elephantdrive', 'app_bring_up_verify': True}),
                ])
            if self.execute_test_group('ssh'):
                self.integration.add_testcases(testcases=[
                    SshWithWrongPassword,
                    SshSignatureCheckWithCert,
                    SshSignatureCheckWithEnableRoot,
                    SshAccessWithPassword,
                    SshAccessWithNoPassword,
                ])
            if self.execute_test_group('docker'):
                self.integration.add_testcases(testcases=[
                    DockerAutoRestart,
                    DockerCgroupMount,
                    DockerContainerService,
                    DockerRootDirMountVerify,
                    DockerMonit,
                    DockerNetworkVerify,
                ])
            if self.execute_test_group('led'):
                self.integration.add_testcases(testcases=[
                    LEDPowerStateReady,
                    LEDCheckUSBSlurp,
                    LEDCheckBootSequence,
                    LEDDeviceReset,
                    (OTA_Daily_Stress, {'TEST_NAME': 'KDP-905 - [LED] Firmware update', 'update_mode': 'n_plus_one',
                                        'test_fw': current_fw, 'start_fw': start_fw, 'firmware_version': current_fw,
                                        'skip_data_integrity': True, 'skip_factory_reset': True,
                                        'ota_bucket_id': ota_bucket_id}),
                ])
            if self.execute_test_group('storage'):
                self.integration.add_testcases(testcases=[
                     (RaidConversion,
                      {'raid_type': 'span', 'attach_owner': True, 'read_write_check': True}),
                     (RaidConversion,
                      {'raid_type': 'mirror', 'attach_owner': True, 'read_write_check': True})
                ])
            if self.uut.get('model') == 'yodaplus2':
                if self.execute_test_group('wi-fi'):
                    if self.power_switch:
                        self.integration.add_testcases(testcases=[
                            (AutoConnect2GAfterShutdown, {
                                'wifi_ssid_2g': self.wifi_ssid_2g, 'wifi_password_2g': self.wifi_password_2g
                            }),
                            (AutoConnect5GAfterShutdown, {
                                'wifi_ssid_5g': self.wifi_ssid_5g, 'wifi_password_5g': self.wifi_password_5g
                            }),
                         ])
                    self.integration.add_testcases(testcases=[
                        CheckYodaplusUbootMemory,
                        WiFiChannelPlan,
                        (Connect2GAfterReboot, {
                            'wifi_ssid_2g': self.wifi_ssid_2g, 'wifi_password_2g': self.wifi_password_2g
                        }),
                        (Connect5GAfterReboot, {
                            'wifi_ssid_5g': self.wifi_ssid_5g, 'wifi_password_5g': self.wifi_password_5g
                        }),
                        (ConnectWithIncorrectPW, {
                            'wifi_ssid_5g': self.wifi_ssid_5g, 'wifi_password_5g': self.wifi_password_5g
                        }),
                        (WifiChange2GTo5G, {
                            'wifi_ssid_5g': self.wifi_ssid_5g, 'wifi_password_5g': self.wifi_password_5g,
                            'wifi_ssid_2g': self.wifi_ssid_2g, 'wifi_password_2g': self.wifi_password_2g
                        }),
                        (WifiChange5GTo2G, {
                            'wifi_ssid_5g': self.wifi_ssid_5g, 'wifi_password_5g': self.wifi_password_5g,
                            'wifi_ssid_2g': self.wifi_ssid_2g, 'wifi_password_2g': self.wifi_password_2g
                        }),
                    ])
                    if self.execute_test_group('led'):
                        self.integration.add_testcases(testcases=[
                            LEDYodaPowerup,
                            LEDYodaReadyToOnboard
                        ])
                    if self.execute_test_group('file_transfer'):
                        self.integration.add_testcases(testcases=[
                            Yodaplus2TimeMachineVerify
                        ])
            else:
                # MCH only
                if self.execute_test_group('app'):
                    self.integration.add_testcases(testcases=[
                        (InstallApp,
                         {'app_id': 'com.plexapp.mediaserver.smb', 'check_app_install': True, 'check_proxy_to_app': True,
                          'check_mount_points': True, 'check_container_env': True}),
                        (UninstallApp, {'app_id': 'com.plexapp.mediaserver.smb'}),
                        (InstallApp,
                         {'app_id': 'com.wdc.nasslurp', 'check_app_install': True, 'check_mount_points': True,
                          'check_container_env': True, 'add_install_multiple_app_ticket': True}),
                        (UninstallApp, {'app_id': 'com.wdc.nasslurp'}),
                    ])
                if self.execute_test_group('device'):
                    self.integration.add_testcases(testcases=[
                        ResetButtonRebootWithoutUser
                    ])
            if self.execute_test_group('device'):
                self.integration.add_testcases(testcases=[
                    CheckNetworkRecovery,
                    PressResetButton60secs,
                    (FactoryReset, {'samba_io': True})
                ])
        else:
            if self.uut.get('environment') == 'prod':
                self.integration.add_testcases(testcases=[
                    (FirmwareUpdate, {'force_update': True}),
                    CheckCloudService,
                    AvahiServiceCheck,
                    AFPServiceDisableCheck,
                    CloudEnvCheck,
                    CheckDockerService,
                    CheckDbusDaemon,
                    CheckAppManagerService,
                    UserRootsMountOnDevice,
                    LoadOTAClient,
                    LoadRestsdkmodule,
                    TranscodingFlagCheck,
                    CreateUserAttachUser,
                    OtaclientConfigM2MCheck,
                    RestsdkConfigM2MCheck,
                    RestsdkConfigIoTEnabledCheck,
                    SambaServiceCheck,
                    SambaRW,
                    (Reboot, {'TEST_NAME': 'KDP-200 - Device Reboot Test with ssh command', 
                        'TEST_JIRA_ID': 'KDP-200,KDP-1009,KDP-1010,KDP-3296,KDP-1015,KDP-1178,KDP-1936,KDP-3293,KDP-3294,KDP-3295'}),
                    (Reboot, {'no_rest_api': False, 'TEST_NAME': 'KDP-1008 - Device Reboot Test via restapi request', 
                        'TEST_JIRA_ID': 'KDP-1008,KDP-1009,KDP-1010,KDP-3296,KDP-1015,KDP-1178,KDP-1936,KDP-3293,KDP-3294,KDP-3295,KDP-3297,KDP-3298'}),
                    OTAProxyCheck,
                    UnauthenticatedPortsCheck,
                    UsbAutoMount,
                    UsbSlurpBackupFile,
                    UsbSlurpDeleteFile,
                    RestSDKAutoRestart,
                    SshWithWrongPassword,
                    WiFiChannelPlan
                ])
            else:
                self.integration.add_testcases(testcases=[
                    (FirmwareUpdate, {'force_update': True}),
                    CheckCloudService,
                    AvahiServiceCheck,
                    AFPServiceDisableCheck,
                    CloudEnvCheck,
                    CheckDockerService,
                    CheckDbusDaemon,
                    CheckAppManagerService,
                    UserRootsMountOnDevice,
                    LoadOTAClient,
                    LoadRestsdkmodule,
                    TranscodingFlagCheck,
                    CreateUserAttachUser,
                    OtaclientConfigM2MCheck,
                    RestsdkConfigM2MCheck,
                    RestsdkConfigIoTEnabledCheck,
                    (InstallApp, {'app_id': 'com.elephantdrive.elephantdrive', 'check_app_install':True}),
                    (UninstallApp, {'app_id': 'com.elephantdrive.elephantdrive'}),
                    SambaServiceCheck,
                    SambaRW,
                    (Reboot, {'TEST_NAME': 'KDP-200 - Device Reboot Test with ssh command', 
                        'TEST_JIRA_ID': 'KDP-200,KDP-1009,KDP-1010,KDP-3296,KDP-1015,KDP-1178,KDP-1936,KDP-3293,KDP-3294,KDP-3295'}),
                    (Reboot, {'no_rest_api': False, 'TEST_NAME': 'KDP-1008 - Device Reboot Test via restapi request', 
                        'TEST_JIRA_ID': 'KDP-1008,KDP-1009,KDP-1010,KDP-3296,KDP-1015,KDP-1178,KDP-1936,KDP-3293,KDP-3294,KDP-3295,KDP-3297,KDP-3298'}),
                    OTAProxyCheck,
                    UnauthenticatedPortsCheck,
                    UsbAutoMount,
                    UsbSlurpBackupFile,
                    UsbSlurpDeleteFile,
                    TimeSyncHTTPFallback,
                    RestSDKAutoRestart,
                    SshWithWrongPassword,
                    WiFiChannelPlan
                ])

    def execute_test_group(self, test_group_name):
        test_group_list = [x.lower() for x in self.test_group]
        if 'all' in test_group_list or test_group_name in test_group_list:
            return True
        else:
            return False

    def after_test(self):
        self.log.warning('Calculate the number of Pass/Fail here and generate a report.')
        # The following is for html report on Jenkins
        test_result_dict = {}
        """
        Example:
            {'test_name': {'pass':2, 'fail':4}}
        """
        for item in self.data.test_result:
            if not test_result_dict.get(item.TEST_NAME):
                test_result_dict[item.TEST_NAME] = {'pass': 0, 'fail': 0, 'test_jira_id': item.get("test_jira_id")}
            if item.TEST_PASS == True:
                test_result_dict[item.TEST_NAME]['pass'] += 1
            elif item.TEST_PASS == False:
                test_result_dict[item.TEST_NAME]['fail'] += 1
            elif item.TEST_PASS == None:
                self.log.warning('item.TEST_PASS == None, test case name:{}, test item:{}'.format(item.TEST_NAME, item))

        # table start
        # Different test items
        '''
        Example:
            <tr><td>Factory_Reset_Test</td><td>20</td><td>15</td><td>5</td></tr>
        '''
        HTML_RESULT = '<table id="report" class="MTBF">'
        HTML_RESULT += '<tr><th>Test Name</th><th>Test Cases</th><th>Iterations</th><th>PASS</th><th>FAIL</th></tr>'  # Title column
        # Calculate the number of total iterations after all test items are printed
        '''
        Example:
            <tr><td>Factory_Reset_Test</td><td>20</td><td>15</td><td>5</td></tr>
        '''
        total_pass = 0
        total_fail = 0
        total_test_case_number = 0
        for item in test_result_dict:
            HTML_RESULT += '<tr>'
            total_pass += test_result_dict[item]['pass']
            total_fail += test_result_dict[item]['fail']
            itr_per_item = test_result_dict[item]['pass'] + test_result_dict[item]['fail']
            test_cases = test_result_dict[item]['test_jira_id'].split(',')
            test_case_number = len(test_cases)
            total_test_case_number += test_case_number
            test_name = item
            if test_case_number > 1:
                test_name += ", include:"
                # If the test cases > 5, print 5 test cases in each line to avoid the HTML report become too wide
                span = 5
                test_case_group = [",".join(test_cases[i:i+span]) for i in range(0, test_case_number, span)]
                for group in test_case_group:
                    test_name += '<br/>{}'.format(group.replace(',', ', '))
            HTML_RESULT += "<td>{}</td><td>{}</td><td>{}</td><td class='pass'>{}</td><td class='fail'>{}</td>".format(test_name, test_case_number, itr_per_item, test_result_dict[item]['pass'], test_result_dict[item]['fail'])
            HTML_RESULT += '</tr>'
        HTML_RESULT += '<tr>'
        HTML_RESULT += "<td>TOTAL</td><td>{}</td><td>{}</td><td class='pass'>{}</td><td class='fail'>{}</td>".format(total_test_case_number, total_pass+total_fail, total_pass, total_fail)
        HTML_RESULT += '</tr>'
        # table finished
        HTML_RESULT += '</table>'
        MTBF_RESULT_jenkins_property = "MTBF_RESULT={}\n".format(HTML_RESULT)
        try:
            with open('/root/app/output/MTBF_RESULT', 'w') as f:
                f.write(MTBF_RESULT_jenkins_property)
        except:
            with open('MTBF_RESULT', 'w') as f:
                f.write(MTBF_RESULT_jenkins_property)
        # The following is for csv file
        final_result_dict_base = {'product': self.uut.get('model'), 'build': self.uut.get('firmware'), 'Count_unit':'number of times', 'executionTime': int(time.time()*1000)}
        test_result_list = []
        for index, item in enumerate(['TotalPass', 'TotalFail']):
            test_result_list.append(dict(final_result_dict_base))
            if item == 'TotalPass':
                count = total_pass
            elif item == 'TotalFail':
                count = total_fail
            test_result_list[index].update({'Result':item, 'Count_avg':count})
        result_csv = ''
        for element in test_result_list:
            for item in ['product', 'build', 'Result', 'Count_avg', 'Count_unit', 'executionTime']:
                value = element.get(item)
                result_csv += '{},'.format(value)  # String
            result_csv += '\r\n'
        with open('{}/result.csv'.format(self.env.results_folder), 'a') as f:
            f.write(result_csv + '\r\n')

        def dict_copy(self, dict_data):
            return dict(dict_data)


if __name__ == '__main__':
    parser = KDPIntegrationTestArgument("""\
        *** MTBF Running script ***
        Examples: ./start.sh functional_tests/MTBF.py ./run.sh  functional_tests/MTBF.py --uut_ip 10.0.0.8 --cloud_env qa1 --serial_server_ip 10.0.0.6 --serial_server_port 20000 --ap_ssid jason_5G --ap_password automation --disable_serial_server_daemon_msg --dry_run --exec_ordering "(1,0) --choice 3"
        """)

    # Test Arguments
    parser.add_argument('--single_run', help='Run single case for Platform BAT')
    parser.add_argument('--file_server', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--sanity_test', help='Only run sanity test cases', action='store_true')
    parser.add_argument('--test_group', nargs='+', default=['all'],
                        help='run all or specific test groups in sanity test, e.g. --test_group config usb app')
    parser.add_argument('--wifi_ssid_2g', help="", default='stability')
    parser.add_argument('--wifi_password_2g', help="", default='automation')
    parser.add_argument('--wifi_ssid_5g', help="", default='stability_5G-1')
    parser.add_argument('--wifi_password_5g', help="", default='automation')

    test = MTBF(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)