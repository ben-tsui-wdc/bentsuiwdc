# -*- coding: utf-8 -*-
""" A test with run test behavior of template.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class SimpleTest(TestCase):

    TEST_SUITE = 'SimpleTests'
    TEST_NAME = 'SimpleTest'

    def init(self):
        self.some_var = 'some_var'
        self.log.warning('Run init step.')

    def before_test(self):
        self.log.warning('Run before_test step.')

    def test(self):
        self.log.warning("Run test step! I have {0} and {1}".format(self.some_var, self.my_var))

    def after_test(self):
        self.log.warning('Run after_test step.')

    def before_loop(self):
        self.log.warning('Run before_loop step.')

    def after_loop(self):
        self.log.warning('Run after_loop step.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Simple Test on Kamino Android ***
        Examples: ./run.sh middleware/examples/simple_case.py --uut_ip 10.136.137.159\
        """)
    # Test Arguments
    parser.add_argument('-mv', '--my_var', help='An additional variable.', type=int, default=1000)

    test = SimpleTest(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)

"""
[Command]
    ./run.sh middleware/examples/simple_case.py --uut_ip 10.136.137.159 -lsu http://10.136.127.127:8080 -debug --my_var 123

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
KAT.restAPI                   : INFO     Use existed ID token, it will be expired in 1799 seconds
KAT.restAPI                   : INFO     Get local code and security code successfully
KAT.restAPI                   : INFO     User: wdctest_owner@test.com is attached to device successfully
KAT.adblib                    : INFO     Executing commmand: adb connect 10.136.128.41:5555
KAT.adblib                    : INFO     stdout: already connected to 10.136.128.41:5555

KAT.adblib                    : INFO     Test ADB connect with whoami...
KAT.adblib                    : INFO     ADB Connect works.
KAT.adblib                    : INFO     Connect as root user.
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     TEST_SUITE=SimpleTests TEST_NAMES=SimpleTest
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
 'log': <logging.Logger object at 0x7f13fe3b9a90>,
 'logcat_name': 'logcat',
 'logstash_server_url': 'http://10.136.127.127:8080',
 'loop_times': None,
 'output_folder': 'output',
 'password': 'Test1234',
 'power_switch_ip': None,
 'power_switch_port': None,
 'results_folder': 'output/results',
 'testcase': <__main__.SimpleTest object at 0x7f13fe3b9a10>,
 'username': 'wdctest_owner@test.com',
 'uut_ip': '10.136.128.41',
 'uut_port': 5555}
KAT.middleware                : INFO     Test Case Attributes:
{'SETTINGS': {'adb': True,
              'disable_loop': False,
              'power_switch': True,
              'uut_owner': True},
 'adb': <platform_libraries.adblib.ADB object at 0x7f13fe3b9b90>,
 'data': <middleware.component.ResultComponent object at 0x7f13fe3b9b10>,
 'env': <middleware.test_case.Environment object at 0x7f13fe3b9a50>,
 'err': <module 'middleware.error' from '/root/inte/app/middleware/error.pyc'>,
 'ext': <middleware.component.ExtensionComponent object at 0x7f13fe3b9ad0>,
 'log': <logging.Logger object at 0x7f1403f4a7d0>,
 'my_var': 123,
 'power_switch': None,
 'timing': <middleware.component.TimingComponent object at 0x7f13fe3b9b50>,
 'utils': <class 'middleware.component.UtilityGenerator'>,
 'uut_owner': <platform_libraries.restAPI.RestAPI object at 0x7f13fe3ddb50>}
KAT.middleware                : INFO     ###########################################################################
Run init step.
KAT.SimpleTest                : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.SimpleTest                : INFO     Start SimpleTest...
KAT.middleware                : INFO     Reset Test Result.
Run before_test step.
Run test step! I have some_var and 123
KAT.middleware                : INFO     Test Elapsed Time: 2.00271606445e-05s
Run after_test step.
KAT.TestResult                : INFO     Output to json file:output/results/SimpleTest.json.
KAT.middleware                : INFO     Save Result To output/results/SimpleTest.json
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Test Result:
{'build': '4.0.0-364',
 'elapsed_sec': 2.002716064453125e-05,
 'testName': 'SimpleTest',
 'testSuite': 'SimpleTests'}
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Update Result To Logstash: http://10.136.127.127:8080
KAT.TestResult                : INFO     Uploaded data to logstash server: http://10.136.127.127:8080
KAT.SimpleTest                : INFO     SimpleTest Is Done.
KAT.SimpleTest                : INFO     <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
KAT.adblib                    : INFO     Save logcat information to output/logcat
test response: True
"""

"""
[Command]
    ./run.sh middleware/examples/simple_case.py --uut_ip 10.136.137.159 -lsu http://10.136.127.127:8080 -debug --my_var 123 -lt 2

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
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     TEST_SUITE=SimpleTests TEST_NAMES=SimpleTest
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
 'log': <logging.Logger object at 0x7f46b3bb6a90>,
 'logcat_name': 'logcat',
 'logstash_server_url': 'http://10.136.127.127:8080',
 'loop_times': 2,
 'output_folder': 'output',
 'password': 'Test1234',
 'power_switch_ip': None,
 'power_switch_port': None,
 'results_folder': 'output/results',
 'testcase': <__main__.SimpleTest object at 0x7f46b3bb6a10>,
 'username': 'wdctest_owner@test.com',
 'uut_ip': '10.136.128.41',
 'uut_port': 5555}
KAT.middleware                : INFO     Test Case Attributes:
{'SETTINGS': {'adb': True,
              'disable_loop': False,
              'power_switch': True,
              'uut_owner': True},
 'adb': <platform_libraries.adblib.ADB object at 0x7f46b3bb6b90>,
 'data': <middleware.component.ResultComponent object at 0x7f46b3bb6b10>,
 'env': <middleware.test_case.Environment object at 0x7f46b3bb6a50>,
 'err': <module 'middleware.error' from '/root/inte/app/middleware/error.pyc'>,
 'ext': <middleware.component.ExtensionComponent object at 0x7f46b3bb6ad0>,
 'log': <logging.Logger object at 0x7f46b97477d0>,
 'my_var': 123,
 'power_switch': None,
 'timing': <middleware.component.TimingComponent object at 0x7f46b3bb6b50>,
 'utils': <class 'middleware.component.UtilityGenerator'>,
 'uut_owner': <platform_libraries.restAPI.RestAPI object at 0x7f46b3bdab50>}
KAT.middleware                : INFO     ###########################################################################
Run init step.
KAT.SimpleTest                : INFO     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
KAT.middleware                : INFO     Reset Test Loop Results.
Run before_loop step.
KAT.SimpleTest                : INFO     Start SimpleTest Iteration #1...
KAT.middleware                : INFO     Reset Test Result.
Run before_test step.
Run test step! I have some_var and 123
KAT.middleware                : INFO     Test Elapsed Time: 1.21593475342e-05s
Run after_test step.
KAT.TestResult                : INFO     Output to json file:output/results/SimpleTest#1.json.
KAT.middleware                : INFO     Save Result To output/results/SimpleTest#1.json
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Test Result:
{'build': '4.0.0-364',
 'elapsed_sec': 1.2159347534179688e-05,
 'iteration': '4.0.0-364_itr_01',
 'testName': 'SimpleTest',
 'testSuite': 'SimpleTests'}
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Update Result To Logstash: http://10.136.127.127:8080
KAT.TestResult                : INFO     Uploaded data to logstash server: http://10.136.127.127:8080
KAT.SimpleTest                : INFO     SimpleTest Iteration #1 Is Done.
KAT.middleware                : INFO     Append Test #1 To Loop Results.
KAT.SimpleTest                : INFO     Start SimpleTest Iteration #2...
KAT.middleware                : INFO     Reset Test Result.
Run before_test step.
Run test step! I have some_var and 123
KAT.middleware                : INFO     Test Elapsed Time: 6.91413879395e-06s
Run after_test step.
KAT.TestResult                : INFO     Output to json file:output/results/SimpleTest#2.json.
KAT.middleware                : INFO     Save Result To output/results/SimpleTest#2.json
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Test Result:
{'build': '4.0.0-364',
 'elapsed_sec': 6.9141387939453125e-06,
 'iteration': '4.0.0-364_itr_02',
 'testName': 'SimpleTest',
 'testSuite': 'SimpleTests'}
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Update Result To Logstash: http://10.136.127.127:8080
KAT.TestResult                : INFO     Uploaded data to logstash server: http://10.136.127.127:8080
KAT.SimpleTest                : INFO     SimpleTest Iteration #2 Is Done.
KAT.middleware                : INFO     Append Test #2 To Loop Results.
KAT.middleware                : INFO     Save Loop Results To output/results/test_report.xml
Run after_loop step.
KAT.SimpleTest                : INFO     SimpleTest Is Done.
KAT.SimpleTest                : INFO     <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
KAT.adblib                    : INFO     Save logcat information to output/logcat
test response: True
"""