# -*- coding: utf-8 -*-
""" Implementation of Integration Test Case for Kamino product.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# middleware modules
from core.integration_extensions import IntegrationExtensions, IntegrationComponent
from test_case import TestCase


class IntegrationTest(IntegrationExtensions, TestCase):
    """ Superclass for integration test. """

    #
    # MiddleWare Hooks Area
    #
    def _before_launch_subtest(self):
        # Render correlation id for sub test.
        if self.uut_owner and self.env.subtest_index != 1:
            self.uut_owner.render_correlation_id()


    class Environment(IntegrationExtensions.Environment, TestCase.Environment):

        def init_integration_components(self, of_inst):
            """ Initiate components """
            super(IntegrationTest.Environment, self).init_integration_components(of_inst)
            target_inst = of_inst
            target_inst.integration = KaminoIntegrationComponent(testcase_inst=target_inst) # replace


class KaminoIntegrationComponent(IntegrationComponent):
    """ Test cases management of integration test. """

    def _extend_hook_of_init_subtest_exception(self, input_env, subtest):
        input_env['run_models'] = None # Disable for sub-caess.
        # Set values from intgration test.
        # TODO: firmware_version may need update by ADB or others, but sometimes fw may uppdated in test case.
        input_env['firmware_version'] = self.testcase.env.UUT_firmware_version or self.testcase.env.firmware_version or self.testcase.uut.get('firmware')
        input_env['model'] = self.testcase.env.model or self.testcase.uut.get('model')

    def _extend_hook_of_reder_subtest(self, locals):
        subtest = locals['subtest']
        prefix = locals['prefix']
        return
