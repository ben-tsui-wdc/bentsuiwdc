___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from platform_libraries.restAPI import RestAPI
from junit_xml import TestCase


class rebootTest(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env
        self.log = common_utils.create_logger(overwrite=False)
        self.device_init()
        self.username = 'wdctestbat01@test.com'
        self.password = 'Test1234'
        self.timeout = 60*30

    def run(self):
        self._reset_start_time()
        testcase = None
        try:
            # Reboot device
            if self.env:
                self.log.info('Use REST API to reboot device')
                self.rest_u1 = RestAPI(uut_ip=self.adb.uut_ip, env=self.env, username=self.username, password=self.password, debug=True)
                if self.rest_u1.reboot_device():
                    self.log.info('Device rebooting..')
            else:
                self.log.info('Use ADB command to reboot device')
                self.adb.executeShellCommand('busybox nohup reboot')
            self.adb.disconnect()
            time.sleep(60)
            self.check_adb()
            self.check_device_bootup()
            self.check_platform_boot_completed()

            if self._is_timeout(self.timeout):
                self.error('Device is not ready, timeout for {} minutes'.format(self.timeout/60))
            else:
                self.log.info('Device Reboot Test! Test PASSED!!!!')
                testcase = TestCase(name='Device Reboot Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
        except Exception as ex:
            testcase = TestCase(name='Device Reboot Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            testcase.add_failure_info('Test Failed. Err: {}'.format(ex))
            self.log.warning('Reboot failed, try to use ADB command to reboot device again')
            self.adb.executeShellCommand('busybox nohup reboot')
            self.adb.disconnect()
            time.sleep(60)
            self.check_adb()
            self.check_device_bootup()
            self.check_platform_boot_completed()
        finally:
            return testcase

    def check_adb(self):
        if self.adb.connected:
            self.adb.disconnect()
        while not self._is_timeout(self.timeout):
            self.log.info('Attempt to connect...')
            try:
                self.adb.connect(timeout=10)
            except Exception:
                self.log.info('adb not connecting')
                time.sleep(5)
            if self.adb.connected:
                break
        if not self.adb.connected:
            self.error('Device not responding, timeout for {} secs'.format(self.timeout))

    def check_device_bootup(self):
        # check device boot up
        while not self._is_timeout(self.timeout):
            boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed', timeout=10)[0]
            if '1' in boot_completed:
                self.log.info('Boot completed')
                break
            time.sleep(2)

    def check_platform_boot_completed(self):
        # check platform boot completed
        while not self._is_timeout(self.timeout):
            platform_bootable = self.adb.executeShellCommand('getprop wd.platform.bootable', timeout=10)[0]
            if '0' in platform_bootable:
                self.log.info('Platform is bootable')
                break
            time.sleep(2)

    def _reset_start_time(self):
        self.start_time = time.time()

    def _is_timeout(self, timeout):
        return (time.time() - self.start_time) >= timeout

    def device_init(self):
        try:
            self.adb.connect()
            time.sleep(2)
            self.version = self.adb.getFirmwareVersion()
            self.platform = self.adb.getModel()
            self.log.info('Firmware is :{}'.format(self.version.split()[0]))
            self.log.info('Platform is :{}'.format(self.platform.split()[0]))
            time.sleep(1)
            return self.version.split()[0], self.platform.split()[0]
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
    parser.add_argument('-env', help='Target environment, ex. dev1 (default)')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    port = args.port
    env = args.env
    adb = ADB(uut_ip=uut_ip, port=port)

    testrun = rebootTest(adb=adb, env=env)
    testrun.run()
