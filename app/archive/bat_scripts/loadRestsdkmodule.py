___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from junit_xml import TestCase


class loadRestsdkmodule(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env
        # self.log = logging.getLogger('BAT')
        # formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-4s: %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        # common_utils.setupLogger(loggerName='BAT', logfile='output/adb/bat.log', level=logging.DEBUG, formatter=formatter)

    def run(self):
        # self.log.info('===== Start to test Load Rest-sdk module =====')
        start_time = time.time()
        testcase = None
        try:
            self.device_init()
            restsdk_daemon = self.adb.executeShellCommand('ps | grep restsdk | grep -v grep')[0]
            restsdk_ls_list = self.adb.executeShellCommand('ls -l /data/wd/diskVolume0/restsdk/data/db')[0]
            check_list1 = ['restsdk-server']
            check_list2 = ['index.db', 'index.db-shm', 'index.db-wal']
            if all(word in restsdk_daemon for word in check_list1) and all(word in restsdk_ls_list for word in check_list2):
                print 'Verify Restsdk module is loaded in firmware PASSED!!'
                # self.log.info('Verify Restsdk module is loaded in firmware PASSED!!')
                testcase = TestCase(name='Load Rest-sdk Module', classname='BAT', elapsed_sec=time.time()-start_time)
            else:
                # self.log.error('Verify Restsdk module is loaded in firmware FAILED!!', level=logging.ERROR)
                raise Exception('Verify Restsdk module is loaded in firmware FAILED!!')
        except Exception as ex:
            testcase = TestCase(name='Load Rest-sdk Module', classname='BAT', elapsed_sec=time.time()-start_time)
            testcase.add_failure_info('Test Failed. Err: {}'.format(ex))
            raise Exception('Test Failed. Err: {}'.format(ex))
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

    testrun = loadRestsdkmodule(adb=adb)
    testrun.run()
