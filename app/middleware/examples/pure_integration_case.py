# -*- coding: utf-8 -*-
""" A test to run test behavior of CoreIntegrationTest.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import CoreIntegrationTestArgument
from middleware.core.integration_test import IntegrationTest
from middleware.core.test_case import TestCase
# test cases
from pure_simple_case import SimpleTest


class RaiseErrorTest(TestCase):

    TEST_SUITE = 'RaiseErrorTests'
    TEST_NAME = 'RaiseErrorTest'

    def test(self):
        raise self.err.TestError('Raise TestError!')

class RaiseFailureTest(TestCase):

    TEST_SUITE = 'RaiseErrorTests'
    TEST_NAME = 'RaiseFailureTest'

    def test(self):
        raise self.err.TestFailure('Raise TestFailure!')

class RaiseSkippedTest(TestCase):

    TEST_SUITE = 'RaiseErrorTests'
    TEST_NAME = 'RaiseSkippedTest'

    def test(self):
        raise self.err.TestSkipped('Raise RaiseSkippedTest!')

class RaiseExceptionTest(TestCase):

    TEST_SUITE = 'RaiseErrorTests'
    TEST_NAME = 'RaiseExceptionTest'

    def test(self):
        raise Exception('Raise Exception!')


class IntegrationTest(IntegrationTest):

    TEST_SUITE = 'IntegrationTests'
    TEST_NAME = 'IntegrationTest'

    def init(self):
        self.log.warning('Run init step of IntegrationTest.')
        # Integration test will run each sub-test in ordering.
        # Pass a list of test case.
        self.integration.add_testcases(testcases=[
            RaiseErrorTest, RaiseFailureTest, RaiseSkippedTest, RaiseExceptionTest, # Use self to create these test cases.
            {'testcase': SimpleTest, 'custom_env':{'loop_times': 2, 'my_var': 123}}, # Use self + custom_env to create this test case.
            (RaiseFailureTest, {'loop_times': 2}) # More simple way.
        ])
        self.integration.add_testcase(testcase=SimpleTest, custom_env={'my_var': 789})
        self.share['from_super'] = 'data'

    def before_test(self):
        self.log.warning('Run before_test step of IntegrationTest.')

    """
    def test(self): # IntegrationTest class already have one. 
        pass
    """

    def after_test(self):
        self.log.warning('Run before_loop step of IntegrationTest.')

    def before_loop(self):
        self.log.warning('Run before_test step of IntegrationTest.')

    def after_loop(self):
        self.log.warning('Run after_loop step of IntegrationTest.')


if __name__ == '__main__':
    parser = CoreIntegrationTestArgument("""\
        *** Integration Test***
        Examples: ./run.sh middleware/examples/pure_integration_case.py --uut_ip 10.136.137.159\
        """)

    test = IntegrationTest(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
