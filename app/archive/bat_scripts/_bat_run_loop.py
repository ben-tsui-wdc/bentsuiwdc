___author___ = 'Vance Lo <vance.lo@wdc.com>'

import sys
import os
import argparse
import time

from junit_xml import TestSuite
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from loadRestsdkmodule import loadRestsdkmodule
from checkCloudServices import checkCloudServices
from network_adb_connect import network_adb_Connect
from sambaEnabledCheck import sambaEnabledCheck
from loadAvahiNetatalkCheck import loadAvahiNetatalkCheck
from loadAfpCheck import loadAfpCheck
from loadAppManager import loadAppManager
from loadOtaClient import loadOtaClient
from checkUserRootsMountOnDevice import checkUserRootsMountOnDevice
from fwUpdateUtility import fwUpdateUtility

class bat_run(object):
    def __init__(self, adb=None):
        self.adb = adb
        self.isRunning = False
        self.log = common_utils.create_logger(root_log='BAT')
        self.start_time = None
        self.adb.connect()
        time.sleep(3)
        self.version = self.adb.getFirmwareVersion()
        self.platform = self.adb.getModel()
        if not self.version:
            raise Exception('Get build version error')

    def run(self, single=None, env=None, timeout=60*30, iterations=1):
        testcases = []
        for i in xrange(1, iterations+1):
            self._reset_start_time()
            # check device boot up
            while not self._is_timeout(timeout):
                boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed', timeout=10)[0]
                if '1' in boot_completed:
                    self.log.info('Boot completed')
                    break
                time.sleep(2)

            # check disk mounted
            while not self._is_timeout(timeout):
                disk_mounted= self.adb.executeShellCommand('getprop sys.wd.disk.mounted', timeout=10)[0]
                if '1' in disk_mounted:
                    self.log.info('Disk mounted')
                    break
                time.sleep(5)

            # check platform boot completed
            while not self._is_timeout(timeout):
                platform_bootable = self.adb.executeShellCommand('getprop wd.platform.bootable', timeout=10)[0]
                if '0' in platform_bootable:
                    self.log.info('Platform is bootable')
                    break
                time.sleep(2)

            if self._is_timeout(timeout):
                self.error('Device not mount'.format(timeout))

            testlist = [
                fwUpdateUtility,
                loadRestsdkmodule,
                network_adb_Connect,
                sambaEnabledCheck,
                loadAppManager,
                loadAvahiNetatalkCheck,
                loadAfpCheck,
                loadOtaClient,
                checkUserRootsMountOnDevice,
            ]


            for item in testlist:
                testrun = item(adb=adb, env=env)
                self.log.info('=============== Start to run {} test!! ==============='.format(str(item)))
                test = testrun.run()
                testcases.append(test)
                time.sleep(2)

        ts = TestSuite('BAT Test Suite', testcases)

        with open('output.xml', 'w') as f:
            TestSuite.to_file(f, [ts], prettyprint=True)

    def check_adb(self, timeout):
        if self.adb.connected:
            self.adb.disconnect()
        while not self._is_timeout(timeout):
            self.log.info('Attempt to connect...')
            try:
                self.adb.connect(timeout=10)
            except Exception:
                self.log.info('adb not connecting')
                time.sleep(5)
            if self.adb.connected:
                break
        if not self.adb.connected:
            self.error('Device not responding, timeout for {} secs'.format(timeout))

    def _reset_start_time(self):
        self.start_time = time.time()

    def _is_timeout(self, timeout):
        return (time.time() - self.start_time) >= timeout

    def error(self, message):
        self.log.error(message)
        raise Exception(message)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    parser.add_argument('-env', help='Target environment', default='dev1')
    parser.add_argument('-single', help='Run single case')
    parser.add_argument('-iter', help='Number of iterations, ex. 100')
    args = parser.parse_args()

    if args.iter:
        iterations = int(args.iter)
    else:
        iterations = 1
    uut_ip = args.uut_ip
    env = args.env
    single = args.single
    if args.port:
        port = args.port
    else:
        port = '5555'

    adb = ADB(uut_ip=uut_ip, port=port)

    bat = bat_run(adb=adb)
    bat.run(single=single, env=env, iterations=iterations)

