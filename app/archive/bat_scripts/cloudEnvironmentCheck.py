___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from junit_xml import TestCase


class cloudEnvironmentCheck(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env
        self.log = common_utils.create_logger(overwrite=False)
        self.device_init()

    def run(self):
        start_time = time.time()
        testcase = None
        try:
            cloudEnv = self.adb.executeShellCommand('cat /system/etc/restsdk-server.toml | grep "configURL"')[0]
            if self.env == 'dev1':
                check_list = ['https://dev1.wdtest1.com']
            elif self.env == 'qa1':
                check_list = ['https://qa1.wdtest1.com']
            else:
                check_list = ['https://config.mycloud.com']
            if all(word in cloudEnv for word in check_list):
                self.log.info('Cloud Environment Checked PASSED!!')
                testcase = TestCase(name='Cloud Environment Check', classname='BAT', elapsed_sec=time.time()-start_time)
            else:
                raise Exception('Cloud Environment Checked FAILED!!')
        except Exception as ex:
            testcase = TestCase(name='Cloud Environment Check', classname='BAT', elapsed_sec=time.time()-start_time)
            testcase.add_failure_info('Test Failed. Err: {}'.format(ex))
        finally:
            return testcase

    def device_init(self):
        try:
            self.adb.connect()
            time.sleep(2)
            version = self.adb.getFirmwareVersion()
            platform = self.adb.getModel()
            self.log.info('Firmware is :{}'.format(version.split()[0]))
            self.log.info('Platform is :{}'.format(platform.split()[0]))
            time.sleep(1)
            return version.split()[0], platform.split()[0]
        except Exception as ex:
            self.log.error('Failed to connect to device and execute adb command! Err: {}'.format(ex))

    def error(self, message):
        """
            Save the error log and raise Exception at the same time
            :param message: The error log to be saved
        """
        self.log.error(message)
        raise Exception(message)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)', default='5555')
    parser.add_argument('-env', help='Target environment', default='dev1')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    port = args.port
    env = args.env
    adb = ADB(uut_ip=uut_ip, port=port)

    testrun = cloudEnvironmentCheck(adb=adb, env=env)
    testrun.run()
