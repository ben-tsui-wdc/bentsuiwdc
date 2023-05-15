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


class usbAutoMount(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env
        self.log = common_utils.create_logger(overwrite=False)
        self.device_init()
        self.username = 'wdctestbat01@test.com'
        self.password = 'Test1234'
        self.mount_path = '/mnt/media_rw/'

    def run(self):
        start_time = time.time()
        testcase = None
        try:
            self.owner = RestAPI(self.adb.uut_ip, self.env, self.username, self.password)
            self.usb_mount = self.adb.executeShellCommand('ls {}'.format(self.mount_path))[0].strip()
            if self.usb_mount:
                usb_info = self.owner.get_usb_info()
                self.usb_id = usb_info.get('id')
                self.usb_name = usb_info.get('name')
                self.log.info('USB Name is: {}'.format(self.usb_name))
                self.log.info('USB folder id is: {}'.format(self.usb_id))
                self.log.info('USB Auto Mount Test! Test PASSED!!!!')
                testcase = TestCase(name='USB Auto Mount Test', classname='BAT', elapsed_sec=time.time()-start_time)
            else:
                self.error('USB is not mounted!!!!')
        except Exception as ex:
            testcase = TestCase(name='USB Auto Mount Test', classname='BAT', elapsed_sec=time.time()-start_time)
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
    parser.add_argument('-env', help='Target environment, ex. dev1 (default)')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    port = args.port
    env = args.env
    adb = ADB(uut_ip=uut_ip, port=port)

    testrun = usbAutoMount(adb=adb, env=env)
    testrun.run()
