"""
Create on 31 Aug, 2016
@Author: Nick Yang
Objective:  Check cloud services and IP address by Rest command by verifying "cloudConnected" and "localIpAddress" fields
wiki URL:   http://silk.sc.wdc.com/silk/DEF/TM/Test+Plan?nEx=33214&execView=execDetails&view=details&pltab=steps&pId=86&nTP=317547
"""

import requests
import argparse
import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries.restAPI import RestAPI
from platform_libraries import common_utils
from junit_xml import TestCase


class checkCloudServices(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env
        self.username = 'wdctestbat01@test.com'
        self.password = 'Test1234'
        self.log = common_utils.create_logger(overwrite=False)


    def run(self):
        start_time = time.time()
        testcase = None
        try:
            if self.env:
                rest_u1 = RestAPI(uut_ip=self.adb.uut_ip, env=self.env, username=self.username, password=self.password, debug=True)
            else:
                rest_u1 = RestAPI(uut_ip=self.adb.uut_ip, username=self.username, password=self.password)
            device_info = rest_u1.get_device_info()
            self.log.info(device_info)

            cloud_connected_value = None

            for k, v in device_info.items():
                if k == 'cloudConnected':
                    cloud_connected_value = str(v)

            if cloud_connected_value == 'True':
                self.log.info('*** PASS: cloudConnected: {}'.format(cloud_connected_value))
            else:
                raise Exception('*** FAIL: cloudConnected: {}'.format(cloud_connected_value))

        except Exception as ex:
            testcase = TestCase(name='Check Cloud Services', classname='BAT', elapsed_sec=time.time()-start_time)
            testcase.add_failure_info('*** ERROR: Check cloud services is not successful: {} ***'.format(repr(ex)))
            raise Exception('*** ERROR: Check cloud services is not successful: {} ***'.format(repr(ex)))
        else:
            self.log.info('*** PASS: Check cloud services is performed successfully ***')
            testcase = TestCase(name='Check Cloud Services', classname='BAT', elapsed_sec=time.time()-start_time)
        finally:
            return testcase

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Execute check cloud services')
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

    test = checkCloudServices(adb=adb, env=env)
    test.run()
