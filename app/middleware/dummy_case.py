# -*- coding: utf-8 -*-
""" Dummy cases are the replacement of normal test cases, they are designed for supporting more convenient
    way to use integration test.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# middleware modules
from core.test_case import Settings, TestCase as CoreTestCase
from test_case import TestCase
from grack_test_case import GrackTestCase

#
# Product Names
#
CORE = 'CORE'
KAMINO = 'KAMINO'
GRACK = 'GRACK'

#
# Basic Utilities
#
def determine(ref_class):
    # Specail handle for duplicate name.
    if ref_class.__name__ in ['TestCase', 'IntegrationTest']:
        if issubclass(ref_class, TestCase):
            return KAMINO
        return CORE
    # Common rules
    rules = {
        ('DummyCase', 'PassCase', 'FailureCase'): CORE,
        ('KaminoDummyCase', 'KaminoPassCase', 'FailureCase'): KAMINO,
        ('GrackTestCase', 'GrackIntegrationTest', 'GrackDummyCase', 'GrackPassCase', 'GrackFailureCase'): GRACK
    }
    for rule, name in rules.iteritems():
        if ref_class.__name__ in rule:
            return name
    if ref_class.__base__:
        return determine(ref_class.__base__)
    print 'Unknown parent test case'
    return None

def get_dummy_case(ref_class):
    return {
        CORE: DummyCase,
        KAMINO: KaminoDummyCase,
        GRACK: GrackDummyCase,
    }.get(determine(ref_class), DummyCase)

def get_pass_case(ref_class):
    return {
        CORE: PassCase,
        KAMINO: KaminoPassCase,
        GRACK: GrackPassCase,
    }.get(determine(ref_class), PassCase)

def get_failure_case(ref_class):
    return {
        CORE: FailureCase,
        KAMINO: KaminoFailureCase,
        GRACK: GrackFailureCase,
    }.get(determine(ref_class), FailureCase)

#
# Basic Cases
#
def main_for_dummy(self):
    self.data.reset_test_result()
    self.data.print_test_result()
    return True

def main_for_pass(self):
    self.data.reset_test_result()
    if self.pass_message:
        self.log.test_step(self.pass_message)
    self.data.print_test_result()
    return True

def main_for_failure(self):
    # Set failure result by given exception object.
    self.data.reset_test_result()
    self.data.error_callback(exception=self.input_exception)
    self.data.print_test_result()
    return False

class DummyCase(CoreTestCase):
    """ Basic dummy case. """
    TEST_SUITE = 'Dummy_Case'
    TEST_NAME = 'Dummy_Case'
    # TODO: Disable more features here if we need.
    SETTINGS = Settings(**{
        'disable_loop': True
    })

    main = main_for_dummy

class PassCase(DummyCase):
    """ A dummy case for pass test. """
    TEST_SUITE = 'Pass_Case'
    TEST_NAME = 'Pass_Case'

    def __init__(self, input_obj, pass_message=None, keeper_list=None):
        CoreTestCase.__init__(self, input_obj, keeper_list)
        self.pass_message = pass_message

    main = main_for_pass

class FailureCase(DummyCase):
    """ A dummy case for failed test. """
    TEST_SUITE = 'Failure_Case'
    TEST_NAME = 'Failure_Case'

    def __init__(self, input_obj, exception=None, keeper_list=None):
        CoreTestCase.__init__(self, input_obj, keeper_list)
        self.input_exception = exception if exception else self.err.TestFailure('Test Failed')

    main = main_for_failure

#
# For Kamino
#
class KaminoDummyCase(TestCase):
    """ Basic dummy case. """
    TEST_SUITE = 'Kamino_Dummy_Case'
    TEST_NAME = 'Kamino_Dummy_Case'

    SETTINGS = Settings(**{
        'disable_loop': True,
        'disable_firmware_consistency': True,
        'adb': False,
        'ap': False,
        'btle_client': False,
        'power_switch': False, 
        'serial_client': False,
        'uut_owner' : False
    })

    main = main_for_dummy

class KaminoPassCase(KaminoDummyCase, PassCase):
    TEST_SUITE = 'Kamino_Pass_Case'
    TEST_NAME = 'Kamino_Pass_Case'

    def __init__(self, input_obj, pass_message=None, keeper_list=None):
        TestCase.__init__(self, input_obj, keeper_list)
        self.pass_message = pass_message

    main = main_for_pass

class KaminoFailureCase(KaminoDummyCase, FailureCase):
    TEST_SUITE = 'Kamino_Failure_Case'
    TEST_NAME = 'Kamino_Failure_Case'

    def __init__(self, input_obj, exception=None, keeper_list=None):
        TestCase.__init__(self, input_obj, keeper_list)
        self.input_exception = exception if exception else self.err.TestFailure('Test Failed')

    main = main_for_failure

#
# For Grack
#
class GrackDummyCase(GrackTestCase):
    """ Basic dummy case. """
    TEST_SUITE = 'Grack_Dummy_Case'
    TEST_NAME = 'Grack_Dummy_Case'

    SETTINGS = Settings(**{
        'disable_loop': True,
        'power_switch': False, 
        'serial_client': False
    })

    main = main_for_dummy

class GrackPassCase(GrackDummyCase, PassCase):
    TEST_SUITE = 'Grack_Pass_Case'
    TEST_NAME = 'Grack_Pass_Case'

    def __init__(self, input_obj, pass_message=None, keeper_list=None):
        GrackTestCase.__init__(self, input_obj, keeper_list)
        self.pass_message = pass_message

    main = main_for_pass

class GrackFailureCase(GrackDummyCase, FailureCase):
    TEST_SUITE = 'Grack_Failure_Case'
    TEST_NAME = 'Grack_Failure_Case'

    def __init__(self, input_obj, exception=None, keeper_list=None):
        GrackTestCase.__init__(self, input_obj, keeper_list)
        self.input_exception = exception if exception else self.err.TestFailure('Test Failed')

    main = main_for_failure
