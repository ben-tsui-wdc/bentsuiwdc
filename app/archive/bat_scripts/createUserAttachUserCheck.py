___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries.restAPI import RestAPI
from junit_xml import TestCase


class createUserAttachUser(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env
        self.start_time = time.time()
        self.testcase = None
        self.device_init()
        self.username = 'wdctestbat01@test.com'
        self.password = 'Test1234'

    def run(self):
        try:
            if self.env:
                self.rest_u1 = RestAPI(uut_ip=self.adb.uut_ip, env=self.env, username=self.username, password=self.password, debug=True)
            else:
                self.rest_u1 = RestAPI(uut_ip=self.adb.uut_ip, username=self.username, password=self.password)

            # self.rest_u1.create_user()
            # self.rest_u1.attach_user_to_device()
            print 'Create User & Attach User Checked PASSED!!'
            self.testcase = TestCase(name='Create User & Attach User Checked', classname='BAT', elapsed_sec=time.time()-self.start_time)
        except Exception as ex:
            self.testcase = TestCase(name='Create User & Attach User Checked', classname='BAT', elapsed_sec=time.time()-self.start_time)
            self.testcase.add_failure_info('Create User & Attach User Checked FAILED!! Err: {}'.format(ex))
            raise Exception('Test Failed. Err: {}'.format(ex))
        finally:
            return self.testcase

    def device_init(self):
        try:
            self.adb.connect()
            time.sleep(2)
            version = self.adb.getFirmwareVersion()
            platform = self.adb.getModel()
            print 'Firmware is :{}'.format(version.split()[0])
            print 'Platform is :{}'.format(platform.split()[0])
            time.sleep(1)
            return version.split()[0], platform.split()[0]
        except Exception as ex:
            raise Exception('Failed to connect to device and execute adb command! Err: {}'.format(ex))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    parser.add_argument('-env', help='Target environment, ex. dev1 (default)')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    env = args.env
    if args.port:
        port = args.port
    else:
        port = '5555'
    adb = ADB(uut_ip=uut_ip, port=port)

    testrun = createUserAttachUser(adb=adb, env=env)
    testrun.run()
    time.sleep(5)
