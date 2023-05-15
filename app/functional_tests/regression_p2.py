# -*- coding: utf-8 -*-
""" Platform Functional Regression Cycle P2 test.
"""
__author__ = "Ben Lin <ben.lin@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
# Sub-tests
from functional_tests.cron_move_log import CronJobMoveLog
from functional_tests.log_upload_frequency_check import LogUploadFrequencyCheck
from functional_tests.log_without_local_ip_check import LogWithoutLocalIPCheck
from functional_tests.reset_button_factory_reset_softap_mode import FactoryResetSoftAPMode
from functional_tests.reset_button_device_owner_softap_mode import FactoryResetDemoteSoftAPMode
from functional_tests.log_without_java_exception_on_boot_check import LogWithoutJavaExceptionOnBoot
from functional_tests.confirm_afp_disabled import ConfirmAFPDisabled
from functional_tests.shutdown_device import ShutdownDevice
from functional_tests.lost_power_test import LostPower
from functional_tests.led_factory_reset import LEDFactoryReset
from functional_tests.loguploader_test import LogUploaderTest
from functional_tests.reset_button_softap_to_client_mode import SoftAPToClientMode
from functional_tests.led_device_reset import LEDDeviceReset
from functional_tests.remove_personal_information import RemovePersonalInfomation
from functional_tests.check_debug_logs import CheckDebugLogs
from functional_tests.led_shutdown_test import LEDCheckShutdown
from functional_tests.press_reset_button_60secs import PressResetButton60secs
from functional_tests.sumologic_upload_log_before_reboot import SumologicUploadBeforeReboot
from functional_tests.confirm_smb_disabled import ConfirmSMBDisabled
from functional_tests.sumologic_platform_factory_reset_log_generated import SumologicPlatformFactoryReset
from functional_tests.factory_reset_log_upload_when_pip_on import FactoryResetLogUploadWhenPIPIsOn
from functional_tests.factory_reset_log_upload_when_pip_off import FactoryResetLogUploadWhenPIPIsOff
from functional_tests.led_yoda import LEDYoda
from functional_tests.sumologic_appmgr_logs_hash_user_id import SumologicAppmgrHashUserID
from functional_tests.log_filtering_flag_set_true import LogFilteringFlagSetTrue
from functional_tests.wifi_change_5G_verify import WifiChange5GVerify
from functional_tests.wifi_change_2G_verify import WifiChange2GVerify
from functional_tests.connect_5G_after_reboot import Connect5GAfterReboot
from functional_tests.connect_2G_after_reboot import Connect2GAfterReboot
from functional_tests.connect_5G import Connect5GAfterReset
from functional_tests.device_type import DeviceType
from functional_tests.abnormal_shutdown_in_softap_mode import AbnormalShutdownInSoftAP
from functional_tests.sumologic_logging_policy_applied import SumologicLogPolicyApplied
from functional_tests.cron_upload_logs_to_sumologic_check import CronUploadLogsToSumologicCheck
from functional_tests.led_fw_update import LEDCheckUpdateFW
from functional_tests.log_kernel_crash_check import LogKernelCrashCheck
from functional_tests.sumologic_filter_out_PII_data import SumologicFilterOutPIIData
from functional_tests.check_debug_logs_without_wan import CheckDebugLogsWithoutWan
from functional_tests.p2_auto_connect_after_wan_recovered import AutoConnectAfterWANRecovered
from functional_tests.p2_auto_connect_after_wifi_recovered import AutoConnectAfterWiFiRecovered
from functional_tests.log_upload_after_wifi_back import LogUploadAfterWIFIBack

class Functional_Regression_Cycle_P2(IntegrationTest):

    TEST_SUITE = 'Platform_Functional_Regression_Cycle'
    TEST_NAME = 'Platform_Functional_Regression_Cycle_P2'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            model = self.adb.getModel()
            if model == 'yodaplus':
                sn = 'YODA-PLUS'
                wifi_ssid_2_4G = 'A1-2.4G-dd-wrt'
                wifi_ssid_5G = 'A1-5G-dd-wrt'
            elif model == 'yoda':
                sn = 'YODA-YODA'
                wifi_ssid_2_4G = 'A2-2.4G-dd-wrt'
                wifi_ssid_5G = 'A2-5G-dd-wrt'
            else:
                sn = None
                wifi_ssid_2_4G = None
                wifi_ssid_5G = None  

            self.integration.add_testcases(testcases=[
                    (CronJobMoveLog, {'TEST_NAME': 'KAM-17602: Cron job moves device logs every 15 minutes when disk is mounted'}),
                    (LogUploadFrequencyCheck, {'TEST_NAME': 'KAM-21401: Check Log upload frequency'}),
                    (LogWithoutLocalIPCheck, {'TEST_NAME': 'KAM-21400: Local IP being leaked in logs'}),
                    (FactoryResetSoftAPMode, {'TEST_NAME': 'KAM-24052: Rest button - Do Factory reset while device in SoftAP mode','mac_server_ip': '192.168.1.165', 'mac_username': 'root', 'mac_password': '`1q'}),
                    (FactoryResetDemoteSoftAPMode, {'TEST_NAME': 'KAM-25155: Rest button - Do demote device owner while device in SoftAP mode','mac_server_ip': '192.168.1.165', 'mac_username': 'root', 'mac_password': '`1q'}),
                    (LogWithoutJavaExceptionOnBoot, {'TEST_NAME': 'KAM-21404: Confirm platform console/log without Java exception on boot'}),
                    (ConfirmAFPDisabled, {'TEST_NAME': 'KAM-24226: Confirm AFP protocol has been disabled in both Yoda and Yoda+','mac_server_ip': '192.168.1.165', 'mac_username': 'root', 'mac_password': '`1q'}),
                    (ShutdownDevice, {'TEST_NAME': 'KAM-7875: Power State - Power Up after Graceful Shutdown'}),
                    (LostPower, {'TEST_NAME': 'KAM-7873: Power State - Lost Power from Ready mode'}),
                    (LEDFactoryReset, {'TEST_NAME': 'KAM-24686: [LED] YODA - Factory reset'}),
                    (LogUploaderTest, {'TEST_NAME': 'KAM-17894: Log upload when PIP is enabled'}),
                    (SoftAPToClientMode, {'TEST_NAME': 'KAM-24051: Reset button - SoftAP mode','mac_server_ip': '192.168.1.165', 'mac_username': 'root', 'mac_password': '`1q'}),
                    (LEDDeviceReset, {'TEST_NAME': 'KAM-8767: [LED] Device reset'}),
                    (RemovePersonalInfomation, {'TEST_NAME': 'KAM-18208: Remove Personal Identification Information from Platform verification'}),
                    (CheckDebugLogs, {'TEST_NAME': 'KAM-21695 [On demand logging] Local endpoint access to generate and export debug_logs file'}),
                    (LEDCheckShutdown, {'TEST_NAME': 'KAM-8768: [LED] Shutdown through app', 'run_models':['yoda', 'yodaplus']}),
                    (PressResetButton60secs, {'TEST_NAME': 'KAM-14703: [Factory reset] Press Reset Button >= 60 secs : Factory reset'}),
                    (SumologicUploadBeforeReboot, {'TEST_NAME': 'KAM-26712: Logs are uploaded before device reboot'}),
                    (ConfirmSMBDisabled, {'TEST_NAME': 'KAM-23480: Confirm Samba protocol has been disabled in both Yoda and Yoda+','mac_server_ip': '192.168.1.165', 'mac_username': 'root', 'mac_password': '`1q'}),
                    (SumologicPlatformFactoryReset, {'TEST_NAME': 'KAM-19769: [ANALYTICS] Factory reset log generated by platform should be uploaded'}),
                    (FactoryResetLogUploadWhenPIPIsOn, {'TEST_NAME': 'KAM-26711: [Factory reset] Factory reset logs are uploaded when PIP is on'}),
                    (FactoryResetLogUploadWhenPIPIsOff, {'TEST_NAME': 'KAM-26710: [Factory reset] Factory reset logs are uploaded even PIP is off'}),
                    (LEDYoda, {'TEST_NAME': 'KAM-24657: [LED] YODA - Powerup and Initializing', 'led_test_case': 'power_up'}),
                    (SumologicAppmgrHashUserID, {'TEST_NAME': 'KAM-19735: [ANALYTICS] Hash user id in appmgr logs instead of general MASKED'}),
                    (LogFilteringFlagSetTrue, {'TEST_NAME': 'KAM-18068: Log filtering flag property is set on devices'}),
                    (WifiChange5GVerify, {'TEST_NAME': 'KAM-23835: Change connect Wi-Fi AP 5G to 2.4G','wifi_ssid_5g':self.wifi_5G_ssid,'wifi_5g_password':self.wifi_5G_password,'wifi_ssid_2g':self.wifi_2G_ssid,'wifi_2g_password':self.wifi_2G_password}),
                    (WifiChange2GVerify, {'TEST_NAME': 'KAM-23834: Change connect Wi-Fi AP 2.4G to 5G','wifi_ssid_5g':self.wifi_5G_ssid,'wifi_5g_password':self.wifi_5G_password,'wifi_ssid_2g':self.wifi_2G_ssid,'wifi_2g_password':self.wifi_2G_password}),
                    (Connect5GAfterReboot, {'TEST_NAME': 'KAM-23837: Auto connect Wi-Fi AP 5G after YODA restart','wifi_ssid_5g':self.wifi_5G_ssid,'wifi_5g_password':self.wifi_5G_password,'wifi_ssid_2g':self.wifi_2G_ssid,'wifi_2g_password':self.wifi_2G_password}),
                    (Connect2GAfterReboot, {'TEST_NAME': 'KAM-23836: Auto connect Wi-Fi AP 2.4G after YODA restart','wifi_ssid_5g':self.wifi_5G_ssid,'wifi_5g_password':self.wifi_5G_password,'wifi_ssid_2g':self.wifi_2G_ssid,'wifi_2g_password':self.wifi_2G_password}),
                    (Connect5GAfterReset, {'TEST_NAME': 'KAM-23831: Connect Wi-Fi AP 5G','wifi_ssid_5g':self.wifi_5G_ssid,'wifi_5g_password':self.wifi_5G_password,'wifi_ssid_2g':self.wifi_2G_ssid,'wifi_2g_password':self.wifi_2G_password}),
                    (LEDCheckUpdateFW, {'TEST_NAME': 'KAM-8766: [LED] Firmware update'}),
                    (AbnormalShutdownInSoftAP, {'TEST_NAME': 'KAM-27071: Abnormal shutdown while device in SoftAP mode and has W-Fi setting before'}),
                    (SumologicLogPolicyApplied, {'TEST_NAME': "KAM-19734: Logging policy files applied on uploaded logs"}),
                    (CronUploadLogsToSumologicCheck, {'TEST_NAME': "KAM-17604: Cron job uploads device logs to Sumologic"}),
                    (CheckDebugLogsWithoutWan, {'TEST_NAME': 'KAM-22184: Local endpoint access to generate and export debug_logs file on Monarch just has local LAN, no WAN','ap_power_port': self.ap_power_port,'test_2_4G_ssid':self.test_2_4G_ssid,'test_2_4G_password':self.test_2_4G_password}),
                    (AutoConnectAfterWANRecovered, {'TEST_NAME': 'KAM-24659: [LED] YODA - Wifi connection available, No Cloud Connect','ap_power_port': self.ap_power_port,'test_2_4G_ssid': self.test_2_4G_ssid,'test_2_4G_password': self.test_2_4G_password}),
                    (AutoConnectAfterWiFiRecovered, {'TEST_NAME': 'KAM-24658: [LED] YODA - WIFI connection not available','ap_power_port': self.ap_power_port,'test_2_4G_ssid':self.test_2_4G_ssid,'test_2_4G_password':self.test_2_4G_password,'ap_power_switch_ip': self.ap_power_switch_ip}),
                    (LogUploadAfterWIFIBack, {'TEST_NAME': 'KAM-29233: Logs will be uploaded after wifi disconnect and reconnect back.','ap_power_port': self.ap_power_port,'test_2_4G_ssid':self.test_2_4G_ssid,'test_2_4G_password':self.test_2_4G_password,'ap_power_switch_ip': self.ap_power_switch_ip}),
                    (SumologicFilterOutPIIData, {'TEST_NAME': 'KAM-18971: Uploaded device logs filter out PII data'}),
                    (DeviceType, {'TEST_NAME': 'KAM-23728 Device type for YODA and YODA+'})
            ])

if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** Functional_Regression_Cycle_P2 Running script ***
        Examples: ./start.sh functional_tests/regression_p2 --uut_ip 10.92.224.68 -env dev1\
        """)

    # Test Arguments
    parser.add_argument('--version_check', help='firmware version to compare')
    parser.add_argument('--single_run', help='Run single case for Yoda BAT')
    parser.add_argument('--file_server', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--uboot_version', help='The test uboot version')
    # For DD-WRT settings
    parser.add_argument('-app', '--ap_power_port', help='AP port on power switch', metavar='PORT', type=int)
    parser.add_argument('-aps', '--ap_power_switch_ip', help='Power Switch IP Address', metavar='IP')
    parser.add_argument('-24Gssid', '--test_2_4G_ssid', help='AP SSID for 2.4G test', metavar='SSID')
    parser.add_argument('-24Gpw', '--test_2_4G_password', help='AP password for 2.4G test', metavar='PWD')
    parser.add_argument('-24Gsm', '--test_2_4G_security_mode', help='Security mode for 2.4G test', metavar='MODE', default='psk2')
    parser.add_argument('-5Gssid', '--test_5G_ssid', help='AP SSID for 5G test', metavar='SSID')
    parser.add_argument('-5Gpw', '--test_5G_password', help='AP password for 5G test', metavar='PWD')
    parser.add_argument('-5Gsm', '--test_5G_security_mode', help='Security mode for 5G test', metavar='MODE', default='psk2')
    parser.add_argument('-wifi5Gssid', '--wifi_5G_ssid', help='WIFI 5G SSID for non-ddwrt', metavar='MODE', default='SSID')
    parser.add_argument('-wifi2Gssid', '--wifi_2G_ssid', help='WIFI 2G SSID for non-ddwrt', metavar='MODE', default='SSID')
    parser.add_argument('-wifi5Gpw', '--wifi_5G_password', help='AP password for 5G test on non-ddwrt', metavar='PWD')
    parser.add_argument('-wifi2Gpw', '--wifi_2G_password', help='AP password for 2G test on non-ddwrt', metavar='PWD')

    test = Functional_Regression_Cycle_P2(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
