# -*- coding: utf-8 -*-
""" Platform Functional Regression Cycle P1 test.
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>", "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
# Sub-tests
from bat_scripts_new.create_user_attach_user_check import CreateUserAttachUser
from bat_scripts_new.check_cloud_service import CheckCloudService
from bat_scripts_new.adb_connect_check import ADBConnectCheck
from bat_scripts_new.unauthenticated_ports_check import UnauthenticatedPortsCheck
from bat_scripts_new.cloud_environment_check import CloudEnvCheck
from bat_scripts_new.reboot import Reboot
from bat_scripts_new.uboot_memory_check import UbootMemoryCheck
from bat_scripts_new.wifi_enable_check import WiFiEnableCheck
from bat_scripts_new.factory_reset import FactoryReset
from bat_scripts_new.load_restsdk_module import LoadRestsdkmodule
from bat_scripts_new.load_otaclient import LoadOTAClient
from bat_scripts_new.load_app_manager import LoadAPPManager
from bat_scripts_new.fw_update_pass_check import FWUpdatePASSCheck
from bat_scripts_new.samba_service_check import SambaServiceCheck
from bat_scripts_new.afp_service_check import AFPServiceCheck
from bat_scripts_new.userroots_mount_check import UserRootsMountOnDevice
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

from functional_tests.device_type import DeviceType
from functional_tests.raid_conversion import RaidConversion
from functional_tests.raid_creation import RaidCreation
from functional_tests.raid_rebuild import RaidRebuild
from functional_tests.update_fw_to_same_version import UpdateFWToSameVersion
from functional_tests.usb_fs import USBFormat
from functional_tests.time_machine import TimeMachine
from functional_tests.led_usb_slurp_test import LEDCheckUSBSlurp
from functional_tests.led_device_ready import LEDCheckDeviceReady
from functional_tests.led_shutdown_test import LEDCheckShutdown
from functional_tests.led_boot_sequence import LEDCheckBootSequence
from functional_tests.led_power_ready import LEDCheckPowerUp
from functional_tests.led_yoda import LEDYoda
from functional_tests.service_check import ServiceCheck
from functional_tests.usb_flash_uboot import USB_Flash_Uboot
from functional_tests.usb_flash_firmware import USB_Flash_Firmware
from functional_tests.wifi.auto_connect_after_wan_recovered import AutoConnectAfterWANRecovered
from functional_tests.wifi.auto_connect_after_wifi_recovered import AutoConnectAfterWiFiRecovered
from functional_tests.reset_button_check import ResetButtonCheck
from functional_tests.system_time_after_reboot import SystemTimeAfterReboot
from functional_tests.log_without_java_exception_on_boot_check import LogWithoutJavaExceptionOnBoot
from functional_tests.log_upload_frequency_check import LogUploadFrequencyCheck
from functional_tests.log_without_local_ip_check import LogWithoutLocalIPCheck
from functional_tests.sumologic_platform_factory_reset_log_generated import SumologicPlatformFactoryReset
from functional_tests.log_filtering_flag_set_true import LogFilteringFlagSetTrue
from functional_tests.sumologic_appmgr_logs_hash_user_id import SumologicAppmgrHashUserID
from functional_tests.sumologic_logging_policy_applied import SumologicLogPolicyApplied
from functional_tests.loguploader_test import LogUploaderTest
from integration_tests.time_machine_stress import TimeMachineBackupRestore
from disk_healthy_monitoring import DiskHealthMonitor
from log_not_uploaded_when_pip_off import LogNotUploadWhenPIPOff
from log_when_device_without_network import LogWhenDeviceWithoutNetwork
from reset_button_reboot_without_user import ResetButtonRebootWithoutUser
from reset_button_reboot_with_user import ResetButtonRebootWithUser
from functional_tests.factory_reset_log_upload_when_pip_on import FactoryResetLogUploadWhenPIPIsOn
from functional_tests.factory_reset_log_upload_when_pip_off import FactoryResetLogUploadWhenPIPIsOff

from transcoding_tests.functional_tests.single_file_transcoding import SingleFileTranscodingTest
from transcoding_tests.functional_tests.ns_single_file_transcoding import NSSingleFileTranscodingTest

# App Manager Test Cases
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


class Functional_Regression_Cycle_P1(IntegrationTest):

    TEST_SUITE = 'Platform_Functional_Sanity_Regression_Test'
    TEST_NAME = 'Platform_Functional_Sanity_Regression_Test'
    REPORT_NAME = 'Sanity'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):

        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            self.integration.add_testcases(testcases=[
                    (FactoryReset, {'no_rest_api': True, 'TEST_NAME': 'KAM-13972: Factory Reset Test'}),
                    (FWUpdatePASSCheck, {'version_check': self.version_check, 'TEST_NAME': 'KAM-13986: Firmware Update Test'}),
                    #(SumologicAppmgrHashUserID, {'TEST_NAME': 'KAM-19735: [ANALYTICS] Hash user id in appmgr logs instead of general MASKED'}),
                    (ResetButtonCheck, {'TEST_NAME': 'KAM-29591: Reset Button do factory reset Check'}),
                    (TimeMachineBackupRestore, {'TEST_NAME': 'KAM-6659 [Time Machine] Backup Integrity Verification (AFP)', 
                                                'inventory_server_ip': 'sevtw-inventory-server.hgst.com', 'mac_os': '10.13', 'server_username':'root', 'server_password':'`1q',
                                                'protocol_type': 'afp', 'loop_times': 1, 'dry_run': True,
                                                'file_server':'10.200.141.26',
                                                'run_models':['monarch', 'pelican'],
                                                'TEST_JIRA_ID': 'KAM-6659',
                                                'mac_root_folder':'MacintoshHD'}),
                    (TimeMachine, {'inventory_server_ip': 'sevtw-inventory-server.hgst.com', 'mac_os': '11.1', 'mac_username': 'root', 'mac_password': 'root', 
                                    'protocol': 'afp', 'data_path': '/Volumes/MyPassport/Incremental', 'backup_pattern': 'newbackup',
                                    'TEST_NAME': 'KAM-36596: [Time Machine] MacOSX 11 - New Backup', 'run_models':['monarch', 'pelican'],
                                    'TEST_JIRA_ID': 'KAM-36596'
                    }),
                    (TimeMachine, {'inventory_server_ip': 'sevtw-inventory-server.hgst.com', 'mac_os': '11.1', 'mac_username': 'root', 'mac_password': 'root',
                                    'protocol': 'afp', 'data_path': '/Volumes/MyPassport/Incremental', 'backup_pattern': 'incremental',
                                    'TEST_NAME': 'KAM-36597: [Time Machine] MacOSX 11 - Incremental Backup', 'run_models':['monarch', 'pelican'],
                                    'TEST_JIRA_ID': 'KAM-36597'
                    }),
                    (TimeMachine, {'inventory_server_ip': 'sevtw-inventory-server.hgst.com', 'mac_os': '10.13', 'mac_username': 'root', 'mac_password': '`1q', 
                                    'protocol': 'afp', 'data_path': '/Volumes/MyPassport/Incremental', 'backup_pattern': 'newbackup',
                                    'TEST_NAME': 'KAM-25153: [Time Machine] MacOSX 10.13 - New Backup', 'run_models':['monarch', 'pelican'],
                                    'TEST_JIRA_ID': 'KAM-25153'
                    }),
                    (TimeMachine, {'inventory_server_ip': 'sevtw-inventory-server.hgst.com', 'mac_os': '10.13', 'mac_username': 'root', 'mac_password': '`1q',
                                   'protocol': 'afp', 'data_path': '/Volumes/MyPassport/Incremental', 'backup_pattern': 'incremental',
                                   'TEST_NAME': 'KAM-25154: [Time Machine] MacOSX 10.13 - Incremental Backup', 'run_models':['monarch', 'pelican'],
                                    'TEST_JIRA_ID': 'KAM-25154'
                    }),
                    (ServiceCheck, {'TEST_NAME': 'KAM-21810: Check Samba daemon is active after factory reset', 'test_protocol': 'smb_after_factory_reset', 'run_models':['monarch', 'pelican']
                        }),
                    (Reboot, {'no_rest_api': True, 'wait_device': True, 'TEST_NAME': 'KAM-13971:  Device Reboot Test', 'disable_clean_logcat_log': True}),
                    (LEDCheckDeviceReady, {'TEST_NAME': 'KAM-23590: [LED] Device Ready'}),
                    (LoadRestsdkmodule, {'TEST_NAME': 'KAM-13968: Rest-sdk Daemon Check'}),
                    (CloudEnvCheck, {'cloud_env': self.env.cloud_env, 'TEST_NAME': 'KAM-13973:  Environment config Check for Cloud Server'}),
                    (UnauthenticatedPortsCheck, {'TEST_NAME':'KAM-29774: Unauthenticated ports check'}),
                    (LoadAPPManager, {'TEST_NAME': 'KAM-13974: App Manager Daemon Check'}),
                    (AvahiServiceCheck, {'TEST_NAME': 'KAM-13975: Avahi Daemon Check'}),
                    (LoadOTAClient, {'enable_auto_ota': True, 'TEST_NAME': 'KAM-13977: OTA Client Daemon Check'}),
                    (UserRootsMountOnDevice, {'TEST_NAME': 'KAM-13978: UserRoots Check'}),
                    (BasicTranscoding, {'TEST_NAME': 'KAM-13982: Transcoding Test', 'run_models':['monarch', 'pelican', 'yodaplus']}),
                    (UsbAutoMount, {'TEST_NAME': 'KAM-13983: USB Auto mount on Device', 'run_models':['monarch', 'pelican', 'yodaplus']}),
                    (UsbSlurpBackupFile, {'TEST_NAME': 'KAM-13984: USB Slurp Backup file Test', 'disable_clean_logcat_log': True, 'run_models':['monarch', 'pelican', 'yodaplus']}),
                    (LEDCheckUSBSlurp, {'TEST_NAME': 'KAM-23591: [LED] Data transfer via USB slurp', 'run_models': ['monarch', 'pelican', 'yodaplus']}),
                    (UsbSlurpDeleteFile, {'TEST_NAME': 'KAM-13985: Delete File on USB Drive', 'run_models':['monarch', 'pelican', 'yodaplus']}),
                    (DataLossCheck, {'TEST_NAME': 'KAM-19884: Move log Script check for Data Loss', 'run_models':['monarch', 'pelican', 'yodaplus']}),
                    (SambaServiceCheck, {'TEST_NAME': 'KAM-13970: Samba Enabled Check'}),
                    (SambaRW, {'TEST_NAME': 'KAM-13981: Samba IO Test', 'run_models':['monarch', 'pelican']}),
                    (DeviceType, {'TEST_NAME': 'KAM-21415: Device type for Monarch and Pelican', 'TEST_JIRA_ID': 'KAM-21415'}),
                    (DeviceType, {'TEST_NAME': 'KAM-23728: Device type for Yoda and Yodaplus', 'TEST_JIRA_ID': 'KAM-23728'}),
                    (TranscodingDisableCheck, {'TEST_NAME': 'KAM-24453: Transcoding Flag Check'}),
                    (CreateUserAttachUser, {'TEST_NAME':'KAM-13980: Create User And Attach User Checked'}),
                    (ADBConnectCheck, {'TEST_NAME':'KAM-13969: Network ADB connection test'}),
                    (CheckCloudService, {'TEST_NAME': 'KAM-13979: Check Cloud Services'}),
                    (UpdateFWToSameVersion, {'TEST_NAME': 'KAM-7138: FW update to same version'}),
                    (USBFormat, {'usb_fs': 'exfat', 'TEST_NAME': 'KAM-14616: [USB Slurp] USB 3.0 - MBR_exFAT', 'run_models':['monarch', 'pelican', 'yodaplus'], 'TEST_JIRA_ID': 'KAM-14616'}),
                    (USBFormat, {'usb_fs': 'ntfs', 'TEST_NAME': 'KAM-8612: [USB Slurp] USB 3.0 - MBR_NTFS', 'run_models':['monarch', 'pelican', 'yodaplus'], 'TEST_JIRA_ID': 'KAM-8612'}),
                    (USBFormat, {'usb_fs': 'hfsplus', 'TEST_NAME': 'KAM-8613: [USB Slurp] USB 3.0 - MBR_HFS+', 'run_models':['monarch', 'pelican', 'yodaplus'], 'TEST_JIRA_ID': 'KAM-8613'}),
                    (USBFormat, {'usb_fs': 'fat32', 'TEST_NAME': 'KAM-8610: [USB Slurp] USB 3.0 - MBR_FAT32', 'run_models':['monarch', 'pelican', 'yodaplus'], 'TEST_JIRA_ID': 'KAM-8610'}),
                    (LEDCheckPowerUp, {'TEST_NAME': 'KAM-7871: [LED] Power State - Ready', 'disable_clean_logcat_log': True}),
                    (LEDCheckShutdown, {'TEST_NAME': 'KAM-8768: [LED] Shutdown through app', 'run_models':['monarch', 'pelican']}),
                    (FactoryResetLogUploadWhenPIPIsOn, {'TEST_NAME': 'KAM-26711: [Factory reset] Factory reset logs are uploaded when PIP is on'}),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-9721: [Transcode] 4K H265 AAC 60_30_24FPS to 1080P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/4K_H.265_30fps.mp4',
                        'target_container': 'matroska', 'target_resolution': '1080p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-9721'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-9722: [Transcode] 4K H.265 AAC 60_30_24FPS to 720P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/4K_H.265_30fps.mp4',
                        'target_container': 'matroska', 'target_resolution': '720p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-9722'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-9723: [Transcode] 4K H.265 AAC 60_30_24FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/4K_H.265_30fps.mp4',
                        'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-9723'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-9733: [Transcode] 4K VP9 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/4K_VP9.webm',
                        'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-9733'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-9736: [Transcode] 1080P H.264 30FPS to 720P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_H.264.mp4',
                        'target_container': 'matroska', 'target_resolution': '720p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-9736'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-9740: [Transcode] 1080P VP9 30FPS to 720P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_VP9.webm',
                        'target_container': 'matroska', 'target_resolution': '720p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-9740'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-11052: [Transcode] 1080P H.264 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_H.264.mp4',
                        'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-11052'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-11073: [Transcode] 1080P VP9 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_VP9.webm',
                        'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-11073'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-11104: [Transcode] 4K H.265 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/4K_H.265_30fps.mp4',
                        'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-11104'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-11155: [Transcode] 1080P MPEG4 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_MPEG4.mp4',
                        'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-11155'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-11188: [Transcode] 720P H.264 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/720P_H.264.mp4',
                        'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-11188'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-11212: [Transcode] 720P, MPEG4+AC3+60_30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/720P_MPEG4_ac3.m4v',
                        'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-11212'
                    }),
                    (SingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-11051: [Transcode] 1080P, H.264+AC3+30FPS to 720P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_H.264_ac3.m4v',
                        'target_container': 'matroska', 'target_resolution': '720p', 'run_models':['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-11051'
                    }),
                    (NSSingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-17412: [Transcode] Does not support source video file MPEG2 transcoding', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/480P_MPEG2_AAC_30FPS.mkv',
                        'target_container': 'matroska', 'target_resolution': '480p', 'duration': 5000, 'run_models': ['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-17412'
                    }),
                    (NSSingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-18091: [Transcode] Monarch does not support 4K source file', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/4K_H264.mp4',
                        'target_container': 'matroska', 'target_resolution': '480p', 'duration': 5000, 'run_models': ['monarch'],
                        'TEST_JIRA_ID': 'KAM-18091'
                    }),
                    (NSSingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-18051: [Transcode] Monarch does not support H.265 source file', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/480P_H265_AAC_30FPS.mkv',
                        'target_container': 'matroska', 'target_resolution': '480p', 'duration': 5000, 'run_models': ['monarch'],
                        'TEST_JIRA_ID': 'KAM-18051'
                    }),
                    (NSSingleFileTranscodingTest, {
                        'TEST_NAME': 'KAM-18052: [Transcode] Does not support VP8 source video file', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                        'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/480P_VP8_WMAV1_30FPS.mkv',
                        'target_container': 'matroska', 'target_resolution': '480p', 'duration': 5000, 'run_models': ['monarch', 'pelican', 'yodaplus'],
                        'TEST_JIRA_ID': 'KAM-18052'
                    }),
                    (FactoryResetLogUploadWhenPIPIsOff, {'TEST_NAME': 'KAM-26710: [Factory reset] Factory reset logs are uploaded even PIP is off'}),
                    (ResetButtonRebootWithoutUser, {}),
                    (ResetButtonRebootWithUser, {}),
                    (DiskHealthMonitor, {}),
                    (LogNotUploadWhenPIPOff, {}),
                    (LogWhenDeviceWithoutNetwork, {}),
                    (USB_Flash_Firmware, {'TEST_NAME': 'KAM-7944 Image Upgrade - Monarch', 'file_server': '10.200.141.26', 'img_version': self.env.UUT_firmware_version, 'img_env': self.env.cloud_env, 'img_var': self.env.cloud_variant, 'run_models':['monarch'], 'TEST_JIRA_ID': 'KAM-7944'}), 
                    (USB_Flash_Firmware, {'TEST_NAME': 'KAM-7945 Image Upgrade - Pelican', 'file_server': '10.200.141.26', 'img_version': self.env.UUT_firmware_version, 'img_env': self.env.cloud_env, 'img_var': self.env.cloud_variant, 'run_models':['pelican'], 'TEST_JIRA_ID': 'KAM-7945'}),
                    (RaidConversion, {'raid_type': 'stripe', 'TEST_NAME': 'KAM-18889: Convert RAID 1 to JBOD', 'run_models':['pelican'], 'TEST_JIRA_ID': 'KAM-18889'}),
                    (RaidConversion, {'raid_type': 'mirror', 'TEST_NAME': 'KAM-18901: Convert JBOD to RAID 1', 'run_models':['pelican'], 'TEST_JIRA_ID': 'KAM-18901'}),
                    (RaidCreation, {'TEST_NAME': 'KAM-7948: RAID1 Creation - 2Bay', 'run_models':['pelican']}),
                    (RaidRebuild, {'TEST_NAME': 'KAM-7949: RAID1 Rebuild - 2Bay', 'failed_disk':'sataa2','run_models':['pelican']}),
                    (LogWithoutJavaExceptionOnBoot, {'TEST_NAME': 'KAM-21404: Confirm platform console log without Java exception on boot'}),
                    (LogUploadFrequencyCheck, {'TEST_NAME': 'KAM-21401: Check Log upload frequency'}),
                    (LogWithoutLocalIPCheck, {'TEST_NAME': 'KAM-21400: Local IP being leaked in logs'}),
                    (SumologicPlatformFactoryReset, {'TEST_NAME': 'KAM-19769: [ANALYTICS] Factory reset log generated by platform should be uploaded'}),
                    (LogFilteringFlagSetTrue, {'TEST_NAME': 'KAM-18068: Log filtering flag property is set on devices'}),
                    (SumologicLogPolicyApplied, {'TEST_NAME': "KAM-19734: Logging policy files applied on uploaded logs"}),
                    (LogUploaderTest, {'TEST_NAME': 'KAM-17894: Log upload when PIP is enabled'}),
                    # IMPORTANT: Leave USB flash image test cases at the buttom, if the test failed, all the rest of cases will be failed too
                    # Use file_server IP in MV-Warrior
                    (USB_Flash_Uboot, {'TEST_NAME': 'KAM-7943 U-boot Upgrade', 'file_server': '10.200.141.26', 'run_models':['monarch', 'pelican', 'yodaplus']}),
                    
                    # App Manager Test
                    # Non-Concurrency test cases
                    #(InstallApp, {'app_id': self.app_id, 'check_app_install': True}),
                    #(UninstallApp, {'app_id': self.app_id, 'check_pm_list': True}),
                    # Mark following two test cases becasue they are always skipped in TW lab.
                    #(InstallAppCPUFullLoaded, {'app_id': self.app_id, 'check_app_install': True}),
                    #(UninstallAppCPUFullLoaded, {'app_id': self.app_id, 'check_pm_list': True}),
                    #(InstallAppReboot, {'app_id': self.app_id, 'check_app_install': True, 'uninstall_app':True}),
                    #(RemoveUserWhoInstalledApp, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_pm_list': True}),
                    #(AppUpdateCheck, {'uninstall_app': True}),
                    
                    # Concurrency Install test cases
                    #(ConcurrentInstallDifferentAppMultipleUsers, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                    #(ConcurrentInstallSameAppMultipleUsers, {'app_id': self.app_id, 'check_app_install': True}),
                    #(ConcurrentInstallMultipleAppAdminUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                    #(ConcurrentInstallMultipleAppSecondUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                    #(ConcurrentInstallSameAppDuringUploadDataMultipleUsers, {'app_id': self.app_id, 'check_app_install': True}),
                    
                    # Concurrency Uninstall test cases
                    #(ConcurrentUninstallDifferentAppMultipleUsers, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_pm_list': True}),
                    #(ConcurrentUninstallSameAppMultipleUsers, {'app_id': self.app_id, 'check_pm_list': True}),
                    #(ConcurrentUninstallMultipleAppAdminUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_pm_list': True}),
                    #(ConcurrentUninstallMultipleAppSecondUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_pm_list': True}),
                    
                    # Concurrency Install & Uninstall test cases
                    #(ConcurrentInstallUninstallDifferentAppAdminUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                    #(ConcurrentInstallUninstallDifferentAppSecondUser, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                    #(ConcurrentInstallUninstallAppMultipleUsersDifferentApp, {'app_id_1': self.app_id, 'app_id_2': self.app_id_2, 'check_app_install': True}),
                    #(ConcurrentInstallUninstallAppMultipleUsersSameApp, {'app_id': self.app_id, 'check_app_install': True}),
                    # Concurrency with other process test cases
                    #(RebootSystemDuringInstallApp, {'app_id': self.app_id, 'check_app_install': True}),
                    #(RebootSystemDuringUninstallApp, {'app_id': self.app_id}),
                    #(InstallAppDuringUSBSlurp, {'app_id': self.app_id, 'check_app_install': True, 'download_usb_slurp_files':True}),
                    #(UninstallAppDuringUSBSlurp, {'app_id': self.app_id, 'check_pm_list': True, 'download_usb_slurp_files':False, 'delete_download_files':True}),
                    #(InstallAppDuringUploadData, {'app_id': self.app_id, 'check_app_install': True}),
                    #(UninstallAppDuringUploadData, {'app_id': self.app_id, 'check_pm_list': True}),
                    #(InstallAppDuringFWFlash, {'app_id': self.app_id, 'check_app_install': True}),
                    #(UninstallAppDuringFWFlash, {'app_id': self.app_id, 'check_pm_list': True}),
            ])


if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** Functional_Regression_Cycle_P1 Running script ***
        Examples: ./start.sh functional_tests/regression_p1 --uut_ip 10.92.224.68 -env dev1\
        """)

    # Test Arguments
    parser.add_argument('--version_check', help='firmware version to compare')
    parser.add_argument('--single_run', help='Run single case for Yoda BAT')
    parser.add_argument('--file_server', help='File server IP address', default='10.200.141.26')
    parser.add_argument('--uboot_version', help='The test uboot version')
    # For App Manager test
    parser.add_argument('-appid', '--app_id', help='App ID to installed', required=True)
    parser.add_argument('-appid2', '--app_id_2', help='Second App ID to installed', required=True)

    test = Functional_Regression_Cycle_P1(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
