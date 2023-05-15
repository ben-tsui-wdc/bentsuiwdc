# -*- coding: utf-8 -*-
""" A test with run test behavior of template and use built-in feature.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.decorator import elapsed_time, record_result
from middleware.test_case import TestCase


class DecoratorTest(TestCase):

    TEST_SUITE = 'DecoratorTests'
    TEST_NAME = 'DecoratorTest'

    @elapsed_time(field='time_of_sub_tset_1')
    def sub_tset_1(self):
        print 'Run sub_tset_1.'

    @record_result(field='result_of_sub_tset_1')
    def sub_tset_2(self):
        print 'Run sub_tset_2.'
        return 'PASS'

    def test(self):
        print "Run test step!"
        self.sub_tset_1()
        self.sub_tset_2()
        print 'Is test time over 90s? ', self.timing.is_timeout(timeout=90)


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Decorator Test on Kamino Android ***
        Examples: ./run.sh middleware/examples/decorator_case.py --uut_ip 10.136.137.159\
        """)
    test = DecoratorTest(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)

"""
[Command]
    ./run.sh middleware/examples/decorator_case.py --uut_ip 10.136.137.159 -lsu http://10.136.127.127:8080 -debug

[Output]
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
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     TEST_SUITE=DecoratorTests TEST_NAMES=DecoratorTest
KAT.middleware                : INFO     Environment Attributes:
{'UUT_firmware_version': '4.0.0-364',
 'adb_server_ip': None,
 'adb_server_port': None,
 'cloud_env': 'dev1',
 'debug_middleware': True,
 'disable_firmware_consistency': False,
 'disable_loop': False,
 'disable_save_result': False,
 'dry_run': False,
 'firmware_version': None,
 'iteration': 0,
 'log': <logging.Logger object at 0x7fe3e4e697d0>,
 'logcat_name': 'logcat',
 'logstash_server_url': 'http://10.136.127.127:8080',
 'loop_times': None,
 'output_folder': 'output',
 'password': 'Test1234',
 'power_switch_ip': None,
 'power_switch_port': None,
 'results_folder': 'output/results',
 'testcase': <__main__.DecoratorTest object at 0x7fe3e4e69750>,
 'username': 'wdctest_owner@test.com',
 'uut_ip': '10.136.128.41',
 'uut_port': 5555}
KAT.middleware                : INFO     Test Case Attributes:
{'SETTINGS': {'adb': True,
              'disable_loop': False,
              'power_switch': True,
              'uut_owner': True},
 'adb': <platform_libraries.adblib.ADB object at 0x7fe3e4e698d0>,
 'data': <middleware.component.ResultComponent object at 0x7fe3e4e69850>,
 'env': <middleware.test_case.Environment object at 0x7fe3e4e69790>,
 'err': <module 'middleware.error' from '/root/inte/app/middleware/error.pyc'>,
 'ext': <middleware.component.ExtensionComponent object at 0x7fe3e4e69810>,
 'log': <logging.Logger object at 0x7fe3ea9fb7d0>,
 'power_switch': None,
 'timing': <middleware.component.TimingComponent object at 0x7fe3e4e69890>,
 'utils': <class 'middleware.component.UtilityGenerator'>,
 'uut_owner': <platform_libraries.restAPI.RestAPI object at 0x7fe3e4e8f350>}
KAT.middleware                : INFO     ###########################################################################
KAT.DecoratorTest             : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.DecoratorTest             : INFO     Start DecoratorTest...
KAT.middleware                : INFO     Reset Test Result.
Run test step!
Run sub_tset_1.
Run sub_tset_2.
Is test time over 90s?  False
KAT.middleware                : INFO     Test Elapsed Time: 0.000146865844727s
KAT.TestResult                : INFO     Output to json file:output/results/DecoratorTest.json.
KAT.middleware                : INFO     Save Result To output/results/DecoratorTest.json
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Test Result:
{'build': '4.0.0-364',
 'elapsed_sec': 0.0001468658447265625,
 'result_of_sub_tset_1': 'PASS',
 'testName': 'DecoratorTest',
 'testSuite': 'DecoratorTests',
 'time_of_sub_tset_1': 1.811981201171875e-05}
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Update Result To Logstash: http://10.136.127.127:8080
KAT.TestResult                : INFO     Uploaded data to logstash server: http://10.136.127.127:8080
KAT.DecoratorTest             : INFO     DecoratorTest Is Done.
KAT.DecoratorTest             : INFO     <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
KAT.adblib                    : INFO     Save logcat information to output/logcat
"""
