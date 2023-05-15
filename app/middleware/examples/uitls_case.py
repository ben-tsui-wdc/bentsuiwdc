# -*- coding: utf-8 -*-
""" A test with run test behavior of template.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class UitlsTest(TestCase):

    TEST_SUITE = 'UitlsTests'
    TEST_NAME = 'UitlsTest'

    def test(self):
        print "Run test step!"
        resp = self.adb.whoami()
        self.log.info('whoami: {}'.format(resp))
        resp = self.power_switch.outlet_status_list()
        self.log.info('outlet_status_list: {}'.format(resp))
        resp = self.power_switch.outlet_status(self.env.power_switch_port)
        self.log.info('outlet_status({0}): {1}'.format(self.env.power_switch_port, resp))
        resp = self.uut_owner.get_device_info()
        self.log.info('get_device_info: {}'.format(resp))
        resp = self.uut_owner.get_usb_info()
        self.log.info('get_usb_info: {}'.format(resp))


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Uitls Test on Kamino Android ***
        Examples: ./run.sh middleware/examples/uitls_case.py --uut_ip 10.136.137.159\
        """)
    # Test Arguments
    parser.add_argument('-mv', '--my_var', help='An additional variable.', type=int, default=1000)

    test = UitlsTest(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)

"""
[Command]
    ./run.sh middleware/examples/middleware/examples/uitls_case.py --uut_ip 10.136.137.159 -lsu http://10.136.127.127:8080 -debug --my_var 123 --power_switch_ip 10.136.139.14 --power_switch_port 4

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
 'log': <logging.Logger object at 0x7ff5ae465a50>,
 'logcat_name': 'logcat',
 'logstash_server_url': 'http://10.136.127.127:8080',
 'loop_times': None,
 'output_folder': 'output',
 'password': 'Test1234',
 'power_switch_ip': '10.136.139.14',
 'power_switch_port': 4,
 'results_folder': 'output/results',
 'testcase': <__main__.UitlsTest object at 0x7ff5aabe0150>,
 'username': 'wdctest_owner@test.com',
 'uut_ip': '10.136.137.159',
 'uut_port': 5555}
KAT.middleware                : INFO     Test Case Attributes: {'adb': <platform_libraries.adblib.ADB object at 0x7ff5aabe0290>,
 'data': <middleware.component.ResultComponent object at 0x7ff5aabe0210>,
 'env': <middleware.test_case.Environment object at 0x7ff5aabe0190>,
 'ext': <middleware.component.ExtensionComponent object at 0x7ff5aabe01d0>,
 'log': <logging.Logger object at 0x7ff5b07737d0>,
 'my_var': 123,
 'power_switch': <platform_libraries.powerswitchclient.PowerSwitchClient object at 0x7ff5aabe0b10>,
 'timing': <middleware.component.TimingComponent object at 0x7ff5aabe0250>,
 'utils': <class 'middleware.component.UtilityGenerator'>,
 'uut_owner': <platform_libraries.restAPI.RestAPI object at 0x7ff5aabe0f90>}
KAT.middleware                : INFO     ###########################################################################
KAT.UitlsTest                 : INFO     Start Test...
KAT.middleware                : INFO     Reset Test Result.
Run test step!
KAT.UitlsTest                 : INFO     whoami: root

KAT.UitlsTest                 : INFO     outlet_status_list: [[1, u'Outlet 1', u'ON'], [2, u'Outlet 2', u'ON'], [3, u'Outlet 3', u'ON'], [4, u'Outlet 4', u'ON'], [5, u'Outlet 5', u'ON'], [6, u'Outlet 6', u'ON'], [7, u'Outlet 7', u'ON'], [8, u'Outlet 8', u'ON']]
KAT.UitlsTest                 : INFO     outlet_status(4): [u'ON']
KAT.restAPI                   : INFO     Getting Device Info
KAT.restAPI                   : INFO     Getting ID token of user: wdctest_owner@test.com
KAT.restAPI                   : INFO     Use existed ID token, it will be expired in 1784 seconds
KAT.restAPI                   : INFO     Getting local code and security code
KAT.restAPI                   : INFO     Getting ID token of user: wdctest_owner@test.com
KAT.restAPI                   : INFO     Use existed ID token, it will be expired in 1784 seconds
KAT.restAPI                   : INFO     Get local code and security code successfully
KAT.restAPI                   : INFO     Get device info successfully
KAT.UitlsTest                 : INFO     get_device_info: {u'sendOTANotification': True, u'name': u"'s My Cloud 3", u'createdOn': u'2017-03-14T03:36:48', u'firmware': {u'wiri': u'4.0.0-314'}, u'attachedStatus': u'APPROVED', u'network': {u'tunnelId': u'8a8089be549c18c201549c91dc810000', u'portForwardPort': -1, u'proxyURL': u'https://dev1-proxy1.wdtest1.com:9443/19ca5597-735b-4aa5-8d70-9b1d9074514b', u'portForwardInfoUpdateStatus': u'PORT_TEST_NOT_APPLICABLE', u'connectionType': 3, u'localIpAddress': u'10.136.137.159', u'httpPort': 0, u'externalIpAddress': u'199.255.47.12', u'internalDNSName': u'device-local-19ca5597-735b-4aa5-8d70-9b1d9074514b.wdtest6.com', u'internalURI': u'http://10.136.137.159', u'internalURL': u'http://10.136.137.159', u'externalURI': u'https://dev1-proxy1.wdtest1.com:9443/19ca5597-735b-4aa5-8d70-9b1d9074514b'}, u'mac': u'00:14:ee:00:c1:4e', u'deviceId': u'19ca5597-735b-4aa5-8d70-9b1d9074514b', u'cloudConnected': True, u'configuration': {u'wisb': u'global_default', u'wiri': u'global_default'}, u'type': u'monarch', u'modelId': u'0'}
KAT.restAPI                   : INFO     Get USB informatione
KAT.restAPI                   : INFO     Searching file by parent_id:
KAT.restAPI                   : INFO     Getting ID token of user: wdctest_owner@test.com
KAT.restAPI                   : INFO     Use existed ID token, it will be expired in 1782 seconds
KAT.restAPI                   : INFO     List top level: [{u'mimeType': u'application/x.wd.dir', u'name': u'My Passport', u'storageType': u'usb', u'mTime': u'2017-03-14T03:36:45.443Z', u'id': u'4E1AEA7B1AEA6007', u'eTag': u'"Ag"', u'privatelyShared': False, u'parentID': u'', u'hidden': u'none', u'publiclyShared': False, u'childCount': 0, u'cTime': u'2017-03-14T03:36:45.443Z'}, {u'mimeType': u'application/x.wd.dir', u'name': u'auth0|58c285533d778f6e3000070b', u'storageType': u'local', u'mTime': u'2017-03-14T03:39:27.065Z', u'id': u'YLBh_nKWXb5-QGToZOSJOr6qWCqXpNj2-jl8R1ro', u'eTag': u'"Ag"', u'privatelyShared': False, u'parentID': u'', u'hidden': u'none', u'publiclyShared': False, u'childCount': 0, u'cTime': u'2017-03-14T03:39:27.065Z'}]
KAT.UitlsTest                 : INFO     get_usb_info: {u'mimeType': u'application/x.wd.dir', u'name': u'My Passport', u'storageType': u'usb', u'mTime': u'2017-03-14T03:36:45.443Z', u'id': u'4E1AEA7B1AEA6007', u'eTag': u'"Ag"', u'privatelyShared': False, u'parentID': u'', u'hidden': u'none', u'publiclyShared': False, u'childCount': 0, u'cTime': u'2017-03-14T03:36:45.443Z'}
KAT.middleware                : INFO     Test Elapsed Time: 15.0438730717s
KAT.TestResult                : INFO     Output to json file:output/results/UitlsTest.json.
KAT.middleware                : INFO     Save Result To output/results/UitlsTest.json
KAT.middleware                : INFO     ###########################################################################
KAT.middleware                : INFO     Test Result: {'build': '4.0.0-314',
 'elapsed_time': 15.043873071670532,
 'testName': 'UitlsTest',
 'testSuite': 'UitlsTests'}
KAT.middleware                : INFO     ###########################################################################
KAT.TestResult                : INFO     Uploaded data to logstash server: http://10.136.127.127:8080
KAT.UitlsTest                 : INFO     Test Is Done.
KAT.adblib                    : INFO     Save logcat information to output/logcat
"""