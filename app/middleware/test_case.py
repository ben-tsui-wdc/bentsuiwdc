# -*- coding: utf-8 -*-
""" Implementation of Test case for Kamino product.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"


# std modules
import datetime
import os
# platform modules
from platform_libraries.pyutils import retry, rename_duplicate_filename
# middleware modules
from core.test_case import Settings, TestCase as CoreTestCase
from component import ExtensionComponent, UUTInformationComponent


class TestCase(CoreTestCase):
    """ Superclass for test case. """

    # For Popcorn
    COMPONENT = 'PLATFORM'

    SETTINGS = Settings(**{ # Default flags for features, accept the changes if SETTINGS data supplied;
                 # For input arguments relative features, the key name is the same as input argument.
                 # Set True to Value means Enable this feature or Set True to this attribute as default value;
                 # Set False to Value means Disable this feature or Set False to this attribute as default value.
        'disable_loop': False,
        'disable_firmware_consistency': False,
        'adb': True,
        'ap': True,
        'btle_client': True,
        'power_switch': True, 
        'serial_client': True,
        'uut_owner' : True,
        'always_do_after_test': True,
        'always_do_after_loop': True,
        'run_models': None
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
         # Always save and clean locat log.
        if not self.adb:
            self.env.log.warning('Unable to save logs because of ADB is disabled.')
        elif not self.adb.connected:
            self.env.log.warning('Unable to save logs because of ADB is disconnected.')
        else:
            # Save locat log.
            if not getattr(self.env, 'disable_export_logcat_log', False) and not getattr(self.env, 'disable_export_itr_logcat_log', False):
                self.data.export_logcat_log( # TODO: Check it need another arg or not.
                    clean_logcat=not getattr(self.env, 'disable_clean_logcat_log', False),
                    name_postfix='#{}'.format(self.env.iteration)
                )
        CoreTestCase.finally_of_single_iteration(self)

    def finally_of_exit_test(self):
        try:
            self.uut.update_UUT_info()
        except Exception, e:
            self.env.log.warning(e, exc_info=True)
        # Always save locat log & upload logs to sumologic.
        if not self.adb:
            self.env.log.warning('Unable to save logs because of ADB is disabled.')
        elif not self.adb.connected:
            self.env.log.warning('Unable to save logs because of ADB is disconnected.')
        else:
            # Upload logs to sumologic.
            if not getattr(self.env, 'disable_upload_logs_to_sumologic', False):
                self.data.upload_logs_to_sumologic()
            # Print out log metrics.
            if not getattr(self.env, 'disable_get_log_metrics', False):
                self.adb.get_log_metrics()
            # Save locat log.
            if not getattr(self.env, 'disable_export_logcat_log', False):
                self.data.export_logcat_log(clean_logcat=not getattr(self.env, 'disable_clean_logcat_log', False))
        CoreTestCase.finally_of_exit_test(self)

    def _before_single_test_steps(self):
        self.uut.show_device()
        if not self.env.disable_firmware_consistency: self.ext.check_firmware_consistency()

    def _before_single_iteration_steps(self):
        # Render correlation id for each iteration.
        if self.uut_owner and self.env.iteration != 1:
            self.uut_owner.render_correlation_id()

    def device_log(self, msg, force=False):
        # Log utility to print both on local consloe and device.
        self.uut.adb_log(msg, force=force)

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

        def init_flow_variables(self, of_inst, kwargs):
            """ Initiate variables for bulitin testing flow. """
            super(TestCase.Environment, self).init_flow_variables(of_inst, kwargs)
            target_inst = of_inst
            # FIXME: if we have solution to know input argument is supplied.
            target_inst.disable_firmware_consistency = \
                self.testcase.SETTINGS.is_available('disable_firmware_consistency') or \
                kwargs.get('disable_firmware_consistency', False) # Control flag to not check firmware consistency.
            target_inst.disable_clean_logcat_log = kwargs.get('disable_clean_logcat_log', False)
            target_inst.disable_export_logcat_log = kwargs.get('disable_export_logcat_log', False)
            target_inst.disable_export_itr_logcat_log = kwargs.get('disable_export_itr_logcat_log', False)
            target_inst.disable_upload_logs_to_sumologic = kwargs.get('disable_upload_logs_to_sumologic', False)
            target_inst.disable_get_log_metrics = kwargs.get('disable_get_log_metrics', False)
            target_inst.enable_auto_ota = self.testcase.SETTINGS.is_available('enable_auto_ota') or \
                kwargs.get('enable_auto_ota', False) # Control flag to not stop otaclient.
            target_inst.run_models = kwargs.get('run_models', None) or self.testcase.SETTINGS.get('run_models')

        def init_variables(self, of_inst, kwargs):
            """ Initiate common variables """
            super(TestCase.Environment, self).init_variables(of_inst, kwargs)
            target_inst = of_inst
            # UUT and Test settings
            target_inst.cloud_env = kwargs.get('cloud_env')
            target_inst.cloud_variant = kwargs.get('cloud_variant')
            target_inst.firmware_version = kwargs.get('firmware_version')
            target_inst.model = kwargs.get('model')
            target_inst.uut_ip = kwargs.get('uut_ip')
            target_inst.uut_port = kwargs.get('uut_port')
            # ADB Server
            target_inst.adb_server_ip = kwargs.get('adb_server_ip')
            target_inst.adb_server_port = kwargs.get('adb_server_port')
            target_inst.adb_retry_with_reboot_device = kwargs.get('adb_retry_with_reboot_device')
            # Power Switch
            target_inst.power_switch_ip = kwargs.get('power_switch_ip')
            target_inst.power_switch_port = kwargs.get('power_switch_port') # Custom port for Test
            # Serail Client
            target_inst.serial_server_ip = kwargs.get('serial_server_ip')
            target_inst.serial_server_port = kwargs.get('serial_server_port')
            target_inst.serial_server_debug = kwargs.get('serial_server_debug')
            target_inst.disable_serial_server_daemon_msg = kwargs.get('disable_serial_server_daemon_msg')
            # BTLE Settings
            target_inst.btle_addr = kwargs.get('btle_addr')
            # WiFi Settings
            target_inst.ap_ssid = kwargs.get('ap_ssid')
            target_inst.ap_password = kwargs.get('ap_password')
            target_inst.ap_security_mode = kwargs.get('ap_security_mode')
            # AP Settings
            target_inst.ap_ip = kwargs.get('ap_ip')
            target_inst.ap_user = kwargs.get('ap_user')
            target_inst.ap_user_pwd = kwargs.get('ap_user_pwd')
            target_inst.ap_root_pwd = kwargs.get('ap_root_pwd')
            target_inst.ap_port = kwargs.get('ap_port')
            # UUT Onwer
            target_inst.username = kwargs.get('username')
            target_inst.password = kwargs.get('password')
            # Folder Paths
            target_inst.logcat_name = kwargs.get('logcat_name') or 'logcat'

        def init_popcorn_variables(self, of_inst, kwargs):
            """ Initiate Popcorn variables """
            target_inst = of_inst
            if target_inst.env.cloud_env: target_inst.ENVIROMENT = target_inst.env.cloud_env
            if target_inst.env.firmware_version:
                target_inst.VERSION, target_inst.BUILD = target_inst.env.firmware_version.split('-')
                target_inst.FW_BUILD = target_inst.env.firmware_version
            if target_inst.env.model: target_inst.PLATFORM = target_inst.env.model
            super(TestCase.Environment, self).init_popcorn_variables(of_inst, kwargs)

        def init_components(self, of_inst, kwargs):
            """ Initiate components """
            super(TestCase.Environment, self).init_components(of_inst, kwargs)
            target_inst = of_inst
            target_inst.ext = ExtensionComponent(testcase_inst=self.testcase)
            target_inst.uut = UUTInformationComponent(testcase_inst=self.testcase)

        def init_utilities(self, of_inst, kwargs):
            """ Initiate common utilities """
            super(TestCase.Environment, self).init_utilities(of_inst, kwargs)
            self.init_from_UUT_file(kwargs)
            target_inst = of_inst
            # Connect network for Yoda.
            if target_inst.serial_client:
                if not target_inst.serial_client.serial_is_connected(): # Sub-test MAY NOT run this part.
                    target_inst.serial_client.initialize_serial_port() # Connect as default
                    # Setup and connect WiFi
                    if target_inst.env.ap_ssid:
                        # Clear up old AP settings to avoid test recovery when disconnect.(Only for platfrom site, not sure Android behaviros)
                        target_inst.serial_client.clear_reserve_wifi_config()
                        self.log.info('Since ap_ssid is specified, connect to WiFi...')
                        if target_inst.btle_client: # Use BLTE
                            target_inst.serial_client.enable_client_mode()
                            target_inst.serial_client.remove_all_network(save_changes=True, restart_wifi=True, timeout=60, raise_error=False)
                            self.log.info('Use BLTE...')
                            self.connect_with_btle(ssid=target_inst.env.ap_ssid, password=target_inst.env.ap_password, testcase=target_inst)
                        else: # Use serial
                            self.log.info('Use Serial...')
                            target_inst.serial_client.connect_WiFi(ssid=target_inst.env.ap_ssid, password=target_inst.env.ap_password,
                                security_mode=target_inst.env.ap_security_mode, timeout=60*30, reboot_after=60*10, raise_error=True)
                # Always check IP is correct or not if serial client is support.
                self.check_ip_change_by_console()
                # Make sure read queue is clean for each test.
                target_inst.serial_client.init_read_queue()
            # Register serial client into adb client for restart ADB daemon.
            if target_inst.adb and target_inst.serial_client:
                target_inst.adb.set_serial_client(target_inst.serial_client)
            # Register adb client into uut_owner for "ping out from device" in KAM200-6545. 
            if target_inst.adb and target_inst.uut_owner:
                target_inst.uut_owner.set_adb_client(target_inst.adb)
            # Connect ADB afer network is connected.
            if target_inst.adb and not target_inst.adb.connected:
                target_inst.adb.connect() # Connect as default
            # Connect AP
            if target_inst.ap and (not target_inst.ap.client or not target_inst.ap.is_active()):
                target_inst.ap.connect() # Connect as default

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
                return
            self.log.warning('Current IP is {}, but the given UUT IP is {}.'.format(current_ip, self.uut_ip))
            self.log.warning('Now changing to use correct deivce IP...')
            self.uut_ip = current_ip
            ### XXX: Hotfix issue: sub-test should update utils_to_update_ip but it not.
            if self.testcase.adb and not self.testcase.utils.utils_to_update_ip:
                self.testcase.utils.register_util_to_update_ip(util_inst=self.adb, update_method='update_device_ip')
            ###
            self.testcase.utils.update_ip_to_utils(current_ip)

        def connect_with_btle(self, ssid, password, testcase=None, retry_times=60, reboot_ap=None):
            import time
            from bluepy.btle import BTLEException

            testcase.serial_client.enable_client_mode()
            ### Disable debug message for too many message.
            org_flag = testcase.serial_client.daemon_msg
            testcase.serial_client.daemon_msg = False
            ###
            try:
                for idx in xrange(1, retry_times+1): # Workaround retry for BT disconnect issue, this issue may recovery AP settings.
                    try:
                        testcase.serial_client.write_logcat('Set Wi-Fi with bluetooth #{}...'.format(idx))
                        testcase.btle_client.set_wifi(ssid, password)
                        testcase.serial_client.write_logcat('Wait notify...')
                        notify = testcase.btle_client.get_notify(timeout=60*5) # Wiat for device IP ready.
                        try:
                            testcase.btle_client.raise_notify_error(notify)
                        except RuntimeError:
                            if reboot_ap: # Reboot AP for fix password not correct somehow.
                                reboot_ap()
                        if not retry(  # To make sure what SSID actually use.
                                    func=testcase.serial_client.list_network, filter_keyword=ssid,
                                    retry_lambda=lambda x: not x or '\t[CURRENT]' not in x[0],
                                    delay=5, max_retry=6, log=self.log.warning # XXX: Retry to wait ssid setup. (No sure this part has timing issue or not)
                                ):
                            raise RuntimeError('SSID is not correct, set Wi-Fi again')
                        if not testcase.serial_client.wait_for_ip(timeout=60):
                            raise RuntimeError('No device IP, set Wi-Fi again')
                        testcase.serial_client.get_wifi_logs() # More log to check.
                        testcase.serial_client.write_logcat('Got IP.')
                        return
                    except Exception as e:
                        try:
                            testcase.log.warning(e, exc_info=True)
                            testcase.serial_client.write_logcat('Test script catched exception')
                            testcase.serial_client.get_wifi_logs() # More log to check.
                            # Print logcat on screen.
                            testcase.log.warning('.'*75)
                            testcase.serial_client.export_logcat(path=rename_duplicate_filename('{}/wifi_setup_failed'.format(self.output_folder)))
                            testcase.log.warning('.'*75)
                            testcase.serial_client.scan_wifi_ap(list_network=True)
                            testcase.log.warning('.'*75)
                        except Exception as e: # not break test
                            testcase.log.warning('[Exception]{}'.format(e), exc_info=True)
                        finally:
                            if isinstance(e, BTLEException):
                                # For report to RTK.
                                try:
                                    testcase.serial_client.serial_write('test -e /sdcard/btsnoop_hci.cfa && mv /sdcard/btsnoop_hci.cfa /data/wd/diskVolume0/btsnoop_hci.cfa.{}'.format(int(time.time())))
                                    testcase.btle_client.disconnect()
                                    time.sleep(15)
                                    testcase.btle_client.connect(testcase.btle_client.addr)
                                except Exception as e: # not break test
                                    testcase.log.warning('[Finally-Exception]{}'.format(e), exc_info=True)
                            #if isinstance(e, RuntimeError): # Raise the error we don't want to retry.
                            #    raise
                raise testcase.err.TestError('Set Wi-Fi via BTLE failed') # NOTEXCUTED
            finally:
                ### Recover daemon_msg flag.
                testcase.serial_client.daemon_msg = org_flag
                ###

        def _init_utilities(self, target_inst, kwargs):
            """ Create utilities if it needs. """
            target_inst.adb = self.testcase.SETTINGS.is_available('adb', None) and \
                self.testcase.utils.gen_adb(kwargs)
            target_inst.ap = self.testcase.SETTINGS.is_available('ap', None) and \
                self.testcase.utils.gen_ap(kwargs)
            target_inst.btle_client = self.testcase.SETTINGS.is_available('btle_client', None) and \
                self.testcase.utils.gen_btle_client(kwargs)
            target_inst.power_switch = self.testcase.SETTINGS.is_available('power_switch', None) and \
                self.testcase.utils.gen_power_switch(kwargs)
            target_inst.serial_client = self.testcase.SETTINGS.is_available('serial_client', None) and \
                self.testcase.utils.gen_serial_client(kwargs)
            target_inst.uut_owner = self.testcase.SETTINGS.is_available('uut_owner', None) and \
                self.testcase.utils.gen_uut_owner(kwargs)

        def _init_utilities_with_testcase(self, target_inst, testcase, kwargs):
            """ Use the utilities of the given testcase instance instead of creating new one.
                If the given instance does not create utility, then just create one for it, and re.
            """
            if self.testcase.SETTINGS.is_available('adb'):
                target_inst.adb = testcase.adb or self.testcase.utils.gen_adb(kwargs, close_at_end=True)
            else:
                target_inst.adb = None
            if self.testcase.SETTINGS.is_available('ap'):
                target_inst.ap = testcase.ap or self.testcase.utils.gen_ap(kwargs, close_at_end=True)
            else:
                target_inst.ap = None
            if self.testcase.SETTINGS.is_available('btle_client'):
                target_inst.btle_client = testcase.btle_client or self.testcase.utils.gen_btle_client(kwargs, close_at_end=True)
            else:
                target_inst.btle_client = None
            if self.testcase.SETTINGS.is_available('power_switch'):
                target_inst.power_switch = testcase.power_switch or self.testcase.utils.gen_power_switch(kwargs, close_at_end=True)
            else:
                target_inst.power_switch = None
            if self.testcase.SETTINGS.is_available('serial_client'):
                target_inst.serial_client = testcase.serial_client or self.testcase.utils.gen_serial_client(kwargs, close_at_end=True)
            else:
                target_inst.serial_client = None
            if self.testcase.SETTINGS.is_available('uut_owner'):
                target_inst.uut_owner = testcase.uut_owner or self.testcase.utils.gen_uut_owner(kwargs, close_at_end=True)
            else:
                target_inst.uut_owner = None

        def post_init(self, of_inst, kwargs):
            """ Initiate anything which need to do after all initiations done. """
            super(TestCase.Environment, self).post_init(of_inst, kwargs)
            target_inst = of_inst
            # Handle UUT information.
            self.testcase.uut.update_UUT_info() # Init all the device info.
            self.update_popcorn_info()
            self.init_UUT_firmware_version() # For check version before execute test.
            self.init_UUT_model(kwargs) # Set model when ADB is disable.

            # Check test device is support to run test or not.
            self.check_test_model()

            # Attach user after network is connected.
            if self.testcase.uut_owner:
                if not self.testcase.uut_owner.id_token: # init client if it is new.
                    env_version = None
                    # Build version later than 5.1 should use new config URL.
                    if self.testcase.uut.get('firmware') and self.testcase.uut['firmware'].startswith('5.1') and \
                            self.testcase.uut.get('environment') != 'prod':
                        env_version = 'v2'
                    client_settings = {}
                    if self.testcase.uut['config_url']: # Use Config URL of test device.
                        self.log.info('Update config URL: {}'.format(self.testcase.uut['config_url']))
                        client_settings = {'config_url': self.testcase.uut['config_url']}
                    if self.testcase.uut.get('environment') == 'prod': # Workaround solution for admin token cannot use on prod
                        self.log.warning('Env is {}, skipped the wait cloud connected check ...'.format(self.testcase.uut.get('environment')))
                        self.testcase.uut_owner.init_session(client_settings=client_settings, env_version=env_version, with_cloud_connected=False)
                    else:
                        self.log.info('Env is {}, start wait cloud connected check ...'.format(self.testcase.uut.get('environment')))
                        self.testcase.uut_owner.init_session(client_settings=client_settings, env_version=env_version)

            # Handle otaclient.
            if self.testcase.adb:
                self.log.info('.'*75)
                if self.enable_auto_ota:
                    self.log.info('Start otaclient...')
                    self.testcase.adb.start_otaclient()
                else:
                    self.log.info('Stop otaclient...')
                    self.testcase.adb.stop_otaclient()
                self.log.info('.'*75)

            # Enbale PIP, and only owner can enable pip
            if self.testcase.uut_owner and self.testcase.uut_owner.id == 0:
                try:
                    self.testcase.uut_owner.enable_pip()
                except:
                    pass

        def init_from_UUT_file(self, kwargs):
            # TODO: Need to think how to create utilities here.
            self.testcase.uut.update_from_UUT_file()
            return
            if not self.adb_server_ip:
                if self.uut['checkout_UUT'].get('adbServer'): self.adb_server_ip = self.uut['checkout_UUT']['adbServer'].get('ipAddress')
            if not self.adb_server_port:
                if self.uut['checkout_UUT'].get('adbServer'): self.adb_server_port = self.uut['checkout_UUT']['adbServer'].get('port')
            if not self.power_switch_ip:
                if self.uut['checkout_UUT'].get('powerSwitch'): self.power_switch_ip = self.uut['checkout_UUT']['powerSwitch'].get('ipAddress')
            if not self.power_switch_port:
                if self.uut['checkout_UUT'].get('powerSwitch'): self.power_switch_port = self.uut['checkout_UUT']['powerSwitch'].get('port')
            if not self.uut_ip:
                self.uut_ip = self.uut['checkout_UUT'].get('internalIPAddress')

        def dump_to_dict(self):
            """ Dump attributes to a dict object which can pass into input_parse(). """
            # Collect Environment attributes, remove unused attributes data from dict.
            settings = super(TestCase.Environment, self).dump_to_dict()
            settings.pop('UUT_firmware_version', None)
            return settings

        def init_UUT_firmware_version(self):
            """ UUT_firmware_version is relevant to check_firmware_consistency() and reset_test_result(). """
            if self.firmware_version: # Specify a version then just set it as default.
                self.testcase.uut['firmware'] = self.UUT_firmware_version = self.firmware_version
            elif getattr(self.testcase.adb, 'connected', False): # Init it with ADB.
                self.UUT_firmware_version = self.testcase.uut['firmware']
            else: # Is this a valid case?
                self.log.warning('--firmware_version is not supplied without available ADB connection.')
                self.UUT_firmware_version = None
                if not self.disable_save_result or self.dry_run:
                    self.log.warning('The "build" of test result will be set to None.')
                if not self.disable_firmware_consistency:
                    self.disable_firmware_consistency = False
                    self.log.warning('Set disable_firmware_consistency to False')
                    #raise RuntimeError('Unable to check firmware consistency. Please execute test with --disable_firmware_consistency.')

        def init_UUT_model(self, kwargs):
            # Keep value from ADB is the first priority, only update value by custom value when ADB is disable.
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
                if '-' in self.testcase.FW_BUILD:
                    version, build = self.testcase.FW_BUILD.split('-')
                else:
                    version = self.testcase.FW_BUILD.split('.')[0]
                    build = self.testcase.FW_BUILD.replace(version+".", "")
                if not self.testcase.VERSION:
                    self.testcase.VERSION = version
                if not self.testcase.BUILD:
                    self.testcase.BUILD = build
            if self.testcase.uut.get('model'):
                if not self.testcase.PLATFORM:
                    self.testcase.PLATFORM = self.testcase.uut.get('model')
                if not self.testcase.PROJECT:
                    if 'yoda' in self.testcase.uut.get('model'):
                        self.testcase.PROJECT = 'ibi'
                    if 'monarch' in self.testcase.uut.get('model') or 'pelican' in self.testcase.uut.get('model'):
                        self.testcase.PROJECT = 'MCH'

            if self.testcase.uut.get('environment') and not self.testcase.ENVIROMENT:
                self.testcase.ENVIROMENT = self.testcase.uut.get('environment')

            if self.testcase.uut_owner and not self.testcase.USER:
                self.testcase.USER = self.testcase.uut_owner.username
