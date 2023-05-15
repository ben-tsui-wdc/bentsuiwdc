# -*- coding: utf-8 -*-
""" A test without run test behavior of template but use built-in feature.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.decorator import elapsed_time, exit_test, record_result
from middleware.test_case import TestCase


class NakedV2Test(TestCase):

    TEST_SUITE = 'NakedV2Tests'
    TEST_NAME = 'NakedV2Test'

    @elapsed_time(field='time_of_sub_tset_1')
    def sub_tset_1(self):
        print 'Run sub_tset_1.'

    @record_result(field='result_of_sub_tset_1')
    def sub_tset_2(self):
        print 'Run sub_tset_2.'
        return 'PASS'

    @exit_test
    def my_way_test(self):
        self.data.reset_test_result() # Use self.data Component.
        print 'Test result:', self.data.test_result
        self.timing.reset_start_time()  # Use self.timing Component.
        print 'Set test start time:', self.timing.start_time
        # Start Test
        print "Just run test my way! I have {0}!".format(self.my_var)
        self.sub_tset_1()
        self.sub_tset_2()
        print 'Is test time over 90s? ', self.timing.is_timeout(timeout=90)
        # Update result by self.data Component.
        self.data.upload_test_result()


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Naked V2 Test on Kamino Android ***
        Examples: ./run.sh middleware/examples/naked_v2_case --uut_ip 10.136.137.159\
        """)
    # Test Arguments
    parser.add_argument('-mv', '--my_var', help='An additional variable.', type=int, default=1000)

    test = NakedV2Test(parser)
    resp = test.my_way_test()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)

"""
[Command]
    ./run.sh middleware/examples/naked_v2_case.py --uut_ip 10.136.137.159 -lsu http://10.136.127.127:8080 -debug

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
 'log': <logging.Logger object at 0x7f9e3cd1ef50>,
 'logcat_name': 'logcat',
 'logstash_server_url': 'http://10.136.127.127:8080',
 'loop_times': None,
 'output_folder': 'output',
 'password': 'Test1234',
 'power_switch_ip': None,
 'power_switch_port': None,
 'results_folder': 'output/results',
 'testcase': <__main__.NakedV2Test object at 0x7f9e3949a290>,
 'username': 'wdctest_owner@test.com',
 'uut_ip': '10.136.137.159',
 'uut_port': 5555}
KAT.middleware                : INFO     Test Case Attributes: {'adb': <platform_libraries.adblib.ADB object at 0x7f9e3949a3d0>,
 'data': <middleware.component.ResultComponent object at 0x7f9e3949a350>,
 'env': <middleware.test_case.Environment object at 0x7f9e3949a2d0>,
 'ext': <middleware.component.ExtensionComponent object at 0x7f9e3949a310>,
 'log': <logging.Logger object at 0x7f9e3950e210>,
 'my_var': 1000,
 'power_switch': None,
 'timing': <middleware.component.TimingComponent object at 0x7f9e3949a390>,
 'utils': <class 'middleware.component.UtilityGenerator'>,
 'uut_owner': <platform_libraries.restAPI.RestAPI object at 0x7f9e3949ad90>}
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Reset Test Result.
Test result: {'testSuite': 'NakedV2Tests', 'build': '4.0.0-314', 'testName': 'NakedV2Test'}
Set test start time: 1489463118.35
Just run test my way! I have 1000!
Run sub_tset_1.
Run sub_tset_2.
Is test time over 90s?  False
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Test Result: {'build': '4.0.0-314',
 'result_of_sub_tset_1': 'PASS',
 'testName': 'NakedV2Test',
 'testSuite': 'NakedV2Tests',
 'time_of_sub_tset_1': 3.0994415283203125e-05}
KAT.middleware                : INFO     ###########################################################################
KAT.TestResult                : INFO     Uploaded data to logstash server: http://10.136.127.127:8080
KAT.adblib                    : INFO     Save logcat information to output/logcat
test response: None
"""
