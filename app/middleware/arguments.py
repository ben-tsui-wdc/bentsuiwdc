# -*- coding: utf-8 -*-
""" Argument tools for Test Case. 
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import ast
import logging
from argparse import ArgumentParser, RawTextHelpFormatter
from textwrap import dedent
# platform modules
from platform_libraries.constants import LOGSTASH_SERVER_TW
from platform_libraries.pyutils import NoResult


class CoreInputArgumentParser(ArgumentParser):
    """ Wrap ArgumentParser with setting bulitin common arguments for Test Case. """

    def __init__(self, description, **kwargs):
        """ Pass other arguments only with kwargs. """
        kwargs['description'] = dedent(description) # Only "description" fixed.
        kwargs['formatter_class'] = kwargs.get('formatter_class', RawTextHelpFormatter)
        super(CoreInputArgumentParser, self).__init__(**kwargs)
        self.init_bulitin_args()
        self.init_integration_bulitin_args()

    def init_bulitin_args(self):
        # Environment Settings
        self.add_argument('-lsu', '--logstash_server_url', help='Logstash server URL', metavar='URL', default=LOGSTASH_SERVER_TW)
        # Execution Settings
        self.add_argument('-dr', '--dry_run', help='Local test mode, will not upload result to logstash server', action='store_true', default=False)
        self.add_argument('-lt', '--loop_times', help='How many test iterations', metavar='NUMBER', type=int, default=None)
        self.add_argument('-ltf', '--loop_times_from', help='Start index of test iterations', metavar='NUMBER', type=int, default=1)
        # Bulitin Feature Settings
        self.add_argument('-dsr', '--disable_save_result', help='Not save test result to file', action='store_true', default=False)
        self.add_argument('-dul', '--disable_upload_logs', help='Not upload output folder to server', action='store_true', default=False)
        self.add_argument('-dpe', '--disable_print_errors', help='Not print test errors at end of test', action='store_true', default=False)
        self.add_argument('-sll', '--stream_log_level', help='Log level of print out message', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        self.add_argument('-debug', '--debug_middleware', help='Print debug messages of middleware', action='store_true', default=False)
        self.add_argument('-ref', '--run_even_failure', help='Keep run looping even there is any sub-test failed', action='store_true', default=False)
        # Folders/Files Settings (Maybe these are not necessary )
        self.add_argument('-ln', '--logcat_name', help='Destination file name of logcat log', metavar='NAME', default='logcat')
        self.add_argument('-rf', '--results_folder', help='Destination relative path of test results folder', metavar='PATH', default='output/results')
        self.add_argument('-of', '--output_folder', help='Destination relative path of output results folder', metavar='PATH', default='output')
        self.add_argument('-lrn', '--loop_result_name', help='test_report.xml', default='')
        self.add_argument('-trp', '--test_result_prefix', help='test_name_1.json', default='')
        # Replace bulitin values.
        self.add_argument('-test_name', '--TEST_NAME', help='Replace TEST_NAME', metavar='TEST_NAME', default=None)
        self.add_argument('-test_suite', '--TEST_SUITE', help='Replace TEST_SUITE', metavar='TEST_SUITE', default=None)
        self.add_argument('-set', '--Settings', action='append', help='Set feature flags. e.g., adb=False', metavar='Name=Boolean', default=None)
        # Popcorn report values.
        self.add_argument('-dpr', '--disable_popcorn_report', help='Not generate Popcorn report', action='store_true', default=False)
        self.add_argument('-dupr', '--disable_upload_popcorn_report', help='Will not upload popcorn result to server', action='store_true', default=False)
        self.add_argument('-ppj', '--popcorn_project', help='Replace PROJECT', metavar='PROJECT', default=None)
        self.add_argument('-ppf', '--popcorn_platform', help='Replace PLATFORM', metavar='PLATFORM', default=None)
        self.add_argument('-ptt', '--popcorn_test_type', help='Replace TEST_TYPE', metavar='TEST_TYPE', default=None)
        self.add_argument('-ptj', '--popcorn_test_jira_id', help='Replace TEST_JIRA_ID', metavar='TEST_JIRA_ID', default=None)
        self.add_argument('-ppr', '--popcorn_priority', help='Replace PRIORITY', metavar='PRIORITY', default=None)
        self.add_argument('-pc', '--popcorn_component', help='Replace COMPONENT', metavar='COMPONENT', default=None)
        self.add_argument('-pv', '--popcorn_version', help='Replace VERSION', metavar='VERSION', default=None)
        self.add_argument('-pb', '--popcorn_build', help='Replace BUILD', metavar='BUILD', default=None)
        self.add_argument('-pfw', '--popcorn_fwbuild', help='Replace fwBuild', metavar='FW_BUILD', default=None)
        self.add_argument('-pij', '--popcorn_issue_jira_id', help='Replace ISSUE_JIRA_ID', metavar='ISSUE_JIRA_ID', default=None)
        self.add_argument('-pe', '--popcorn_enviroment', help='Replace ENVIROMENT', metavar='ENVIROMENT', default=None)
        self.add_argument('-pu', '--popcorn_user', help='Replace USER', metavar='USER', default=None)
        self.add_argument('-pon', '--popcorn_os_name', help='Replace OS_NAME', metavar='OS_NAME', default=None)
        self.add_argument('-pov', '--popcorn_os_version', help='Replace OS_VERSION', metavar='OS_VERSION', default=None)
        self.add_argument('-pbl', '--popcorn_build_url', help='Replace BUILD_URL', metavar='BUILD_URL', default=None)
        self.add_argument('-ps', '--popcorn_source', help='Replace POPCORN_SOURCE', metavar='POPCORN_SOURCE', default='PLATFORM')
        self.add_argument('-pse', '--popcorn_skip_error', help='Skip errors on Popcorn report', action='store_true', default=False)
        self.add_argument('-prn', '--popcorn_report_name', help='Replace REPORT_NAME', metavar='REPORT_NAME', default=None)


    def init_integration_bulitin_args(self):
        pass

class InputArgumentParser(CoreInputArgumentParser):
    """ Wrap ArgumentParser with setting bulitin common arguments for Kamino Test Case. """

    def init_bulitin_args(self):
        super(InputArgumentParser, self).init_bulitin_args()
        # UUT Settings
        self.add_argument('-ip', '--uut_ip', help='Destination UUT IP address', metavar='IP')
        self.add_argument('-port', '--uut_port', help='Destination UUT port', type=int, metavar='PORT', default=5555)
        # ADB Settings (Default enable ADB with --uut_ip)
        self.add_argument('-adb_ip', '--adb_server_ip', help='The IP address of adb server', metavar='IP', default=None)
        self.add_argument('-adb_port', '--adb_server_port', help='The port of adb server', type=int, metavar='PORT', default=None)
        self.add_argument('-arwrd', '--adb_retry_with_reboot_device', help='Reboot device at final retry ADB command', action='store_true', default=False)
        # Power Switch Settings (Enable Power Switch if --power_switch_ip is supplied)
        self.add_argument('-power_ip', '--power_switch_ip', help='Power Switch IP Address', metavar='IP', default=None)
        self.add_argument('-power_port', '--power_switch_port', help='Device power slot on power switch', type=int, metavar='PORT', default=None)
        # Environment Settings
        self.add_argument('-env', '--cloud_env', help='Cloud test environment', default='dev1', choices=['dev', 'dev1', 'dev2', 'qa1', 'qa2', 'prod'])
        self.add_argument('-var', '--cloud_variant', help='Cloud test variant', default='userdebug', choices=['userdebug', 'user', 'engr'])
        # User Settings (UUT Onwer)
        self.add_argument('-p', '--password', help='The password of user attached with UUT', metavar='PWD', default='Wdctest1234')
        self.add_argument('-u', '--username', help='The username of user attached with UUT', metavar='EMAIL', default='wdcautotw+qawdc@gmail.com')
        # Serial Settings
        self.add_argument('-ss_ip', '--serial_server_ip', help='Destination serial server IP address', metavar='IP', default=None)
        self.add_argument('-ss_port', '--serial_server_port', help='Destination UUT serial port', metavar='PORT', default=None)
        self.add_argument('-ss_debug', '--serial_server_debug', help='Enable debug mode of serial client', action='store_true', default=False)
        self.add_argument('-dss_daemon_msg', '--disable_serial_server_daemon_msg', help='Disable debug message of serial daemon', action='store_true', default=False)
        # BTLE Settings
        self.add_argument('-btle_addr', '--btle_addr', help='The Address of destination device', metavar='ADDR', default=None)
        # WiFi Settings
        self.add_argument('-ap_ssid', '--ap_ssid', help='The SSID of destination AP', metavar='SSID', default=None)
        self.add_argument('-ap_password', '--ap_password', help='The password of destination AP', metavar='PWD', default=None)
        self.add_argument('-ap_mode', '--ap_security_mode', help='The security mode of destination AP', metavar='MODE', default='WPA-PSK')
        # AP Settings
        self.add_argument('-ap_ip', '--ap_ip', help='The IP address of destination DD-WRT AP', metavar='IP', default=None)
        self.add_argument('-ap_user', '--ap_user', help='The user name of destination DD-WRT AP', metavar='USER', default=None)
        self.add_argument('-ap_user_pwd', '--ap_user_pwd', help="The user's password of destination DD-WRT AP", metavar='PWD', default=None)
        self.add_argument('-ap_root_pwd', '--ap_root_pwd', help="The root's password of destination DD-WRT AP", metavar='PWD', default=None)
        self.add_argument('-ap_port', '--ap_port', help='The SSH port of destination DD-WRT AP', type=int, metavar='PORT', default=22)
        # Bulitin Feature Settings
        self.add_argument('-fw', '--firmware_version', help='Make sure the specified firmware version on UUT', metavar='FW', default=None)
        self.add_argument('-dfw', '--disable_firmware_consistency', help='Test can run with different firmware version for each iteration', action='store_true', default=False)
        self.add_argument('-dcll', '--disable_clean_logcat_log', help='Not clean logcat log after export logs (for Kamino)', action='store_true', default=False)
        self.add_argument('-dell', '--disable_export_logcat_log', help='Not export logcat log after test is done (for Kamino)', action='store_true', default=False)
        self.add_argument('-deill', '--disable_export_itr_logcat_log', help='Not export logcat log after one single iteration is done (for Kamino)', action='store_true', default=False)
        self.add_argument('-dults', '--disable_upload_logs_to_sumologic', help='Not upload logs to sumologic after test is done', action='store_true', default=False)
        self.add_argument('-dglm', '--disable_get_log_metrics', help='Not print out device metrics logs after test is done', action='store_true', default=False)
        self.add_argument('-eao', '--enable_auto_ota', help='Enable auto OTA process', action='store_true', default=False)
        self.add_argument('-model', '--model', help='Model name in test result, use it when ADB is disable', metavar='MODEL', default=None)
        self.add_argument('-RestAPI_debug', '--RestAPI_debug', help='Print debug messages of RestAPI', action='store_true', default=False)
        self.add_argument('-rms', '--run_models', nargs='*', help='Available model list to run this test case. e.g., -rms pelican yodaplus', metavar='MODEL', default=None)

class GrackInputArgumentParser(CoreInputArgumentParser):
    """ Wrap ArgumentParser with setting bulitin common arguments for Grack Test Case. """

    def init_bulitin_args(self):
        super(GrackInputArgumentParser, self).init_bulitin_args()
        # UUT Settings
        self.add_argument('-ip', '--uut_ip', help='Destination UUT IP address', metavar='IP')
        self.add_argument('-port', '--uut_port', help='Destination UUT port', type=int, metavar='PORT', default=8001)
        # User Settings (UUT Onwer)
        self.add_argument('-p', '--password', help='The password of user attached with UUT', metavar='PWD', default='gtech')
        self.add_argument('-u', '--username', help='The username of user attached with UUT', metavar='USER', default='admin')
        # Bulitin Feature Settings
        self.add_argument('-model', '--model', help='Model name in test result.', metavar='MODEL', default=None)
        self.add_argument('-fw', '--firmware_version', help='Make sure the specified firmware version on UUT', metavar='FW', default=None)

class GodzillaInputArgumentParser(CoreInputArgumentParser):
    """ Wrap ArgumentParser with setting bulitin common arguments for Godzilla Test Case. """

    def init_bulitin_args(self):
        super(GodzillaInputArgumentParser, self).init_bulitin_args()
        # UUT Settings
        self.add_argument('-ip', '--uut_ip', help='Destination UUT IP address', metavar='IP')
        self.add_argument('-restsdk_port', '--uut_restsdk_port', help='Destination UUT port', type=int, metavar='PORT', default=8001)
        # Power Switch Settings (Enable Power Switch if --power_switch_ip is supplied)
        self.add_argument('-power_ip', '--power_switch_ip', help='Power Switch IP Address', metavar='IP', default=None)
        self.add_argument('-power_port', '--power_switch_port', help='Device power slot on power switch', type=int, metavar='PORT', default=None)
        # Environment Settings
        self.add_argument('-env', '--cloud_env', help='Cloud test environment', default='qa1', choices=['dev1', 'qa1', 'prod'])
        self.add_argument('-var', '--cloud_variant', help='Cloud test variant', default='user', choices=['userdebug', 'user'])
        # User Settings (UUT Onwer)
        self.add_argument('-p', '--password', help='The password of user attached with UUT', metavar='PWD', default='Password1234#')
        self.add_argument('-u', '--username', help='The username of user attached with UUT', metavar='USER', default='wdcautotw+qawdc.gza@gmail.com')
        # Serial Settings
        self.add_argument('-ss_ip', '--serial_server_ip', help='Destination serial server IP address', metavar='IP', default=None)
        self.add_argument('-ss_port', '--serial_server_port', help='Destination UUT serial port', metavar='PORT', default=None)
        self.add_argument('-ss_debug', '--serial_server_debug', help='Enable debug mode of serial client', action='store_true', default=False)
        self.add_argument('-dss_daemon_msg', '--disable_serial_server_daemon_msg', help='Disable debug message of serial daemon', action='store_true', default=False)
        # SSH Settings
        self.add_argument('-ssh_user', '--ssh_user', help='The username of SSH server', default="sshd")
        self.add_argument('-ssh_password', '--ssh_password', help='The password of SSH server', metavar='PWD', default="Test1234")
        self.add_argument('-ssh_port', '--ssh_port', help='The port of SSH server', type=int, metavar='PORT', default=22)
        # Bulitin Feature Settings
        self.add_argument('-fw', '--firmware_version', help='Make sure the specified firmware version on UUT', metavar='FW', default=None)
        self.add_argument('-dfw', '--disable_firmware_consistency', help='Test can run with different firmware version for each iteration', action='store_true', default=False)
        self.add_argument('-eao', '--enable_auto_ota', help='Enable auto OTA process', action='store_true', default=False)
        self.add_argument('-model', '--model', help='Model name in test result, use it when SSH is disable', metavar='MODEL', default=None)
        self.add_argument('-RestAPI_debug', '--RestAPI_debug', help='Print debug messages of RestAPI', action='store_true', default=False)
        self.add_argument('-dcdl', '--disable_clean_device_logs', help='Not clean device log after export logs (for GZA)', action='store_true', default=False)
        self.add_argument('-dedl', '--disable_export_device_log', help='Not export device log after test is done (for GZA)', action='store_true', default=False)

class KDPInputArgumentParser(GodzillaInputArgumentParser):
    """ Wrap ArgumentParser with setting bulitin common arguments for KDP Test Case. """

    def init_bulitin_args(self):
        super(KDPInputArgumentParser, self).init_bulitin_args()
        self.set_defaults(ssh_user="root", ssh_password="", uut_restsdk_port=None, username="wdcautotw+qawdc.kdp@gmail.com")
        # WiFi Settings
        self.add_argument('-ap_ssid', '--ap_ssid', help='The SSID of destination AP', metavar='SSID', default=None)
        self.add_argument('-ap_password', '--ap_password', help='The password of destination AP', metavar='PWD', default=None)
        self.add_argument('-ap_mode', '--ap_security_mode', help='The security mode of destination AP', metavar='MODE', default='WPA-PSK')
        # nasAdmin Settings
        self.add_argument('-on', '--owner_name', help='Local user name for owner user', metavar='NAME', default='owner')
        self.add_argument('-op', '--owner_pw', help='Local password for owner user', metavar='PW', default='password')
        # serial console
        self.add_argument('-cp', '--console_password', help='Password for serial console', metavar='PW', default=None)

class IntegrationTestArgumentExtensions(object):
    """ Method extensions for integration test argument. """

    def init_integration_bulitin_args(self):
        self.add_argument('-sof', '--stop_on_failure', help='Stop test if any sub-test failed', action='store_true', default=False)
        self.add_argument('-dsd', '--disable_subtest_dryrun', help='All of sub-testcase will upload its result to ELK', action='store_true', default=False)
        # MTBF feature
        self.add_argument('-c', '--choice', help='Random choice test case to run. Acceptable values: "all": total number equal to test list; "(2,5)": total number is random from 2 to 5;  "10": total number is 10', default=None)
        self.add_argument('-uc', '--unique_choice', help='Random choice test case to run, but not choice duplicate.  Acceptable values refer to --choice', default=None)
        self.add_argument('-ec', '--exec_ordering', help='Specify execute odering of sub-tests with a touple index list (index start from 0), example: "(2,4,1,1,3)"', default=None)

        self.add_argument('--exec_group', help='Specify execute odering of sub-tests with a touple index list (index start from 0), example: "[(2,4), (1,3)]"', default=None)

class CoreIntegrationTestArgument(IntegrationTestArgumentExtensions, CoreInputArgumentParser):
    pass

class IntegrationTestArgument(IntegrationTestArgumentExtensions, InputArgumentParser):
    pass

class GrackIntegrationTestArgument(IntegrationTestArgumentExtensions, GrackInputArgumentParser):
    pass

class GodzillaIntegrationTestArgument(IntegrationTestArgumentExtensions, GodzillaInputArgumentParser):
    pass

class KDPIntegrationTestArgument(IntegrationTestArgumentExtensions, KDPInputArgumentParser):
    pass

class KeywordArguments(dict):
    """ Argument tool for Environment of Tast Case. """
    #TODO: Getter tool for variables.

    def __init__(self, *args, **kwargs):
        super(KeywordArguments, self).__init__(*args, **kwargs)
        self.access_list = [] # Record keyword name which has been used. 

    def get(self, name, default=None):
        """ Record the given name to access_list and return value.

        The access_list is designed for recognizing the arguments is bulitin args or custom args,
        this feature is the key to auto setup arguments to Test Case object.
        """
        value = super(KeywordArguments, self).get(name, default)
        if name not in self.access_list: self.access_list.append(name)
        value = self.args_additional_handle(name, value)
        return value

    def args_additional_handle(self, name, value):
        if 'stream_log_level' == name:
            if isinstance(value, int):
                return value
            # Covert string to level value.
            return getattr(logging, value, logging.INFO)

        if name in ['choice', 'unique_choice']:
            if not value:
                return None
            elif value == 'all':
                return value
            elif value.isdigit(): # Except: 5
                return int(value)
            else: # Except: (2,4)
                try:
                    value = ast.literal_eval(value)
                except:
                    value = None
                if not isinstance(value, tuple) or [i for i in value if not isinstance(i, int)] or len(value) != 2:
                    raise ValueError('{} is not correct'.format(name))

        if name in ['exec_ordering']:# Except: (2,4)
            if not value:
                return None
            try:
                value = ast.literal_eval(value)
            except:
                value = None
            if not isinstance(value, tuple) or [i for i in value if not isinstance(i, int)]:
                raise ValueError('{} is not correct'.format(name))

        return value

    def gen_unused_dict(self):
        """ Return a dict object contain all unused data. """
        return {k:v for k, v in self.iteritems() if k not in self.access_list}
