# -*- coding: utf-8 -*-
""" A test to run test behavior of Grack IntegrationTest.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GrackIntegrationTestArgument
from middleware.grack_integration_test import GrackIntegrationTest
from middleware.grack_test_case import GrackTestCase

# test cases
from decorator_case import DecoratorTest
from grack_simple_case import GrackSimpleTest


class RaiseErrorTest(GrackTestCase):

    TEST_SUITE = 'RaiseErrorTests'
    TEST_NAME = 'RaiseErrorTest'

    def test(self):
        raise self.err.TestError('Raise TestError!')

class RaiseFailureTest(GrackTestCase):

    TEST_SUITE = 'RaiseErrorTests'
    TEST_NAME = 'RaiseFailureTest'

    def test(self):
        raise self.err.TestFailure('Raise TestFailure!')

class RaiseSkippedTest(GrackTestCase):

    TEST_SUITE = 'RaiseErrorTests'
    TEST_NAME = 'RaiseSkippedTest'

    def test(self):
        raise self.err.TestSkipped('Raise RaiseSkippedTest!')

class RaiseExceptionTest(GrackTestCase):

    TEST_SUITE = 'RaiseErrorTests'
    TEST_NAME = 'RaiseExceptionTest'

    def test(self):
        raise Exception('Raise Exception!')


class GrackSampleIntegrationTest(GrackIntegrationTest):

    TEST_SUITE = 'IntegrationTests'
    TEST_NAME = 'IntegrationTest'

    def init(self):
        print 'Run init step.'
        # Integration test will run each sub-test in ordering.
        # Pass a list of test case.
        self.integration.add_testcases(testcases=[
            RaiseErrorTest, RaiseFailureTest, RaiseSkippedTest, RaiseExceptionTest, # Use self to create these test cases.
            {'testcase': GrackSimpleTest, 'custom_env':{'loop_times': 2, 'my_var': 123}}, # Use self + custom_env to create this test case.
            (RaiseFailureTest, {'loop_times': 2}) # More simple way.
        ])
        self.integration.add_testcase(testcase=GrackSimpleTest, custom_env={'my_var': 789})
        #self.integration.add_testcase(testcase=DecoratorTest)
        self.share['from_super'] = 'data'

    def before_test(self):
        print 'Run before_test step.'

    """
    def test(self): # IntegrationTest class already have one. 
        pass
    """

    def after_test(self):
        print 'Run after_test step.'

    def before_loop(self):
        print 'Run before_loop step.'

    def after_loop(self):
        print 'Run after_loop step.'


if __name__ == '__main__':
    parser = GrackIntegrationTestArgument("""\
        *** Integration Test on Grack Android ***
        Examples: ./run.sh middleware/examples/grack_integration_case.py --uut_ip 10.136.137.159\
        """)

    test = GrackSampleIntegrationTest(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
