# -*- coding: utf-8 -*-
""" Implementation of Test case for KDP product.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import datetime
import os
import re
import copy
# middleware modules
from core.test_case import Settings, TestCase as CoreTestCase
from godzilla_test_case import GodzillaTestCase
# 3rd party
from packaging.version import parse


class KDPTestCase(GodzillaTestCase):
    """ Superclass for test case. """

    # For Popcorn
    COMPONENT = 'PLATFORM'

    SETTINGS = Settings(**{ # Default flags for features, accept the changes if SETTINGS data supplied;
                 # For input arguments relative features, the key name is the same as input argument.
                 # Set True to Value means Enable this feature or Set True to this attribute as default value;
                 # Set False to Value means Disable this feature or Set False to this attribute as default value.
        'disable_loop': False,
        'disable_firmware_consistency': True,
        'ap': False,
        'btle_client': False,
        'power_switch': True, 
        'serial_client': True,
        'uut_owner' : True,
        'nasadmin' : True,
        'always_do_after_test': True,
        'always_do_after_loop': True,
        'run_models': None,
        'ssh_client': True
    })

    #
    # MiddleWare Hooks Area
    #
    def finally_of_single_iteration(self):
        if not self.ssh_client:
            self.env.log.warning('Unable to save logs because of SSH is disabled.')
        elif not self.ssh_client.check_ssh_connectable:
            self.env.log.warning('Unable to save logs because of SSH is disconnected.')
        else: # TODO: Clean logs for each iteration if we needs.
            # Save device log.
            if not getattr(self.env, 'disable_export_device_log', False):
                self.data.export_kdp_logs(
                    clean_device_logs=not getattr(self.env, 'disable_clean_device_logs', False),
                    name_postfix='#{}'.format(self.env.iteration),
                    device_tmp_log=self.env.device_tmp_log
                )
        CoreTestCase.finally_of_single_iteration(self)

    def finally_of_exit_test(self):
        try:
            self.uut.update_UUT_info()
        except Exception, e:
            self.env.log.warning(e, exc_info=True)
        # Always save locat log.
        if not hasattr(self, 'ssh_client') or not self.ssh_client:
            self.env.log.warning('Unable to save logs because of SSH is disabled.')
        elif not self.ssh_client.check_ssh_connectable:
            self.env.log.warning('Unable to save logs because of SSH is disconnected.')
        else:
            # Save device log.
            if not getattr(self.env, 'disable_export_device_log', False):
                self.data.export_kdp_logs(
                    clean_device_logs=not getattr(self.env, 'disable_clean_device_logs', False),
                    device_tmp_log=self.env.device_tmp_log
                )
        CoreTestCase.finally_of_exit_test(self)

 
    class Environment(GodzillaTestCase.Environment):
        """ Initiate all attributes which TestCase use here. """

        def init_utilities(self, of_inst, kwargs):
            """ Initiate common utilities """
            super(KDPTestCase.Environment, self).init_utilities(of_inst, kwargs)
            target_inst = of_inst

        def _init_utilities(self, target_inst, kwargs):
            super(KDPTestCase.Environment, self)._init_utilities(target_inst, kwargs)

            target_inst.nasadmin = self.testcase.SETTINGS.is_available('nasadmin', None) and \
                self.testcase.utils.gen_nasadmin_client(kwargs, rest_client=target_inst.uut_owner)

            if target_inst.serial_client:
                target_inst.serial_client.device_type = 'kdp'
                target_inst.serial_client.password = self.console_password

        def _init_utilities_with_testcase(self, target_inst, testcase, kwargs):
            super(KDPTestCase.Environment, self)._init_utilities_with_testcase(target_inst, testcase, kwargs)

            if self.testcase.SETTINGS.is_available('nasadmin'):
                target_inst.nasadmin = testcase.nasadmin or self.testcase.utils.gen_nasadmin_client(
                        kwargs, rest_client=target_inst.uut_owner)
            else:
                target_inst.nasadmin = None

        def init_variables(self, of_inst, kwargs):
            if kwargs.get('model') in ['rocket', 'drax']: # set default values per given params
                self.device_tmp_log = '/Volume1/logs.tgz'
            else:
                self.device_tmp_log = '/data/logs.tgz'
            super(KDPTestCase.Environment, self).init_variables(of_inst, kwargs)
            target_inst = of_inst
            # serial client
            password = ''
            if kwargs.get('console_password') is not None:
                password = kwargs['console_password']
            if self.need_console_password():
                password = '0502e94f11f527cb'  # only for dev1/qa1 and has /wd_config/enable_root
            target_inst.console_password = password

        def update_during_post_init(self):
            if self.testcase.uut['model'] in ['rocket', 'drax']: # change valuse per detect mdoel
                self.device_tmp_log = '/Volume1/logs.tgz'
                self.log.info('Set device_tmp_log to ' + self.device_tmp_log)

        def post_init(self, of_inst, kwargs):
            super(KDPTestCase.Environment, self).post_init(of_inst, kwargs)
            target_inst = of_inst

            if self.testcase.uut.get('firmware'):
                if not self.is_nasadmin_supported(check_instance=False):
                    self.log.info('set nasAdmin to empty')
                    self.testcase.nasadmin = None

            if self.testcase.nasadmin:
                # check with the same resp for saving call
                resp = self.testcase.nasadmin.can_access_nasAdmin(return_resp=True)
                if resp:
                    if not self.testcase.nasadmin.is_nasAdmin_working(provide_resp=resp):
                        self.testcase.nasadmin.wait_for_nasAdmin_works()
                    if self.testcase.uut_owner:
                        self.testcase.nasadmin.set_rest_client(self.testcase.uut_owner)
                        if self.testcase.nasadmin.is_owner_attached_restsdk():
                            if not self.testcase.nasadmin.is_owner_attached(provide_resp=resp):
                                self.testcase.nasadmin.wait_for_owner_attached()
                else:
                    self.log.info('set nasAdmin to empty')
                    self.testcase.nasadmin = None

        def is_nasadmin_supported(self, check_instance=True):
            if self.testcase.uut.get('firmware'):
                vn = self.testcase.uut['firmware'].split('.')
                if int(vn[0]) < 8 or (int(vn[0]) == 8 and int(vn[1]) < 12):
                    self.log.info('nasAdmin is not supported in this build')
                    return False
            if check_instance and not self.testcase.nasadmin:
                self.log.info('nasAdmin client instance is empty')
                return False
            return True

        def need_console_password(self):
            version = None
            if hasattr(self.testcase, 'uut') and self.testcase.uut.get('firmware'):
                version = self.testcase.uut['firmware']
            elif self.firmware_version:
                version = self.firmware_version

            if version:
                v = parse(version)
                base1 = parse('8.12.0-149')
                base2 = parse('9.4.0-140')
                if (v.major <= 8 and v < base1) or v.major == 9 and v < base2:
                    return False
            else:
                #  TODO: change me if most of our test devices are required password.
                self.log.info("Don't know the build version, suppose it doesn't need console password")
                return False
            self.log.info('Console need password')
            return True

        def update_popcorn_info(self):
            # Only update when it's empty.
            if not self.testcase.FW_BUILD:
                if self.firmware_version:
                    self.testcase.FW_BUILD = self.firmware_version
                else:
                    self.testcase.FW_BUILD = self.testcase.uut.get('firmware')
            version, build = self.testcase.FW_BUILD.split('-')
            if not self.testcase.VERSION:
                self.testcase.VERSION = version
            if not self.testcase.BUILD:
                self.testcase.BUILD = build
            if self.testcase.uut.get('model'):
                if not self.testcase.PLATFORM:
                    self.testcase.PLATFORM = self.testcase.uut.get('model')
                if not self.testcase.PROJECT:
                    self.testcase.PROJECT = "Keystone Device Platform"

            if self.testcase.uut.get('environment') and not self.testcase.ENVIROMENT:
                self.testcase.ENVIROMENT = self.testcase.uut.get('environment')

            if self.testcase.uut_owner and not self.testcase.USER:
                self.testcase.USER = self.testcase.uut_owner.username
