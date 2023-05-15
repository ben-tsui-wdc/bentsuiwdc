# -*- coding: utf-8 -*-
""" Mean Time Between Failure test.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import os
import sys
import time
# platform modules
from middleware.arguments import KDPIntegrationTestArgument
from middleware.kdp_integration_test import KDPIntegrationTest
# Sub-tests
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
from kdp_scripts.bat_scripts.factory_reset import FactoryReset
from kdp_scripts.bat_scripts.check_appmgr_service import CheckAppManagerService
from kdp_scripts.bat_scripts.afp_service_disable_check import AFPServiceDisableCheck
from kdp_scripts.bat_scripts.transcoding_flag_check import TranscodingFlagCheck
from kdp_scripts.bat_scripts.timesync_http_fallback import TimeSyncHTTPFallback
from kdp_scripts.functional_tests.app_manager.install_app import InstallApp
from kdp_scripts.functional_tests.app_manager.uninstall_app import UninstallApp
from kdp_scripts.bat_scripts.usb_auto_mount import UsbAutoMount
from kdp_scripts.bat_scripts.usb_slurp_backup_file import UsbSlurpBackupFile
from kdp_scripts.bat_scripts.usb_slurp_delete_file import UsbSlurpDeleteFile
# functional
from kdp_scripts.functional_tests.storage.raid_conversion import RaidConversion
from kdp_scripts.functional_tests.led.led_usb_slurp_test import LEDCheckUSBSlurp
from kdp_scripts.functional_tests.analytics.check_force_log_rotate import CheckForceLogRotate
from kdp_scripts.functional_tests.analytics.check_force_log_rotate_negative import CheckForceLogRotateNegative
from kdp_scripts.functional_tests.analytics.check_max_rotate_log_number import CheckMaxRotateLogNumber
from kdp_scripts.functional_tests.analytics.check_normal_log_rotate import CheckNormalLogRotate
from kdp_scripts.functional_tests.analytics.check_normal_log_rotate_negative import CheckNormalLogRotateNegative
from kdp_scripts.functional_tests.analytics.local_endpoint_export_debug_logs import LocalEndpointCanExportDebugLogs
# stress
from kdp_scripts.stress_tests.ffmpeg_stress import FFmpegStress
from kdp_scripts.stress_tests.usb_slurp_sync_stress import USBSlurpSyncStress

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
        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
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
                    LoadOTAClient,
                    LoadRestsdkmodule,
                    TranscodingFlagCheck,
                    CreateUserAttachUser,
                    OtaclientConfigM2MCheck,
                    RestsdkConfigM2MCheck,
                    SambaServiceCheck,
                    (Reboot, {'TEST_NAME': 'KDP-200 - Device Reboot Test with ssh command', 
                        'TEST_JIRA_ID': 'KDP-200,KDP-1009,KDP-1010,KDP-3296,KDP-1015,KDP-1178,KDP-1936,KDP-3293,KDP-3294,KDP-3295'}),
                    (Reboot, {'no_rest_api': False, 'TEST_NAME': 'KDP-1008 - Device Reboot Test via restapi request', 
                        'TEST_JIRA_ID': 'KDP-1008,KDP-1009,KDP-1010,KDP-3296,KDP-1015,KDP-1178,KDP-1936,KDP-3293,KDP-3294,KDP-3295,KDP-3297,KDP-3298'}),
                    OTAProxyCheck,
                    UnauthenticatedPortsCheck,
                    UsbAutoMount,
                    UsbSlurpBackupFile,
                    UsbSlurpDeleteFile,
                    RestSDKAutoRestart
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
                    LoadOTAClient,
                    LoadRestsdkmodule,
                    TranscodingFlagCheck,
                    CreateUserAttachUser,
                    OtaclientConfigM2MCheck,
                    RestsdkConfigM2MCheck,
                    (InstallApp, {'app_id': self.app_id, 'check_app_install':True}),
                    (UninstallApp, {'app_id': self.app_id}),
                    SambaServiceCheck,
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
                    (RaidConversion, {'raid_type':'span,mirror', 'attach_owner': True, 'read_write_check':True, 'TEST_JIRA_ID':'KDP-526'}),
                    (RaidConversion, {'raid_type':'mirror,span', 'attach_owner': True, 'read_write_check':True, 'TEST_JIRA_ID':'KDP-523'}),
                    CheckForceLogRotate,
                    CheckForceLogRotateNegative,
                    CheckMaxRotateLogNumber,
                    CheckNormalLogRotate,
                    CheckNormalLogRotateNegative,
                    LocalEndpointCanExportDebugLogs,
                    (FFmpegStress, {'file_donwload_url':'http://10.200.141.26/test/FFmpegStress/', 'loop_times':1}),
                    LEDCheckUSBSlurp,
                    #(FFmpegStress, {'file_donwload_url':'http://fileserver.hgst.com/test/FFmpegStress/', 'loop_times':1}),
                    (USBSlurpSyncStress, {'folder_name':'usb_slurp_stress_dataset', 'loop_times':1})
                ])


    def after_test(self):
        self.log.warning('Calculate the number of Pass/Fail here and generate a report.')
        # The following is for html report on Jenkins
        test_result_dict = {}
        """
        Example:
            {'test_name': {'pass':2, 'fail':4}}
        """
        #for test_result in self.test_result_list:
        for item in self.data.test_result:
            #print item.TEST_NAME, item.TEST_PASS
            #print type(item.TEST_PASS)
            if not test_result_dict.get(item.TEST_NAME):
                test_result_dict[item.TEST_NAME] = {'pass':0, 'fail':0}
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
        HTML_RESULT += '<tr><th>Test Name</th><th>Iterations</th><th>PASS</th><th>FAIL</th></tr>'  # Title column
        # Calculate the number of total iterations after all test items are printed
        '''
        Example:
            <tr><td>Factory_Reset_Test</td><td>20</td><td>15</td><td>5</td></tr>
        '''
        total_pass = 0
        total_fail = 0
        for item in test_result_dict:
            HTML_RESULT += '<tr>'
            total_pass += test_result_dict[item]['pass']
            total_fail += test_result_dict[item]['fail']
            itr_per_item = test_result_dict[item]['pass'] + test_result_dict[item]['fail']
            HTML_RESULT += "<td>{}</td><td>{}</td><td class='pass'>{}</td><td class='fail'>{}</td>".format(item, itr_per_item, test_result_dict[item]['pass'], test_result_dict[item]['fail'])
            HTML_RESULT += '</tr>'
        HTML_RESULT += '<tr>'
        HTML_RESULT += "<td>TOTAL</td><td>{}</td><td class='pass'>{}</td><td class='fail'>{}</td>".format(total_pass+total_fail, total_pass, total_fail)
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
    parser.add_argument('--app_id', help='App ID for install and uninstall app test', default='com.wdc.filebrowser')
    parser.add_argument('--file_server', help='File server IP address', default='fileserver.hgst.com')


    test = MTBF(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
