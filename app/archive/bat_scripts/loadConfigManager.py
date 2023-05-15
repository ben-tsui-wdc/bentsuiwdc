___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from junit_xml import TestCase


class loadConfigManager(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env

    def run(self):
        start_time = time.time()
        testcase = None
        try:
            self.device_init()
            config_daemon = self.adb.executeShellCommand('ps | grep configmgr')[0]
            config_ls_list = self.adb.executeShellCommand('ls -l /data/wd/diskVolume0/confmgr/db')[0]
            check_list1 = ['/bin/configmgr']
            check_list2 = ['config.store']
            if all(word in config_daemon for word in check_list1) and all(word in config_ls_list for word in check_list2):
                print 'Load Conf Manager in firmware test PASSED!!'
                testcase = TestCase(name='Load Config Manager', classname='BAT', elapsed_sec=time.time()-start_time)
            else:
                raise Exception('Load Conf Manager in firmware test FAILED!!')
        except Exception as ex:
            testcase = TestCase(name='Load Config Manager', classname='BAT', elapsed_sec=time.time()-start_time)
            testcase.add_failure_info('Test Failed. Err: {}'.format(ex))
            raise Exception('Test Failed. Err: {}'.format(ex))
        finally:
            return testcase

    def device_init(self):
        try:
            self.adb.connect()
            time.sleep(2)
            version = self.adb.executeShellCommand('getprop ro.build.version.incremental')[0]
            print 'Firmware is :{}'.format(version)
            time.sleep(1)
        except Exception as ex:
            raise Exception('Failed to connect to device and execute adb command! Err: {}'.format(ex))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    if args.port:
        port = args.port
    else:
        port = '5555'
    adb = ADB(uut_ip=uut_ip, port=port)

    testrun = loadConfigManager(adb=adb)
    testrun.run()
