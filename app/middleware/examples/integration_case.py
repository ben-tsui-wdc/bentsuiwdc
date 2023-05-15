# -*- coding: utf-8 -*-
""" A test to run test behavior of IntegrationTest.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
from middleware.test_case import TestCase
# test cases
from decorator_case import DecoratorTest
from simple_case import SimpleTest


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
        self.integration.add_testcase(testcase=DecoratorTest)
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
    parser = IntegrationTestArgument("""\
        *** Integration Test on Kamino Android ***
        Examples: ./run.sh middleware/examples/integration_case.py --uut_ip 10.136.137.159\
        """)

    test = IntegrationTest(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)

"""
[Command]
    ./run.sh middleware/examples/integration_case.py --uut_ip 10.136.128.41 -dr

[Output]

KAT.restAPI                   : INFO     Creating user:wdctest_owner@test.com
KAT.restAPI                   : INFO     User: wdctest_owner@test.com is already exist
KAT.restAPI                   : INFO     Attaching user to device
KAT.restAPI                   : INFO     Getting ID token of user: wdctest_owner@test.com
KAT.restAPI                   : INFO     ID token not exist, trying to get a new token
KAT.restAPI                   : INFO     Get new ID token complete
KAT.restAPI                   : INFO     Getting User ID
KAT.restAPI                   : INFO     User ID: auth0|58c285533d778f6e3000070b
KAT.restAPI                   : INFO     Getting local code and security code
KAT.restAPI                   : INFO     Getting ID token of user: wdctest_owner@test.com
KAT.restAPI                   : INFO     Use existed ID token, it will be expired in 1800 seconds
KAT.restAPI                   : INFO     Get local code and security code successfully
KAT.restAPI                   : INFO     User: wdctest_owner@test.com is attached to device successfully
KAT.adblib                    : INFO     Executing commmand: adb connect 10.136.128.41:5555
KAT.adblib                    : INFO     stdout: already connected to 10.136.128.41:5555

KAT.adblib                    : INFO     Test ADB connect with whoami...
KAT.adblib                    : INFO     ADB Connect works.
KAT.adblib                    : INFO     Connect as root user.
Run init step.
KAT.IntegrationTest           : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.IntegrationTest           : INFO     Start IntegrationTest...
Run init step.
Run init step.
KAT.middleware                : INFO     Reset Test Result.
Run before_test step.
KAT.middleware                : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.middleware                : INFO     Start RaiseErrorTest...
KAT.middleware                : INFO     Reset Test Result.
KAT.middleware                : INFO     Test Elapsed Time: 2.8133392334e-05s
KAT.middleware                : ERROR    Catch An Exception During Testing.
Traceback (most recent call last):
  File "/root/inte/app/middleware/decorator.py", line 90, in wrapper
    return method(self, *args, **kwargs)
  File "/root/inte/app/middleware/decorator.py", line 68, in wrapper
    return test_method(self, *args, **kwargs)
  File "/root/inte/app/middleware/test_case.py", line 49, in run_test
    test_result = self._run_test()
  File "/root/inte/app/middleware/test_case.py", line 62, in _run_test
    self.test()
  File "app/middleware/examples/integration_case.py", line 23, in test
    raise self.err.TestError('Raise TestError!')
TestError: Raise TestError!
KAT.adblib                    : INFO     Save logcat information to output/IntegrationTests-1-RaiseErrorTest-logcat
KAT.middleware                : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.middleware                : INFO     Start RaiseFailureTest...
KAT.middleware                : INFO     Reset Test Result.
KAT.middleware                : INFO     Test Elapsed Time: 1.50203704834e-05s
KAT.middleware                : ERROR    Catch An Exception During Testing.
Traceback (most recent call last):
  File "/root/inte/app/middleware/decorator.py", line 90, in wrapper
    return method(self, *args, **kwargs)
  File "/root/inte/app/middleware/decorator.py", line 68, in wrapper
    return test_method(self, *args, **kwargs)
  File "/root/inte/app/middleware/test_case.py", line 49, in run_test
    test_result = self._run_test()
  File "/root/inte/app/middleware/test_case.py", line 62, in _run_test
    self.test()
  File "app/middleware/examples/integration_case.py", line 31, in test
    raise self.err.TestFailure('Raise TestFailure!')
TestFailure: Raise TestFailure!
KAT.adblib                    : INFO     Save logcat information to output/IntegrationTests-2-RaiseFailureTest-logcat
KAT.middleware                : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.middleware                : INFO     Start RaiseSkippedTest...
KAT.middleware                : INFO     Reset Test Result.
KAT.middleware                : INFO     Test Elapsed Time: 1.19209289551e-05s
KAT.middleware                : ERROR    Catch An Exception During Testing.
Traceback (most recent call last):
  File "/root/inte/app/middleware/decorator.py", line 90, in wrapper
    return method(self, *args, **kwargs)
  File "/root/inte/app/middleware/decorator.py", line 68, in wrapper
    return test_method(self, *args, **kwargs)
  File "/root/inte/app/middleware/test_case.py", line 49, in run_test
    test_result = self._run_test()
  File "/root/inte/app/middleware/test_case.py", line 62, in _run_test
    self.test()
  File "app/middleware/examples/integration_case.py", line 39, in test
    raise self.err.TestSkipped('Raise RaiseSkippedTest!')
TestSkipped: Raise RaiseSkippedTest!
KAT.adblib                    : INFO     Save logcat information to output/IntegrationTests-3-RaiseSkippedTest-logcat
KAT.middleware                : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.middleware                : INFO     Start RaiseExceptionTest...
KAT.middleware                : INFO     Reset Test Result.
KAT.middleware                : INFO     Test Elapsed Time: 1.28746032715e-05s
KAT.middleware                : ERROR    Catch An Exception During Testing.
Traceback (most recent call last):
  File "/root/inte/app/middleware/decorator.py", line 90, in wrapper
    return method(self, *args, **kwargs)
  File "/root/inte/app/middleware/decorator.py", line 68, in wrapper
    return test_method(self, *args, **kwargs)
  File "/root/inte/app/middleware/test_case.py", line 49, in run_test
    test_result = self._run_test()
  File "/root/inte/app/middleware/test_case.py", line 62, in _run_test
    self.test()
  File "app/middleware/examples/integration_case.py", line 47, in test
    raise Exception('Raise Exception!')
Exception: Raise Exception!
KAT.adblib                    : INFO     Save logcat information to output/IntegrationTests-4-RaiseExceptionTest-logcat
KAT.middleware                : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.middleware                : INFO     Reset Test Loop Results.
Run before_loop step.
KAT.middleware                : INFO     Start SimpleTest Iteration #1...
KAT.middleware                : INFO     Reset Test Result.
Run before_test step.
Run test step! I have some_var and 123
KAT.middleware                : INFO     Test Elapsed Time: 4.81605529785e-05s
Run after_test step.
KAT.TestResult                : INFO     Output to json file:output/results/IntegrationTests-5-SimpleTest#1.json.
KAT.middleware                : INFO     Save Result To output/results/IntegrationTests-5-SimpleTest#1.json
KAT.middleware                : INFO     SimpleTest Iteration #1 Is Done.
KAT.middleware                : INFO     Append Test #1 To Loop Results.
KAT.middleware                : INFO     Start SimpleTest Iteration #2...
KAT.middleware                : INFO     Reset Test Result.
Run before_test step.
Run test step! I have some_var and 123
KAT.middleware                : INFO     Test Elapsed Time: 7.29560852051e-05s
Run after_test step.
KAT.TestResult                : INFO     Output to json file:output/results/IntegrationTests-5-SimpleTest#2.json.
KAT.middleware                : INFO     Save Result To output/results/IntegrationTests-5-SimpleTest#2.json
KAT.middleware                : INFO     SimpleTest Iteration #2 Is Done.
KAT.middleware                : INFO     Append Test #2 To Loop Results.
KAT.middleware                : INFO     Save Loop Results To output/results/test_report.xml
Run after_loop step.
KAT.middleware                : INFO     SimpleTest Is Done.
KAT.middleware                : INFO     <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
KAT.adblib                    : INFO     Save logcat information to output/IntegrationTests-5-SimpleTest-logcat
KAT.middleware                : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.middleware                : INFO     Reset Test Loop Results.
KAT.middleware                : INFO     Start RaiseFailureTest Iteration #1...
KAT.middleware                : INFO     Reset Test Result.
KAT.middleware                : INFO     Test Elapsed Time: 1.19209289551e-05s
KAT.middleware                : INFO     Append Test #1 To Loop Results.
KAT.middleware                : ERROR    Catch An Exception During Testing.
Traceback (most recent call last):
  File "/root/inte/app/middleware/decorator.py", line 90, in wrapper
    return method(self, *args, **kwargs)
  File "/root/inte/app/middleware/decorator.py", line 68, in wrapper
    return test_method(self, *args, **kwargs)
  File "/root/inte/app/middleware/test_case.py", line 80, in run_loop_test
    self._run_test()
  File "/root/inte/app/middleware/test_case.py", line 62, in _run_test
    self.test()
  File "app/middleware/examples/integration_case.py", line 31, in test
    raise self.err.TestFailure('Raise TestFailure!')
TestFailure: Raise TestFailure!
KAT.adblib                    : INFO     Save logcat information to output/IntegrationTests-6-RaiseFailureTest-logcat
KAT.middleware                : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.middleware                : INFO     Start SimpleTest...
KAT.middleware                : INFO     Reset Test Result.
Run before_test step.
Run test step! I have some_var and 789
KAT.middleware                : INFO     Test Elapsed Time: 1.59740447998e-05s
Run after_test step.
KAT.TestResult                : INFO     Output to json file:output/results/IntegrationTests-7-SimpleTest.json.
KAT.middleware                : INFO     Save Result To output/results/IntegrationTests-7-SimpleTest.json
KAT.middleware                : INFO     SimpleTest Is Done.
KAT.middleware                : INFO     <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
KAT.adblib                    : INFO     Save logcat information to output/IntegrationTests-7-SimpleTest-logcat
KAT.middleware                : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.middleware                : INFO     Start DecoratorTest...
KAT.middleware                : INFO     Reset Test Result.
Run test step!
Run sub_tset_1.
Run sub_tset_2.
Is test time over 90s?  False
KAT.middleware                : INFO     Test Elapsed Time: 0.000470161437988s
KAT.TestResult                : INFO     Output to json file:output/results/IntegrationTests-8-DecoratorTest.json.
KAT.middleware                : INFO     Save Result To output/results/IntegrationTests-8-DecoratorTest.json
KAT.middleware                : INFO     DecoratorTest Is Done.
KAT.middleware                : INFO     <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
KAT.adblib                    : INFO     Save logcat information to output/IntegrationTests-8-DecoratorTest-logcat
Run after_test step.
KAT.middleware                : INFO     Save Result To output/results/IntegrationTests.xml
KAT.IntegrationTest           : INFO     IntegrationTest Is Done.
KAT.IntegrationTest           : INFO     <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
KAT.adblib                    : INFO     Save logcat information to output/logcat

"""