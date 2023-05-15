___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from junit_xml import TestCase


class network_adb_Connect(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env

    def run(self):
        start_time = time.time()
        testcase = None
        try:
            self.device_init()
            stdout, stderr = self.adb.executeShellCommand('cat /proc/version')
            if 'Linux version' in stdout:
                print 'Test enable network and adb connection PASSED!!'
                testcase = TestCase(name='Network ADB Connect', classname='BAT', elapsed_sec=time.time()-start_time)
            else:
                raise Exception('Test enable network and adb connection FAILED!!')
        except Exception as ex:
            testcase = TestCase(name='Network ADB Connect', classname='BAT', elapsed_sec=time.time()-start_time)
            testcase.add_failure_info('ADB connect and execute shell failed. Err: {}'.format(ex))
            raise Exception('ADB connect and execute shell failed. Err: {}'.format(ex))
        finally:
            return testcase

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
    parser = argparse.ArgumentParser(description='Test script to test network enable and adb connection')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    if args.port:
        port = args.port
    else:
        port = '5555'
    adb = ADB(uut_ip=uut_ip, port=port)

    testrun = network_adb_Connect(adb=adb)
    testcase = testrun.run()


