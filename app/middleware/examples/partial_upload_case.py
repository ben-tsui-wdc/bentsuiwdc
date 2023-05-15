# -*- coding: utf-8 -*-
""" A test with run test behavior of template.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class PartialUploadCase(TestCase):

    TEST_SUITE = 'PartialUploadCases'
    TEST_NAME = 'PartialUploadCase'
    SETTINGS = { # Disable all utilities.
        'disable_firmware_consistency': True,
        'adb': False, # Disbale ADB and ignore any relevant input argument.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def before_loop(self):
        self.total_pass = 0
        self.need_reset = False

    def before_test(self):
        if self.need_reset: # Reset after uploaded results.
            print 'Reset self.total_pass.'
            self.total_pass = 0
            self.need_reset = False

    def test(self):
        self.total_pass += 1
        print "Run test step! self.total_pass: {}".format(self.total_pass)

    def upload_result(self):
        if self.env.iteration % 10 == 0: # Upload results every 10 times.
            self.need_reset = True
            self.data.test_result['pass'] = self.total_pass
            self.data.upload_test_result()


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Partial Upload Case on Kamino Android ***
        Examples: ./run.sh middleware/examples/partial_upload_case.py --uut_ip 10.136.137.159\
        """)
    test = PartialUploadCase(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)

"""
[Command]
    ./run.sh middleware/examples/partial_upload_case.py --uut_ip 10.136.137.159 -lsu http://10.136.127.127:8080 -debug -lt 100 --disable_firmware_consistency -fw 4.0.0-314

[Output]
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Environment Attributes: {'SETTINGS': {'adb': False,
              'disable_loop': False,
              'power_switch': True,
              'uut_owner': False},
 'UUT_firmware_version': '4.0.0-314',
 'adb_server_ip': None,
 'adb_server_port': None,
 'debug_middleware': True,
 'disable_firmware_consistency': True,
 'disable_loop': False,
 'disable_save_result': False,
 'dry_run': False,
 'firmware_version': '4.0.0-314',
 'iteration': 0,
 'log': <logging.Logger object at 0x7f41cb86dfd0>,
 'logcat_name': 'logcat',
 'logstash_server_url': 'http://10.136.127.127:8080',
 'loop_times': 1,
 'output_folder': 'output',
 'password': 'Test1234',
 'power_switch_ip': '10.136.139.14',
 'power_switch_port': None,
 'results_folder': 'output/results',
 'testcase': <__main__.PartialUploadCase object at 0x7f41cb8090d0>,
 'username': 'wdctest_owner@test.com',
 'uut_ip': '10.136.137.159',
 'uut_port': 5555}
KAT.middleware                : INFO     Test Case Attributes: {'adb': False,
 'cloud_env': 'dev1',
 'data': <middleware.component.ResultComponent object at 0x7f41cb809190>,
 'env': <middleware.test_case.Environment object at 0x7f41cb809110>,
 'ext': <middleware.component.ExtensionComponent object at 0x7f41cb809150>,
 'log': <logging.Logger object at 0x7f41cb8098d0>,
 'power_switch': <platform_libraries.powerswitchclient.PowerSwitchClient object at 0x7f41cb809210>,
 'timing': <middleware.component.TimingComponent object at 0x7f41cb8091d0>,
 'utils': <class 'middleware.component.UtilityGenerator'>,
 'uut_owner': False}
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Reset Test Loop Results.
KAT.PartialUploadCase         : INFO     Start Test Iteration #1...
KAT.middleware                : INFO     Reset Test Result.
Run test step! self.total_pass: 1
KAT.middleware                : INFO     Test Elapsed Time: 2.90870666504e-05s
KAT.TestResult                : INFO     Output to json file:output/results/PartialUploadCase#1.json.
KAT.middleware                : INFO     Save Result To output/results/PartialUploadCase#1.json
KAT.PartialUploadCase         : INFO     Test Iteration #1 Is Done.
KAT.middleware                : INFO     Append Test #1 To Loop Results.
KAT.middleware                : INFO     Save Loop Results To output/results/test_report.xml
KAT.PartialUploadCase         : INFO     Test Is Done.
KAT.middleware                : WARNING  Unable to save logcat log because of ADB is disabled.
root@dc1ac4d28efa:~/app/output# rm -r  ~/m/app/middleware/
root@dc1ac4d28efa:~/app/output# ~/m/app/run.sh ~/m/app/middleware/examples/partial_upload_case.py --uut_ip 10.136.137.159 -lsu http://10.136.127.127:8080 -debug -lt 1 --disable_firmware_consistency -fw 4.0.0-314
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Environment Attributes: {'SETTINGS': {'adb': False,
              'disable_loop': False,
              'power_switch': False,
              'uut_owner': False},
 'UUT_firmware_version': '4.0.0-314',
 'adb_server_ip': None,
 'adb_server_port': None,
 'debug_middleware': True,
 'disable_firmware_consistency': True,
 'disable_loop': False,
 'disable_save_result': False,
 'dry_run': False,
 'firmware_version': '4.0.0-314',
 'iteration': 0,
 'log': <logging.Logger object at 0x7f83a11d0fd0>,
 'logcat_name': 'logcat',
 'logstash_server_url': 'http://10.136.127.127:8080',
 'loop_times': 1,
 'output_folder': 'output',
 'password': 'Test1234',
 'power_switch_ip': None,
 'power_switch_port': None,
 'results_folder': 'output/results',
 'testcase': <__main__.PartialUploadCase object at 0x7f83a116c0d0>,
 'username': 'wdctest_owner@test.com',
 'uut_ip': '10.136.137.159',
 'uut_port': 5555}
KAT.middleware                : INFO     Test Case Attributes: {'adb': None,
 'cloud_env': 'dev1',
 'data': <middleware.component.ResultComponent object at 0x7f83a116c190>,
 'env': <middleware.test_case.Environment object at 0x7f83a116c110>,
 'ext': <middleware.component.ExtensionComponent object at 0x7f83a116c150>,
 'log': <logging.Logger object at 0x7f83a116c210>,
 'power_switch': None,
 'timing': <middleware.component.TimingComponent object at 0x7f83a116c1d0>,
 'utils': <class 'middleware.component.UtilityGenerator'>,
 'uut_owner': None}
KAT.middleware                : INFO     ###########################################################################

...... 

KAT.middleware                : INFO     ###########################################################################
KAT.TestResult                : INFO     Uploaded data to logstash server: http://10.136.127.127:8080
KAT.PartialUploadCase         : INFO     Test Iteration #90 Is Done.
KAT.middleware                : INFO     Append Test #90 To Loop Results.
KAT.PartialUploadCase         : INFO     Start Test Iteration #91...
KAT.middleware                : INFO     Reset Test Result.
Reset self.total_pass.
Run test step! self.total_pass: 1
KAT.middleware                : INFO     Test Elapsed Time: 9.05990600586e-06s
KAT.TestResult                : INFO     Output to json file:output/results/PartialUploadCase#91.json.
KAT.middleware                : INFO     Save Result To output/results/PartialUploadCase#91.json
KAT.PartialUploadCase         : INFO     Test Iteration #91 Is Done.
KAT.middleware                : INFO     Append Test #91 To Loop Results.
KAT.PartialUploadCase         : INFO     Start Test Iteration #92...
KAT.middleware                : INFO     Reset Test Result.
Run test step! self.total_pass: 2
KAT.middleware                : INFO     Test Elapsed Time: 3.91006469727e-05s
KAT.TestResult                : INFO     Output to json file:output/results/PartialUploadCase#92.json.
KAT.middleware                : INFO     Save Result To output/results/PartialUploadCase#92.json
KAT.PartialUploadCase         : INFO     Test Iteration #92 Is Done.
KAT.middleware                : INFO     Append Test #92 To Loop Results.
KAT.PartialUploadCase         : INFO     Start Test Iteration #93...
KAT.middleware                : INFO     Reset Test Result.
Run test step! self.total_pass: 3
KAT.middleware                : INFO     Test Elapsed Time: 1.09672546387e-05s
KAT.TestResult                : INFO     Output to json file:output/results/PartialUploadCase#93.json.
KAT.middleware                : INFO     Save Result To output/results/PartialUploadCase#93.json
KAT.PartialUploadCase         : INFO     Test Iteration #93 Is Done.
KAT.middleware                : INFO     Append Test #93 To Loop Results.
KAT.PartialUploadCase         : INFO     Start Test Iteration #94...
KAT.middleware                : INFO     Reset Test Result.
Run test step! self.total_pass: 4
KAT.middleware                : INFO     Test Elapsed Time: 7.48634338379e-05s
KAT.TestResult                : INFO     Output to json file:output/results/PartialUploadCase#94.json.
KAT.middleware                : INFO     Save Result To output/results/PartialUploadCase#94.json
KAT.PartialUploadCase         : INFO     Test Iteration #94 Is Done.
KAT.middleware                : INFO     Append Test #94 To Loop Results.
KAT.PartialUploadCase         : INFO     Start Test Iteration #95...
KAT.middleware                : INFO     Reset Test Result.
Run test step! self.total_pass: 5
KAT.middleware                : INFO     Test Elapsed Time: 3.19480895996e-05s
KAT.TestResult                : INFO     Output to json file:output/results/PartialUploadCase#95.json.
KAT.middleware                : INFO     Save Result To output/results/PartialUploadCase#95.json
KAT.PartialUploadCase         : INFO     Test Iteration #95 Is Done.
KAT.middleware                : INFO     Append Test #95 To Loop Results.
KAT.PartialUploadCase         : INFO     Start Test Iteration #96...
KAT.middleware                : INFO     Reset Test Result.
Run test step! self.total_pass: 6
KAT.middleware                : INFO     Test Elapsed Time: 7.89165496826e-05s
KAT.TestResult                : INFO     Output to json file:output/results/PartialUploadCase#96.json.
KAT.middleware                : INFO     Save Result To output/results/PartialUploadCase#96.json
KAT.PartialUploadCase         : INFO     Test Iteration #96 Is Done.
KAT.middleware                : INFO     Append Test #96 To Loop Results.
KAT.PartialUploadCase         : INFO     Start Test Iteration #97...
KAT.middleware                : INFO     Reset Test Result.
Run test step! self.total_pass: 7
KAT.middleware                : INFO     Test Elapsed Time: 7.10487365723e-05s
KAT.TestResult                : INFO     Output to json file:output/results/PartialUploadCase#97.json.
KAT.middleware                : INFO     Save Result To output/results/PartialUploadCase#97.json
KAT.PartialUploadCase         : INFO     Test Iteration #97 Is Done.
KAT.middleware                : INFO     Append Test #97 To Loop Results.
KAT.PartialUploadCase         : INFO     Start Test Iteration #98...
KAT.middleware                : INFO     Reset Test Result.
Run test step! self.total_pass: 8
KAT.middleware                : INFO     Test Elapsed Time: 1.00135803223e-05s
KAT.TestResult                : INFO     Output to json file:output/results/PartialUploadCase#98.json.
KAT.middleware                : INFO     Save Result To output/results/PartialUploadCase#98.json
KAT.PartialUploadCase         : INFO     Test Iteration #98 Is Done.
KAT.middleware                : INFO     Append Test #98 To Loop Results.
KAT.PartialUploadCase         : INFO     Start Test Iteration #99...
KAT.middleware                : INFO     Reset Test Result.
Run test step! self.total_pass: 9
KAT.middleware                : INFO     Test Elapsed Time: 9.77516174316e-06s
KAT.TestResult                : INFO     Output to json file:output/results/PartialUploadCase#99.json.
KAT.middleware                : INFO     Save Result To output/results/PartialUploadCase#99.json
KAT.PartialUploadCase         : INFO     Test Iteration #99 Is Done.
KAT.middleware                : INFO     Append Test #99 To Loop Results.
KAT.PartialUploadCase         : INFO     Start Test Iteration #100...
KAT.middleware                : INFO     Reset Test Result.
Run test step! self.total_pass: 10
KAT.middleware                : INFO     Test Elapsed Time: 0.000133991241455s
KAT.TestResult                : INFO     Output to json file:output/results/PartialUploadCase#100.json.
KAT.middleware                : INFO     Save Result To output/results/PartialUploadCase#100.json
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Test Result: {'build': '4.0.0-314',
 'elapsed_time': 0.00013399124145507812,
 'iteration': '4.0.0-314_itr_100',
 'pass': 10,
 'testName': 'PartialUploadCase',
 'testSuite': 'PartialUploadCases'}
KAT.middleware                : INFO     ###########################################################################
KAT.TestResult                : INFO     Uploaded data to logstash server: http://10.136.127.127:8080
KAT.PartialUploadCase         : INFO     Test Iteration #100 Is Done.
KAT.middleware                : INFO     Append Test #100 To Loop Results.
KAT.middleware                : INFO     Save Loop Results To output/results/test_report.xml
KAT.PartialUploadCase         : INFO     Test Is Done.
KAT.middleware                : WARNING  Unable to save logcat log because of ADB is disabled.
"""
