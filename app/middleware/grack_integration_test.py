# -*- coding: utf-8 -*-
""" Implementation of Integration Test Case for Grack product.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# middleware modules
from core.integration_extensions import IntegrationExtensions
from grack_test_case import GrackTestCase


class GrackIntegrationTest(IntegrationExtensions, GrackTestCase):
    """ Superclass for integration test. """

    #
    # MiddleWare Hooks Area
    #

    class Environment(IntegrationExtensions.Environment, GrackTestCase.Environment):
        pass
