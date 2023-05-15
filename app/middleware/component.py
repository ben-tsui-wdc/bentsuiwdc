# -*- coding: utf-8 -*-
""" Components for Test Case. 
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import logging
import json
import os
import time  
from pprint import pformat
# platform modules
from error import get_junit_msg_key_from
from platform_libraries.adblib import ADB
from platform_libraries.btle_client import YodaClient
from platform_libraries.common_utils import create_logger
from platform_libraries.ddwrt_client import DDWRTClient
from platform_libraries.nasadmin_client import NasAdminClient
from platform_libraries.popcorn import gen_popcorn_test, gen_popcorn_report, upload_popcorn_report_to_server
from platform_libraries.pyutils import retry
from platform_libraries.powerswitchclient import PowerSwitchClient
from platform_libraries.restAPI import RestAPI
from platform_libraries.serial_client import SerialClient
from platform_libraries.test_result import ELKTestResult, ELKLoopingResult, object_to_json_file
from platform_libraries.ssh_client import SSHClient
from platform_libraries.godzilla import Godzilla


#
# Object Component Area
#
class TestCaseComponent(object):
    """ Superclass of Test Case Component. """

    def __init__(self, testcase_inst):
        self.testcase = testcase_inst
        self.env = testcase_inst.env
        self.init()

    def init(self, *args, **kwargs):
        """ Initiate attributes of Component. """
        pass

    def dump_to_dict(self):
        """ Dump attributes to a dict object which can pass into input_parse(). """
        return var(self)


class UtilityManagement(TestCaseComponent):

    def init(self):
        # Custom list for closing utils when end of test. 
        self.utils_to_close = []
        self.utils_to_update_ip = []

    def register_util_to_close(self, util_inst, close_method):
        self.utils_to_close.append((util_inst, close_method))

    def close_utils(self):
        for util, method in self.utils_to_close:
            try:
                if method:
                    self.env.log.info('Close utility {} with {}()...'.format(util, method))
                    getattr(util, method)()
            except Exception, e:
                self.env.log.warning('Error found during close utility {}: {}'.format(util, e), exc_info=True)

    def register_util_to_update_ip(self, util_inst, update_method):
        self.utils_to_update_ip.append((util_inst, update_method))

    def update_ip_to_utils(self, ip):
        for util, method in self.utils_to_update_ip:
            try:
                if method:
                    self.env.log.info('Update IP {} to utility {} with {}()...'.format(ip, util, method))
                    getattr(util, method)(ip)
            except Exception, e:
                self.env.log.warning('Error found during update utility {}: {}'.format(util, e), exc_info=True)

    #
    # Generator Methods
    #
    def gen_adb(self, kwargs, close_at_end=False):
        adb_inst = kwargs.get('_utilities', {}).get('adb')
        if isinstance(adb_inst, ADB):
            return adb_inst
        # Create instance
        ret_inst = ADB(uut_ip=kwargs.get('uut_ip'), port=kwargs.get('uut_port'),
            adbServer=kwargs.get('adb_server_ip'), adbServerPort=kwargs.get('adb_server_port'),
            stream_log_level=kwargs.get('stream_log_level'), retry_with_reboot_device=kwargs.get('adb_retry_with_reboot_device'))
        # Register closing method.
        if close_at_end:
            self.register_util_to_close(util_inst=ret_inst, close_method='disconnect')
        # Register updating IP method.
        self.register_util_to_update_ip(util_inst=ret_inst, update_method='update_device_ip')
        return ret_inst

    def gen_ap(self, kwargs, close_at_end=False):
        ap_inst = kwargs.get('_utilities', {}).get('ap')
        if isinstance(ap_inst, DDWRTClient):
            return ap_inst
        elif not (kwargs.get('ap_ip') and kwargs.get('ap_user') and kwargs.get('ap_user_pwd')):
            return None
        # Create instance
        ret_inst = DDWRTClient(hostname=kwargs.get('ap_ip'), username=kwargs.get('ap_user'),
            password=kwargs.get('ap_user_pwd'), port=kwargs.get('ap_port'), root_password=kwargs.get('ap_root_pwd'),
            stream_log_level=kwargs.get('stream_log_level'))
        # Register closing method.
        if close_at_end:
            self.register_util_to_close(util_inst=ret_inst, close_method='close')
        return ret_inst

    def gen_btle_client(self, kwargs, close_at_end=False):
        btle_client_inst = kwargs.get('_utilities', {}).get('btle_client')
        btle_addr = kwargs.get('btle_addr')
        if isinstance(btle_client_inst, YodaClient):
            return btle_client_inst
        elif btle_addr:
            # Create instance
            ret_inst = YodaClient(btle_addr, debug=True, stream_log_level=kwargs.get('stream_log_level'))
            if close_at_end:
                self.register_util_to_close(util_inst=ret_inst, close_method='disconnect')
            return ret_inst
        return None

    def gen_power_switch(self, kwargs, close_at_end=False):
        power_switch_inst = kwargs.get('_utilities', {}).get('power_switch')
        power_switch_ip = kwargs.get('power_switch_ip')
        if isinstance(power_switch_inst, PowerSwitchClient):
            return power_switch_inst
        elif power_switch_ip:
            # Create instance
            return PowerSwitchClient(power_switch_ip, stream_log_level=kwargs.get('stream_log_level'))
        return None

    def gen_serial_client(self, kwargs, close_at_end=False):
        serial_client = kwargs.get('_utilities', {}).get('serial_client')
        server_ip = kwargs.get('serial_server_ip')
        uut_port = kwargs.get('serial_server_port')
        if isinstance(serial_client, SerialClient):
            return serial_client
        elif server_ip and uut_port:
            # Create instance
            ret_inst = SerialClient(
                server_ip, uut_port, debug=kwargs.get('serial_server_debug'),
                daemon_msg=not kwargs.get('disable_serial_server_daemon_msg'),
                stream_log_level=kwargs.get('stream_log_level'), password=kwargs.get('console_password')
            )
            # Register closing method.
            if close_at_end:
                self.register_util_to_close(util_inst=ret_inst, close_method='close_serial_connection')
            return ret_inst
        return None

    def gen_ssh_client(self, kwargs, close_at_end=False):
        # Create the instance of SSH client object
        ssh_client = kwargs.get('_utilities', {}).get('ssh_client')
        server_ip = kwargs.get('uut_ip')
        username = kwargs.get('ssh_user')
        password = kwargs.get('ssh_password')
        port = kwargs.get('ssh_port')
        if isinstance(ssh_client, SSHClient):
            return ssh_client
        elif server_ip and username and (password is not None) and port:
            # Create instance
            ret_inst = SSHClient(server_ip, username, password, port)
            # Register closing method.
            if close_at_end:
                self.register_util_to_close(util_inst=ret_inst, close_method='close')
            # Register updating IP method.
            self.register_util_to_update_ip(util_inst=ret_inst, update_method='update_device_ip')
            return ret_inst
        return None

    def gen_log(self, log_name=None, close_at_end=False, stream_log_level=None):
        return create_logger(log_name=log_name, stream_log_level=stream_log_level)

    def gen_uut_owner(self, kwargs, close_at_end=False):
        uut_owner_inst = kwargs.get('_utilities', {}).get('uut_owner')
        if isinstance(uut_owner_inst, RestAPI):
            return uut_owner_inst
        # Create instance
        ret_inst = RestAPI(
            uut_ip=kwargs.get('uut_ip'), port=kwargs.get('uut_restsdk_port'), env=kwargs.get('cloud_env'), username=kwargs.get('username'),
            password=kwargs.get('password'), debug=kwargs.get('RestAPI_debug', False), init_session=False,
            stream_log_level=kwargs.get('stream_log_level'), client_id=kwargs.get('client_id')
        )
        # Register updating IP method.
        self.register_util_to_update_ip(util_inst=ret_inst, update_method='update_device_ip')
        return ret_inst

    def gen_nasadmin_client(self, kwargs, rest_client=None, close_at_end=False):
        nasadmin_inst = kwargs.get('_utilities', {}).get('nasadmin')
        if isinstance(nasadmin_inst, NasAdminClient):
            return nasadmin_inst
        # Create instance
        uut_ip = kwargs.get('uut_ip')
        nasadmin_inst = NasAdminClient(
            ip=uut_ip, rest_client=rest_client,
            local_name=kwargs.get('owner_name'), local_password=kwargs.get('owner_pw'),
            stream_log_level=kwargs.get('stream_log_level')
        )
        # Register updating IP method.
        self.register_util_to_update_ip(util_inst=nasadmin_inst, update_method='update_device_ip')
        return nasadmin_inst


class ExtensionComponent(TestCaseComponent):
    """ You can put any useful small tool here. """

    def check_firmware_consistency(self):
        """ For auto OTA or Switch back to old partition behavior. """
        if not getattr(self.testcase.adb, 'connected', False):
            return
        self.env.log.info('Check Firmware Consistency.')
        last = self.env.UUT_firmware_version
        current = self.testcase.adb.getFirmwareVersion()
        if last != current:
            raise RuntimeError('Firmware version is changed.')
        self.env.UUT_firmware_version = current # Move me if need.


class UUTInformationComponent(TestCaseComponent, dict):

    def __init__(self, testcase_inst):
        dict.__init__(self)
        TestCaseComponent.__init__(self, testcase_inst)
        # All the Fields.
        self.update(**{
            'firmware': None,
            'variant': None,
            'model': None,
            'serial_number': None,
            'uboot': None,
            'environment': None,
            'mac_address': None,
            'config_url': None,
            'checkout_UUT': None # From UUT file
        })

    def show_device(self):
        self.env.log.info('* Model        : {}'.format(self.get('model', '')))
        self.env.log.info('* Firmware     : {}'.format(self.get('firmware', '')))
        self.env.log.info('* U-boot       : {}'.format(self.get('uboot', '')))
        self.env.log.info('* Variant      : {}'.format(self.get('variant', '')))
        self.env.log.info('* Environment  : {}'.format(self.get('environment', '')))
        self.env.log.info('* Serial Number: {}'.format(self.get('serial_number', '')))
        self.env.log.info('* MAC Address  : {}'.format(self.get('mac_address', '')))
        self.env.log.info('* Config URL   : {}'.format(self.get('config_url', '')))

    def get_UUT_info_with_ADB(self):
        # Check ADB connection.
        if not getattr(self.testcase.adb, 'connected', False):
            return self
        self.env.log.info('Getting device information with ADB...')
        data = {}
        # Workaround for ADB return empty string issue (Encountered at Build#144)...
        data['firmware'] = retry(
            func=self.testcase.adb.getFirmwareVersion,
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        data['variant'] = retry(
            func=self.testcase.adb.get_variant,
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        data['model'] = retry(
            func=self.testcase.adb.getModel,
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        data['serial_number'] = retry(
            func=self.testcase.adb.getSerialNumber,
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        data['uboot'] = retry(
            func=self.testcase.adb.get_uboot,
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        data['environment'] = retry(
            func=self.testcase.adb.get_environment,
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        data['mac_address'] = retry(
            func=self.testcase.adb.get_mac_address, interface= 'wlan0' if 'yoda' in data['model'] else 'eth0',
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        data['config_url'] = retry(
            func=self.testcase.adb.get_config_url,
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        return data

    def get_UUT_info_with_SSH(self):
        self.env.log.info('Getting device information with SSH...')
        data = {}
        data['firmware'] = retry(
            func=self.testcase.ssh_client.get_firmware_version,
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        data['model'] = retry(
            func=self.testcase.ssh_client.get_model_name,
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        data['environment'] = retry(
            func=self.testcase.ssh_client.get_device_environment,
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        data['config_url'] = retry(
            func=self.testcase.ssh_client.get_restsdk_configurl,
            retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
        )
        if data['model'] in ['monarch2', 'pelican2', 'yodaplus2']:   # For KDP
            data['serial_number'] = retry(
                func=self.testcase.ssh_client.get_device_serial_number,
                retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
            )
            data['mac_address'] = retry(
                func=self.testcase.ssh_client.get_mac_address, interface= 'wlan0' if data['model'] in ['yodaplus2', 'rocket', 'drax'] else 'eth0',
                retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
            )
        else:   # For GZA
            data['mac_address'] = retry(
                func=self.testcase.ssh_client.get_mac_address, interface= 'egiga0',
                retry_lambda=lambda ret: not ret, delay=10, max_retry=3, log=self.env.log.warning, not_raise_error=True
            )

        return data

    def update_UUT_info(self):
        """ Update all the info. """
        self.env.log.info('Updating UUT information...')
        if getattr(self.testcase, 'adb', False) and getattr(self.testcase.adb, 'connected', False):
            self.update_with_ADB()
            #self.update_from_UUT_file() # UUT file should be load first in init flow.
        elif getattr(self.testcase, 'ssh_client', False):
            self.update_with_SSH()

    def update_with_SSH(self):
        uut_info = self.get_UUT_info_with_SSH()
        if not isinstance(uut_info, UUTInformationComponent):
            self.update(**uut_info)

    def update_with_ADB(self):
        uut_info = self.get_UUT_info_with_ADB()
        if not isinstance(uut_info, UUTInformationComponent):
            self.update(**uut_info)

    def update_from_UUT_file(self, path='/root/app/output/UUT'):
        checkout_uut_info = self.get_info_from_UUT_file(path)
        if checkout_uut_info:
            self['checkout_UUT'] = checkout_uut_info

    def get_info_from_UUT_file(self, path='/root/app/output/UUT'):
        # TODO: Should we change field name?
        if not os.path.exists(path):
            self.env.log.info('UUT file not found.')
            return None
        # Read UUT file and convert to dict.
        self.env.log.info('Load device information from UUT file...')
        with open(path, 'r') as f:
            info_json_string = f.readline()
        try:
            UUT_dict = json.loads(info_json_string)
            self.env.log.info('Device information from {}: \n{}'.format(path, pformat(UUT_dict)))
            return UUT_dict
        except:
            self.env.log.info('Parse device information failed.')
            return None

    # TODO: Move me if here is not a good place.
    def adb_log(self, message, priority='V', tag='AutomationTest', buffer=None, force=False):
        """ Write logcat message via ADB. """
        if force:
            self.env.log.force_log(logging.INFO, self.env.stream_log_level, message)
        else:
            self.env.log.info(message)
        # Check ADB connection.
        if not getattr(self.testcase, 'adb', None) or not getattr(self.testcase.adb, 'connected', False):
            return
        try:
            self.testcase.adb.write_logcat(message, priority='V', tag='AutomationTest', buffer=None)
        except Exception, e:
            self.env.log.exception(e)

class ResultComponent(TestCaseComponent):
    """ You can put test result relative tool here. """

    def init(self):
        self.init_worksapce()
        self.test_result = None # ELKTestResult object to record the test result on the current iteration.
        self.loop_results = None # ResultList object to append each test iteration result.
        self.file_prefix = '' # Prefix part of output file name.
        self.upload_logstash = True

    def init_worksapce(self):
        """ Create working folders if they don't exist. """
        self.worksapce = os.getcwd()
        self.env.log.debug('Automation Workspace: {}'.format(self.worksapce))
        output_path = '{}/{}'.format(self.worksapce, self.env.output_folder)
        self.env.log.debug('Automation output folder: {}'.format(output_path))
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        results_path = '{}/{}'.format(self.worksapce, self.env.results_folder)
        self.env.log.debug('Automation results folder: {}'.format(results_path))
        if not os.path.exists(results_path):
            os.makedirs(results_path)

    def get_abs_path(self, relative_path):
        if not self.worksapce:
            return relative_path
        return '{}/{}'.format(self.worksapce, relative_path)

    def reset_test_result(self):
        self.env.log.info('Reset Test Result.')
        # For UUT may not support.
        uut = getattr(self.testcase, 'uut')
        if not uut:
            uut = {}
        # Generate test result.
        self.test_result = ELKTestResult(
            test_suite=self.testcase.TEST_SUITE, test_name=self.testcase.TEST_NAME,
            build=uut.get('firmware', ''), iteration=self.env.iteration,
            product=uut.get('model', ''), test_jira_id=self.testcase.TEST_JIRA_ID
        )

    def reset_loop_results(self):
        self.env.log.info('Reset Test Loop Results.')
        # For UUT may not support.
        uut = getattr(self.testcase, 'uut')
        if not uut:
            uut = {}
        self.loop_results = ELKLoopingResult(
            test_suite=self.testcase.TEST_SUITE, test_name=self.testcase.TEST_NAME,
            build=uut.get('firmware', ''),  product=uut.get('model', ''), test_jira_id=self.testcase.TEST_JIRA_ID
        )

    def append_loop_result(self):
        self.env.log.info('Append Test #{} To Loop Results.'.format(self.env.iteration))
        self.loop_results.append(self.test_result)

    def upload_test_result(self):
        if not self.upload_logstash: return True
        try:
            self.env.log.info('Update Result To Logstash: {}'.format(self.env.logstash_server_url))
            self.test_result.upload_to_logstash(server_url=self.env.logstash_server_url)
        except:
            self.env.log.exception('Upload Test Result Failed.')
            return False
        return True

    def upload_loop_result(self):
        if not self.upload_logstash: return True
        try:
            self.env.log.info('Update Loop Result To Logstash: {}'.format(self.env.logstash_server_url))
            self.loop_results.upload_to_logstash(server_url=self.env.logstash_server_url)
        except:
            self.env.log.exception('Upload Loop Result Failed.')
            return False
        return True

    def export_test_result(self):
        if self.env.iteration: # run in loop
            if getattr(self.testcase, 'test_result_prefix', False) and self.testcase.test_result_prefix:
                export_path = '{}/{}{}.json'.format(self.env.results_folder, self.testcase.test_result_prefix, self.env.iteration)
            else:
                export_path = '{0}/{1}{2}#{3}.json'.format(self.env.results_folder, self.file_prefix, self.testcase.TEST_NAME, self.env.iteration)

        else:
            export_path = '{0}/{1}{2}.json'.format(self.env.results_folder, self.file_prefix, self.testcase.TEST_NAME)
        export_path = self.get_abs_path(export_path)
        self.test_result.to_file(export_path)
        self.env.log.info('Save Result To {}'.format(export_path))

    def export_loop_results(self):
        if getattr(self.testcase, 'loop_result_name', False) and self.testcase.loop_result_name:
            export_path = '{}/{}test_report.xml'.format(self.env.results_folder, self.testcase.loop_result_name)
        else:
            export_path = '{}/test_report.xml'.format(self.env.results_folder)
        export_path = self.get_abs_path(export_path)
        self.loop_results.to_file(export_path, output_format='junit-xml')
        self.env.log.info('Save Loop Results To {}'.format(export_path))

    def gen_popcorn(self):
        self.test_result.POPCORN_RESULT = gen_popcorn_test(self.testcase)

    def export_test_result_as_popcorn(self):
        if self.env.iteration: # run in loop
            return # only export one report for entire test.
        self.export_popcorn_report([self.test_result])

    def upload_test_result_to_popcorn(self):
        if self.env.iteration or self.env.is_subtask: # run in loop or it's a sub-task test
            return # only export one report for entire test.
        self.upload_results_to_popcorn([self.test_result])

    def export_loop_results_as_popcorn(self):
        self.export_popcorn_report(self.loop_results)

    def upload_loop_results_to_popcorn(self):
        self.upload_results_to_popcorn(self.loop_results)

    def export_popcorn_report(self, test_results):
        pr = gen_popcorn_report(self.testcase, test_results, self.env.popcorn_skip_error)
        export_path = '{0}/{1}{2}.popcorn.json'.format(self.env.results_folder, self.file_prefix, self.testcase.TEST_NAME)
        export_path = self.get_abs_path(export_path)
        object_to_json_file(pr, export_path)
        self.env.log.info('Save Popcorn Result To {}'.format(export_path))

    def upload_results_to_popcorn(self, test_results):
        pr = gen_popcorn_report(self.testcase, test_results, self.env.popcorn_skip_error)
        upload_popcorn_report_to_server(data=pr, source=self.testcase.POPCORN_SOURCE)
        self.env.log.info('Results have been uploaded to popcorn server.')

    def error_callback(self, exception):
        """ Callback function for handling test failed by exception. """
        self.env.debug_middleware and self.env.log.warning('Handle exception by error_callback()')
        if self.test_result is None:
            return
        # Add JUnit message.
        test_status = self.testcase.err.status_mapping(exception)
        msg_filed = self.testcase.err.field_mapping(test_status)
        if msg_filed:
            try:
                self.test_result[msg_filed] = ''.join(self.testcase.log.test_steps.get_last_one()['messages'])
            except:
                self.test_result[msg_filed] = str(exception)
        # Update test result.
        if 'skipped_message' in self.test_result:
            self.test_result.TEST_PASS = None
        else:
            self.test_result.TEST_PASS = False

    def loop_error_callback(self, exception):
        """ Callback function for handling loop test failed by exception. """
        self.env.debug_middleware and self.env.log.warning('Handle exception by loop_error_handler()')
        if self.loop_results is None:
            return
        # Update test result.
        if 'skipped_message' in self.test_result:
            self.loop_results.TEST_PASS = None
        else:
            self.loop_results.TEST_PASS = False

    def print_test_result(self):
        if not self.env.debug_middleware:
            return
        self.env.log.info('#'*75)
        self.env.log.info('Test Result: \n{}'.format(pformat(self.test_result)))
        self.env.log.info('#'*75)

    def export_logcat_log(self, clean_logcat=True, name_postfix=None):
        try:
            export_path = self.get_abs_path('{0}/{1}{2}'.format(self.env.output_folder, self.file_prefix, self.env.logcat_name))
            if name_postfix: export_path = '{0}{1}'.format(export_path, name_postfix)
            self.testcase.adb.logcat_to_file(export_path)
            if clean_logcat: # Clean logcat after export.
                self.testcase.adb.clean_logcat()
        except:
            self.env.log.warning('Save logcat log failed.', exc_info=True)

    def export_gza_logs(self, clean_device_logs=True, name_postfix=None):
        try:
            export_path = self.get_abs_path('{0}/{1}{2}'.format(
                self.env.output_folder, self.file_prefix,
                'logs{}.tgz'.format(name_postfix) if name_postfix else 'logs.tgz'))
            self.testcase.ssh_client.save_gza_device_logs(export_path)
            if clean_device_logs: # Clean logcat after export.
                self.testcase.ssh_client.clean_device_logs()
        except:
            self.env.log.warning('Save device log failed.', exc_info=True)

    def export_kdp_logs(self, clean_device_logs=True, name_postfix=None, device_tmp_log=None):
        try:
            export_path = self.get_abs_path('{0}/{1}{2}'.format(
                self.env.output_folder, self.file_prefix,
                'logs{}.tgz'.format(name_postfix) if name_postfix else 'logs.tgz'))
            if device_tmp_log:
                self.testcase.ssh_client.save_kdp_device_logs(export_path, device_tmp_log=device_tmp_log)
            else:
                self.testcase.ssh_client.save_kdp_device_logs(export_path)
            if clean_device_logs: # Clean logcat after export.
                self.testcase.ssh_client.clean_device_logs()
        except:
            self.env.log.warning('Save device log failed.', exc_info=True)

    def upload_logs_to_sumologic(self):
        #return # Not upload logs because it may no use and it possbile block other upload prcoess.
        try:
            self.testcase.adb.upload_logs_to_sumologic()
        except:
            self.env.log.warning('Upload logs to sumologic failed.', exc_info=True)
            try:
                self.env.log.info('Check log status...')
                self.testcase.adb.executeShellCommand('logcat -d -s SHELL', consoleOutput=True)
            except:
                self.env.log.warning('Print failed.', exc_info=True)


class TimingComponent(TestCaseComponent):
    """ You can put timing relative tool here. """

    ELAPSED_TIME_FILED = 'elapsed_sec'
    ELAPSED_TIME_ATTR = 'TEST_ELAPSED_SEC'

    def init(self):
        self.start_time = None
        self.end_time = None

    def get_elapsed_time(self):
        if self.start_time is None or self.end_time is None:
            return None
        return self.end_time - self.start_time

    def reset_start_time(self):
        self.start_time = time.time()

    def record_elapsed_time(self, into_dict):
        elapsed_time = self.get_elapsed_time()
        self.env.log.debug('[Single TestCase] Test Elapsed Time: {}s'.format(elapsed_time))
        setattr(into_dict, self.ELAPSED_TIME_ATTR, elapsed_time)
        if self.ELAPSED_TIME_FILED in into_dict: # Add more elasticity to update time.
            self.env.log.debug('Not update Test Elapsed Time to result.')
            return
        into_dict[self.ELAPSED_TIME_FILED] = elapsed_time

    def start(self):
        self.reset_start_time()

    def finish(self):
        self.end_time = time.time()
        self.update_last_test_step()
        if isinstance(self.testcase.data.test_result, dict):
            self.record_elapsed_time(into_dict=self.testcase.data.test_result) # any issue?
        else:
            self.record_elapsed_looping_time(into_list=self.testcase.data.test_result)

    def is_timeout(self, timeout):
        if not self.start_time:
            return False
        return time.time() - self.start_time >= timeout

    def update_last_test_step(self):
        """ For Test Step feature. """
        try:
            last = self.testcase.log.test_steps.get_last_one()
            if last and not last['end_time']:
                last.set_end_time(self.end_time)
        except Exception as e:
            self.log.warning(str(e), exc_info=True)

    def record_elapsed_looping_time(self, into_list):
        elapsed_time = self.get_elapsed_time()
        self.env.log.debug('[Single Iteration] Test Elapsed Time: {}s'.format(elapsed_time))
        setattr(into_list, self.ELAPSED_TIME_ATTR, elapsed_time)

    def start_looping(self):
        self.reset_start_time()

    def finish_looping(self):
        self.end_time = time.time()
        self.update_last_test_step()
        self.record_elapsed_looping_time(into_list=self.testcase.data.loop_results)
