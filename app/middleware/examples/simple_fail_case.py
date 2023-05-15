# -*- coding: utf-8 -*-
""" A test with run test behavior of template in fail case.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class SimpleFaileTest(TestCase):

    TEST_SUITE = 'SimpleFaileTests'
    TEST_NAME = 'SimpleFaileTest'

    def init(self):
        self.some_var = 'some_var'
        print 'Run init step.'

    def before_test(self):
        print 'Run before_test step.'

    def test(self):
        print "Run test step! I have {0} and {1}".format(self.some_var, self.my_var)
        self.adb.disconnect() # Cause to logcat fail.
        raise RuntimeError('Test is Failed!')

    def after_test(self):
        print 'Run after_test step.'

    def before_loop(self):
        print 'Run before_loop step.'

    def after_loop(self):
        print 'Run after_loop step.'


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Simple Fail Test on Kamino Android ***
        Examples: ./run.sh middleware/examples/simple_fail_case.py --uut_ip 10.136.137.159\
        """)
    # Test Arguments
    parser.add_argument('-mv', '--my_var', help='An additional variable.', type=int, default=1000)

    test = SimpleFaileTest(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)

"""
[Command]
    ./run.sh middleware/examples/simple_fail_case.py --uut_ip 10.136.137.159 -lsu http://10.136.127.127:8080 -debug --my_var 123

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
KAT.restAPI                   : INFO     User was already attached to device: wdctest_owner@test.com
KAT.adblib                    : INFO     Executing commmand: adb connect 10.136.137.159:5555
KAT.adblib                    : INFO     stdout: already connected to 10.136.137.159:5555

KAT.adblib                    : INFO     Test ADB connect with whoami...
KAT.adblib                    : INFO     ADB Connect works.
KAT.adblib                    : INFO     Connect as root user.
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Environment Attributes: {'UUT_firmware_version': '4.0.0-314',
 'adb_server_ip': None,
 'adb_server_port': None,
 'debug_middleware': True,
 'disable_firmware_consistency': False,
 'disable_loop': False,
 'disable_save_result': False,
 'dry_run': False,
 'firmware_version': None,
 'iteration': 0,
 'log': <logging.Logger object at 0x7f07195edc90>,
 'logcat_name': 'logcat',
 'logstash_server_url': 'http://10.136.127.127:8080',
 'loop_times': None,
 'output_folder': 'output',
 'password': 'Test1234',
 'power_switch_ip': None,
 'power_switch_port': None,
 'results_folder': 'output/results',
 'testcase': <__main__.SimpleFaileTest object at 0x7f0715d6a390>,
 'username': 'wdctest_owner@test.com',
 'uut_ip': '10.136.137.159',
 'uut_port': 5555}
KAT.middleware                : INFO     Test Case Attributes: {'adb': <platform_libraries.adblib.ADB object at 0x7f0715d6a4d0>,
 'data': <middleware.component.ResultComponent object at 0x7f0715d6a450>,
 'env': <middleware.test_case.Environment object at 0x7f0715d6a3d0>,
 'ext': <middleware.component.ExtensionComponent object at 0x7f0715d6a410>,
 'log': <logging.Logger object at 0x7f0715ddd350>,
 'my_var': 123,
 'power_switch': None,
 'timing': <middleware.component.TimingComponent object at 0x7f0715d6a490>,
 'utils': <class 'middleware.component.UtilityGenerator'>,
 'uut_owner': <platform_libraries.restAPI.RestAPI object at 0x7f0715d6aed0>}
KAT.middleware                : INFO     ###########################################################################
Run init step.
KAT.SimpleFaileTest           : INFO     Start Test...
KAT.middleware                : INFO     Reset Test Result.
Run before_test step.
Run test step! I have some_var and 123
KAT.adblib                    : INFO     Executing commmand: adb disconnect 10.136.137.159:5555
KAT.adblib                    : INFO     stdout:

KAT.adblib                    : INFO     Device disconnected
KAT.middleware                : ERROR    Catch An Exception During Testing.
Traceback (most recent call last):
  File "/root/m/app/middleware/decorator.py", line 46, in wrapper
    return method(self, *args, **kwargs)
  File "/root/m/app/middleware/test_case.py", line 46, in run_test
    test_result = self._run_test()
  File "/root/m/app/middleware/test_case.py", line 57, in _run_test
    self.test()
  File "/root/m/app/middleware/examples/simple_fail_case.py", line 28, in test
    raise RuntimeError('Test is Failed!')
RuntimeError: Test is Failed!
KAT.middleware                : WARNING  Unable to save logcat log because of ADB is disconnected.
test response: False
"""