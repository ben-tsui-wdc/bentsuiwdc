# -*- coding: utf-8 -*-
""" Implementation of Test case for Grack product.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# middleware modules
from core.test_case import Settings, TestCase as CoreTestCase
from component import ExtensionComponent, UUTInformationComponent


class GrackTestCase(CoreTestCase):
    """ Superclass for test case. """

    SETTINGS = Settings(**{
        'disable_loop': False,
        'power_switch': True, 
        'serial_client': True,
        'always_do_after_test': True,
        'always_do_after_loop': True
    })

    class Environment(CoreTestCase.Environment):
        """ Initiate all attributes which TestCase use here. """

        def init_variables(self, of_inst, kwargs):
            """ Initiate common variables """
            super(GrackTestCase.Environment, self).init_variables(of_inst, kwargs)
            target_inst = of_inst
            # UUT and Test settings
            target_inst.firmware_version = kwargs.get('firmware_version')
            target_inst.model = kwargs.get('model')
            target_inst.uut_ip = kwargs.get('uut_ip')
            target_inst.uut_port = kwargs.get('uut_port')
            # Power Switch
            target_inst.power_switch_ip = kwargs.get('power_switch_ip')
            target_inst.power_switch_port = kwargs.get('power_switch_port') # Custom port for Test
            # Serail Client
            target_inst.serial_server_ip = kwargs.get('serial_server_ip')
            target_inst.serial_server_port = kwargs.get('serial_server_port')
            target_inst.serial_server_debug = kwargs.get('serial_server_debug')
            target_inst.disable_serial_server_daemon_msg = kwargs.get('disable_serial_server_daemon_msg')
            # UUT Onwer
            target_inst.username = kwargs.get('username')
            target_inst.password = kwargs.get('password')

        def init_components(self, of_inst, kwargs):
            """ Initiate components """
            super(GrackTestCase.Environment, self).init_components(of_inst, kwargs)
            target_inst = of_inst
            target_inst.ext = ExtensionComponent(testcase_inst=self.testcase)
            target_inst.uut = UUTInformationComponent(testcase_inst=self.testcase)

        def init_utilities(self, of_inst, kwargs):
            """ Initiate common utilities """
            super(GrackTestCase.Environment, self).init_utilities(of_inst, kwargs)
            target_inst = of_inst

        def _init_utilities(self, target_inst, kwargs):
            """ Create utilities if it needs. """
            target_inst.power_switch = self.testcase.SETTINGS.is_available('power_switch', None) and \
                self.testcase.utils.gen_power_switch(kwargs)
            target_inst.serial_client = self.testcase.SETTINGS.is_available('serial_client', None) and \
                self.testcase.utils.gen_serial_client(kwargs)

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

        def post_init(self, of_inst, kwargs):
            """ Initiate anything which need to do after all initiations done. """
            super(GrackTestCase.Environment, self).post_init(of_inst, kwargs)
            target_inst = of_inst
            # Handle UUT information.
            self.init_UUT_model() # Set model when ADB is disable.

        def init_UUT_model(self):
            # Keep value from ADB is the first priority, only update value by custom value when ADB is disable.
            if self.testcase.uut.get('model'):
                return
            self.testcase.uut['model'] = self.model
