# -*- coding: utf-8 -*-
""" Implementation of Test case for Godzilla product.
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"


# std modules
import datetime
import json
import os
import re
import copy
# middleware modules
from core.test_case import Settings, TestCase as CoreTestCase
from component import ExtensionComponent, UUTInformationComponent


class GodzillaTestCase(CoreTestCase):
    """ Superclass for test case. """

    # For Popcorn
    COMPONENT = 'PLATFORM'

    SETTINGS = Settings(**{ # Default flags for features, accept the changes if SETTINGS data supplied;
                 # For input arguments relative features, the key name is the same as input argument.
                 # Set True to Value means Enable this feature or Set True to this attribute as default value;
                 # Set False to Value means Disable this feature or Set False to this attribute as default value.
        'disable_loop': False,
        'disable_firmware_consistency': True,
        'adb': False,
        'ap': False,
        'btle_client': False,
        'power_switch': True, 
        'serial_client': True,
        'uut_owner' : True,
        'always_do_after_test': True,
        'always_do_after_loop': True,
        'run_models': None,
        'ssh_client': True
    })

    #
    # MiddleWare Hooks Area
    #
    def init_error_handle(self, exception):
        # HOTFIX for duplicate name issue.
        # TODO: Move reder method before init sub-test.
        import time
        self.env.logcat_name = 'init_error.logcat.{}'.format(time.time())
        try:
            self.update_error_to_test_step()
            self.finally_of_exit_test() # Need export logs by serail?
            self._end_of_test()
        except Exception, e:
            if getattr(self, 'env', None) and getattr(self.env, 'log', None): # REMOVE ME?
                self.env.log.warning(e, exc_info=True)
            else: # print to console if it has no log instance.
                import traceback
                traceback.print_exc()

    def finally_of_single_iteration(self):
        if not self.ssh_client:
            self.env.log.warning('Unable to save logs because of SSH is disabled.')
        elif not self.ssh_client.check_ssh_connectable:
            self.env.log.warning('Unable to save logs because of SSH is disconnected.')
        else: # TODO: Clean logs for each iteration if we needs.
            # Save device log.
            if not getattr(self.env, 'disable_export_device_log', False):
                self.data.export_gza_logs(
                    clean_device_logs=not getattr(self.env, 'disable_clean_device_logs', False),
                    name_postfix='#{}'.format(self.env.iteration)
                )
        CoreTestCase.finally_of_single_iteration(self)

    def finally_of_exit_test(self):
        try:
            self.uut.update_UUT_info()
        except Exception, e:
            self.env.log.warning(e, exc_info=True)
        # Always save locat log & upload logs to sumologic.
        if not hasattr(self, 'ssh_client') or not self.ssh_client:
            self.env.log.warning('Unable to save logs because of SSH is disabled.')
        elif not self.ssh_client.check_ssh_connectable:
            self.env.log.warning('Unable to save logs because of SSH is disconnected.')
        else:
            # Save device log.
            if not getattr(self.env, 'disable_export_device_log', False):
                self.data.export_gza_logs(clean_device_logs=not getattr(self.env, 'disable_clean_device_logs', False))
        CoreTestCase.finally_of_exit_test(self)

    def _before_single_test_steps(self):
        pass

    def _before_single_iteration_steps(self):
        # Render correlation id for each iteration.
        if self.uut_owner and self.env.iteration != 1:
            self.uut_owner.render_correlation_id()

    def gen_target_path(self):
        """ Naming rules for remote save path. """
        if os.getenv('JOB_NAME') or os.getenv('BUILD_NUMBER'):
            return self.path_for_jenkins_run()
        return self.path_for_local_run()

    def path_for_jenkins_run(self):
        return '{}/{}/{}/{}/{}'.format(
            self.uut['firmware'] if self.uut['firmware'] else 'Unknown',
            self.env.cloud_env if self.env.cloud_env else 'Unknown',
            self.uut['model'] if self.uut['model'] else 'Unknown',
            os.getenv('JOB_NAME', 'Unknown'),
            os.getenv('BUILD_NUMBER', 'Unknown')
        )

    def path_for_local_run(self):
        return '{}/{}/{}/{}/{}'.format(
            self.uut['firmware'] if self.uut['firmware'] else 'Unknown',
            self.env.cloud_env if self.env.cloud_env else 'Unknown',
            self.uut['model'] if self.uut['model'] else 'Unknown',
            self.TEST_SUITE if self.TEST_SUITE else 'Unknown',
            datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')
        )


    class Environment(CoreTestCase.Environment):
        """ Initiate all attributes which TestCase use here. """
        # GZA need to use the same client ID as admin UI pages
        admin_ui_client_ID = {
            "qa1": "6FUNaafq6HlO7IWpOyZZm1llU4Zum8nK",
            "dev1": "kodRsfskI3kx6ovBKOyaIXEJ5sN85AWT",
            "prod": "B3WJ2Aew7VVx7QjsOOPrK6zYNLIsq5bu"
        }

        def init_flow_variables(self, of_inst, kwargs):
            """ Initiate variables for bulitin testing flow. """
            super(GodzillaTestCase.Environment, self).init_flow_variables(of_inst, kwargs)
            target_inst = of_inst
            # FIXME: if we have solution to know input argument is supplied.
            target_inst.disable_firmware_consistency = \
                self.testcase.SETTINGS.is_available('disable_firmware_consistency') or \
                kwargs.get('disable_firmware_consistency', False) # Control flag to not check firmware consistency.
            target_inst.enable_auto_ota = self.testcase.SETTINGS.is_available('enable_auto_ota') or \
                kwargs.get('enable_auto_ota', False) # Control flag to not stop otaclient.
            target_inst.disable_clean_device_logs = kwargs.get('disable_clean_device_logs', False)
            target_inst.disable_export_device_log = kwargs.get('disable_export_device_log', False)

        def init_variables(self, of_inst, kwargs):
            """ Initiate common variables """
            super(GodzillaTestCase.Environment, self).init_variables(of_inst, kwargs)
            target_inst = of_inst
            # UUT and Test settings
            target_inst.cloud_env = kwargs.get('cloud_env')
            target_inst.cloud_variant = kwargs.get('cloud_variant')
            target_inst.firmware_version = kwargs.get('firmware_version')
            target_inst.model = kwargs.get('model')
            target_inst.uut_ip = kwargs.get('uut_ip')
            target_inst.uut_restsdk_port = kwargs.get('uut_restsdk_port')
            # Power Switch
            target_inst.power_switch_ip = kwargs.get('power_switch_ip')
            target_inst.power_switch_port = kwargs.get('power_switch_port') # Custom port for Test
            # Serial Client
            target_inst.serial_server_ip = kwargs.get('serial_server_ip')
            target_inst.serial_server_port = kwargs.get('serial_server_port')
            target_inst.serial_server_debug = kwargs.get('serial_server_debug')
            target_inst.disable_serial_server_daemon_msg = kwargs.get('disable_serial_server_daemon_msg')
            # WiFi Settings
            target_inst.ap_ssid = kwargs.get('ap_ssid')
            target_inst.ap_password = kwargs.get('ap_password')
            target_inst.ap_security_mode = kwargs.get('ap_security_mode')
            # UUT Owner
            target_inst.username = kwargs.get('username')
            target_inst.password = kwargs.get('password')
            # Folder Paths
            target_inst.logcat_name = kwargs.get('logcat_name') or 'logcat'
            target_inst.run_models = kwargs.get('run_models', None) or self.testcase.SETTINGS.get('run_models')
            # SSH Client
            target_inst.ssh_ip = kwargs.get('uut_ip')
            target_inst.ssh_port = kwargs.get('ssh_port')
            target_inst.ssh_user = kwargs.get('ssh_user')
            target_inst.ssh_password = kwargs.get('ssh_password')
            # GZA need to use the same client ID as admin UI pages
            kwargs['client_id'] = self.admin_ui_client_ID.get(kwargs.get('cloud_env'))

        def init_popcorn_variables(self, of_inst, kwargs):
            """ Initiate Popcorn variables """
            target_inst = of_inst
            if target_inst.env.cloud_env: target_inst.ENVIROMENT = target_inst.env.cloud_env
            if target_inst.env.firmware_version:
                target_inst.FW_BUILD = target_inst.env.firmware_version
                regex = r"(\d+.\d+).(\d+)"
                matches = re.match(regex, target_inst.env.firmware_version)
                if matches:
                    # Full match: 3.00.8, group 1: 3.00, group 2: 8
                    target_inst.VERSION = matches.group(1)
                    target_inst.BUILD = matches.group(2)

            if target_inst.env.model: target_inst.PLATFORM = target_inst.env.model
            super(GodzillaTestCase.Environment, self).init_popcorn_variables(of_inst, kwargs)

        def init_components(self, of_inst, kwargs):
            """ Initiate components """
            super(GodzillaTestCase.Environment, self).init_components(of_inst, kwargs)
            target_inst = of_inst
            target_inst.ext = ExtensionComponent(testcase_inst=self.testcase)
            target_inst.uut = UUTInformationComponent(testcase_inst=self.testcase)
            # disable logstash
            target_inst.data.upload_logstash = False

        def init_utilities(self, of_inst, kwargs):
            """ Initiate common utilities """
            super(GodzillaTestCase.Environment, self).init_utilities(of_inst, kwargs)
            target_inst = of_inst
            # Connect network for ibi2 and RND.
            if target_inst.serial_client:
                if not target_inst.serial_client.serial_is_connected(reset_command_line=True): # Sub-test MAY NOT run this part.
                    target_inst.serial_client.initialize_serial_port() # Connect as default
                    model = target_inst.serial_client.get_model()
                    # Setup and connect WiFi
                    if self.is_wifi_support(model) and target_inst.env.ap_ssid:
                        self.log.info('Since ap_ssid is specified, connect to WiFi...')
                        if model == 'rocket' or model == 'drax':
                            self.log.info('Model is {}, only check wlan interface ...'.format(model))
                            target_inst.serial_client.retry_for_connect_WiFi_kdp(ssid=target_inst.env.ap_ssid, password=target_inst.env.ap_password, try_time=3, interface='wlan')
                        else:
                            target_inst.serial_client.retry_for_connect_WiFi_kdp(ssid=target_inst.env.ap_ssid, password=target_inst.env.ap_password, try_time=3)
                # Always check IP is correct or not if serial client is support.
                self.check_ip_change_by_console()
                # Make sure read queue is clean for each test.
                target_inst.serial_client.init_read_queue()
            # Register serial client into ssh client for restart ssh service.
            if target_inst.ssh_client and target_inst.serial_client:
                target_inst.ssh_client.set_serial_client(target_inst.serial_client)
            # Connect SSH after network is connected.
            if target_inst.ssh_client:
                target_inst.ssh_client.connect() # Connect as default
            if target_inst.ssh_client and target_inst.uut_owner:
                target_inst.uut_owner.set_ssh_client(target_inst.ssh_client)

        def is_wifi_support(self, model):
            if 'yoda' in model or 'rocket' in model or 'drax' in model:
                return True
            return False

        def check_ip_change_by_console(self):
            if not self.testcase.serial_client:
                return
            try:
                self.log.info('Device IP checking...')
                current_ip = self.testcase.serial_client.get_ip()
            except Exception, e:
                self.log.warning('Error found during getting IP: {}'.format(e), exc_info=True)
                return
            if not current_ip:
                return
            if self.uut_ip == current_ip:
                if self.testcase.ssh_client:
                    #  force it to reconnect
                    self.testcase.ssh_client.update_device_ip(current_ip)
                return
            self.log.warning('Current IP is {}, but the given UUT IP is {}.'.format(current_ip, self.uut_ip))
            self.log.warning('Now changing to use correct deice IP...')
            self.uut_ip = current_ip
            ### XXX: Hotfix issue: sub-test should update utils_to_update_ip but it not.
            if self.testcase.ssh_client and not self.testcase.utils.utils_to_update_ip:
                self.testcase.utils.register_util_to_update_ip(util_inst=self.ssh_client, update_method='update_device_ip')
            ###
            self.testcase.utils.update_ip_to_utils(current_ip)

        def _init_utilities(self, target_inst, kwargs):
            """ Create utilities if it needs. """
            target_inst.power_switch = self.testcase.SETTINGS.is_available('power_switch', None) and \
                self.testcase.utils.gen_power_switch(kwargs)
            target_inst.serial_client = self.testcase.SETTINGS.is_available('serial_client', None) and \
                self.testcase.utils.gen_serial_client(kwargs)
            target_inst.ssh_client = self.testcase.SETTINGS.is_available('ssh_client', None) and \
                self.testcase.utils.gen_ssh_client(kwargs)
            target_inst.uut_owner = self.testcase.SETTINGS.is_available('uut_owner', None) and \
                self.testcase.utils.gen_uut_owner(kwargs)

        def _init_utilities_with_testcase(self, target_inst, testcase, kwargs):
            """ Use the utilities of the given testcase instance instead of creating new one.
                If the given instance does not create utility, then just create one for it, and re.
            """
            if self.testcase.SETTINGS.is_available('power_switch'):
                target_inst.power_switch = testcase.power_switch or self.testcase.utils.gen_power_switch(kwargs, close_at_end=True)
            else:
                target_inst.power_switch = None
            if self.testcase.SETTINGS.is_available('serial_client'):
                target_inst.serial_client = testcase.serial_client or self.testcase.utils.gen_serial_client(kwargs, close_at_end=True)
            else:
                target_inst.serial_client = None
            if self.testcase.SETTINGS.is_available('ssh_client'):
                target_inst.ssh_client = testcase.ssh_client or self.testcase.utils.gen_ssh_client(kwargs, close_at_end=True)
            else:
                target_inst.ssh_client = None
            if self.testcase.SETTINGS.is_available('uut_owner'):
                target_inst.uut_owner = testcase.uut_owner or self.testcase.utils.gen_uut_owner(kwargs, close_at_end=True)
            else:
                target_inst.uut_owner = None

        def post_init(self, of_inst, kwargs):
            """ Initiate anything which need to do after all initiations done. """
            super(GodzillaTestCase.Environment, self).post_init(of_inst, kwargs)
            target_inst = of_inst
            # Handle UUT information.
            self.testcase.uut.update_UUT_info() # Init all the device info.
            self.update_popcorn_info()
            self.init_UUT_firmware_version() # For check version before execute test.
            self.init_UUT_model(kwargs) # Set model
            if hasattr(self, 'update_during_post_init'): self.update_during_post_init() # update after init UUT.

            # Check test device is support to run test or not.
            self.check_test_model()

            # Handle otaclient.
            if self.testcase.ssh_client:
                self.log.info('.'*75)
                if self.enable_auto_ota:
                    self.log.info('Start otaclient...')
                    if self.testcase.ssh_client.check_is_kdp_rnd_device():
                        self.log.info('Model is {}, unlock otaclient property ...'.format(self.testcase.uut.get('model')))
                        self.testcase.ssh_client.unlock_otaclient_service_kdp()
                    else:
                        self.testcase.ssh_client.start_otaclient_service()
                else:
                    self.log.info('Stop otaclient...')
                    if self.testcase.ssh_client.check_is_kdp_rnd_device():
                        self.log.info('Model is {}, lock otaclient property ...'.format(self.testcase.uut.get('model')))
                        self.testcase.ssh_client.lock_otaclient_service_kdp()
                    else:
                        self.testcase.ssh_client.stop_otaclient_service()
                self.log.info('.'*75)

            # Attach user after network is connected.
            if self.testcase.uut_owner:
                if not self.testcase.uut_owner.get_device().json().get("firstUserAttached"):   # init client if it is new.
                    env_version = 'v2'
                    client_settings = {}
                    if self.testcase.uut['config_url']:  # Use Config URL of test device.
                        self.log.info('Update config URL: {}'.format(self.testcase.uut['config_url']))
                        client_settings = {'config_url': self.testcase.uut['config_url']}
                    if self.testcase.uut.get('environment') == 'prod': # Workaround solution for admin token cannot use on prod
                        self.log.warning('Env is {}, skipped the wait cloud connected check ...'.format(self.testcase.uut.get('environment')))
                        self.testcase.uut_owner.init_session(client_settings=client_settings, env_version=env_version, with_cloud_connected=False)
                    else:
                        self.log.info('Env is {}, start wait cloud connected check ...'.format(self.testcase.uut.get('environment')))
                        self.testcase.uut_owner.init_session(client_settings=client_settings, env_version=env_version)

            # Enbale PIP.
            if self.testcase.uut_owner and self.testcase.uut_owner.id == 0:
                try:
                    self.testcase.uut_owner.enable_pip()
                except:
                    pass

        def init_from_UUT_file(self, kwargs):
            pass

        def dump_to_dict(self):
            """ Dump attributes to a dict object which can pass into input_parse(). """
            # Collect Environment attributes, remove unused attributes data from dict.
            settings = super(GodzillaTestCase.Environment, self).dump_to_dict()
            settings.pop('UUT_firmware_version', None)
            return settings

        def init_UUT_firmware_version(self):
            """ UUT_firmware_version is relevant to check_firmware_consistency() and reset_test_result(). """
            if self.firmware_version: # Specify a version then just set it as default.
                self.testcase.uut['firmware'] = self.UUT_firmware_version = self.firmware_version
            else: # Is this a valid case?
                self.log.warning('--firmware_version is not supplied without available SSH connection.')
                self.UUT_firmware_version = None
                if not self.disable_save_result or self.dry_run:
                    self.log.warning('The "build" of test result will be set to None.')
                self.disable_firmware_consistency = False
                # if not self.disable_firmware_consistency:
                    # self.disable_firmware_consistency = False
                    # self.log.warning('Set disable_firmware_consistency to False')
                    #raise RuntimeError('Unable to check firmware consistency. Please execute test with --disable_firmware_consistency.')

        def init_UUT_model(self, kwargs):
            # Keep value from SSH is the first priority, only update value by custom value when SSH is disable.
            if self.testcase.uut.get('model'):
                return
            if self.is_subtask: # Update model from integration test.
                input_uut = getattr(kwargs.get(self.EXPORT_FILED), 'uut', {})
                self.testcase.uut['model'] = input_uut.get('model')
            # If argument is specified, then always use it.
            if self.model:
                self.testcase.uut['model'] = self.model

        def check_test_model(self):
            if not self.testcase.uut.get('model'): # No model information.
                return
            if not self.run_models: # No check list.
                return
            for model in self.run_models:
                if model.lower() == self.testcase.uut['model'].lower(): # test model is matched.
                    self.log.info('Since test device is {}, allowed to run test case'.format(self.testcase.uut['model']))
                    return
            # TODO: Support report in single test case. May move it out of init step, or add create report for it.
            raise self.testcase.err.TestSkipped('Since test device is {}, skip this test case.'.format(self.testcase.uut['model']))

        def update_popcorn_info(self):
            # Only update when it's empty.
            if not self.testcase.FW_BUILD:
                if self.firmware_version:
                    self.testcase.FW_BUILD = self.firmware_version
                else:
                    self.testcase.FW_BUILD = self.testcase.uut.get('firmware')
                regex = r"(.+)\.(\d+)"
                matches = re.match(regex, self.testcase.FW_BUILD)
                if matches:
                    # Full match: 3.00.8, group 1: 3.00, group 2: 8
                    version = matches.group(1)
                    build = matches.group(2)
                    self.testcase.FW_BUILD = version+'.'+build
                if not self.testcase.VERSION:
                    self.testcase.VERSION = version
                if not self.testcase.BUILD:
                    self.testcase.BUILD = build
            if self.testcase.uut.get('model'):
                if not self.testcase.PLATFORM:
                    self.testcase.PLATFORM = self.testcase.uut.get('model')
                if not self.testcase.PROJECT:
                    self.testcase.PROJECT = "Godzilla"

            if self.testcase.uut.get('environment') and not self.testcase.ENVIROMENT:
                self.testcase.ENVIROMENT = self.testcase.uut.get('environment')

            if self.testcase.uut_owner and not self.testcase.USER:
                self.testcase.USER = self.testcase.uut_owner.username
