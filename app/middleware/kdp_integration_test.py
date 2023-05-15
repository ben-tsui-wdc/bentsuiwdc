# -*- coding: utf-8 -*-
""" Implementation of Integration Test Case for KDP product.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# middleware modules
from core.integration_extensions import IntegrationExtensions, IntegrationComponent
from kdp_test_case import KDPTestCase
from godzilla_integration_test import KaminoIntegrationComponent


class KDPIntegrationTest(IntegrationExtensions, KDPTestCase):
    """ Superclass for integration test. """

    #
    # MiddleWare Hooks Area
    #
    def _before_launch_subtest(self):
        # Render correlation id for sub test.
        if self.uut_owner and self.env.subtest_index != 1:
            self.uut_owner.render_correlation_id()


    class Environment(IntegrationExtensions.Environment, KDPTestCase.Environment):

        def init_integration_components(self, of_inst):
            """ Initiate components """
            super(KDPIntegrationTest.Environment, self).init_integration_components(of_inst)
            target_inst = of_inst
            target_inst.integration = KDPIntegrationComponent(testcase_inst=target_inst) # replace

        def init_components(self, of_inst, kwargs):
            """ Initiate components """
            super(KDPIntegrationTest.Environment, self).init_components(of_inst, kwargs)
            target_inst = of_inst
            # disable logstash
            target_inst.data.upload_logstash = False

class KDPIntegrationComponent(KaminoIntegrationComponent):
    """ Test cases management of integration test. """
    pass
