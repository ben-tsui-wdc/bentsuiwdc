# -*- coding: utf-8 -*-
""" Implementation of Integration Core Test Case.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# middleware modules
from integration_extensions import IntegrationExtensions
from test_case import TestCase as CoreTestCase


class IntegrationTest(IntegrationExtensions, CoreTestCase):
    """ Superclass for integration test. """

    class Environment(IntegrationExtensions.Environment, CoreTestCase.Environment):
        pass
