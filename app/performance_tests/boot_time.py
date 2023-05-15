# -*- coding: utf-8 -*-
""" kpi test includes uboot_time, boot_time, and "device connected to cloud" check.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import os
import re
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.restAPI import RestAPI

class boot_time(TestCase):
    TEST_SUITE = 'Performance_Tests'
    TEST_NAME = 'kpi_boot_time'
    # Popcorn
    TEST_JIRA_ID = 'KAM-13278,KAM-25092'


    # Pre-defined parameters for IntegrationTest
    def declare(self):
        self.boot_time_path = '/proc/boot_time'
        self.uboot_time_path = '/proc/device-tree/factory/boottime'

    # main function
    def test(self):
        self.product = self.adb.getModel()
        reboot_time = self.get_reboot_time()
        uboot_time = self.get_uboot_time()
        boot_time, boot_time_and_additional_check = self.get_boot_time()
        self.adb.stop_otaclient()
        
        self.data.test_result['wifi_mode'] = self.wifi_mode
        self.data.test_result['reboot_time'] = reboot_time
        self.data.test_result['boot_time'] = boot_time
        self.data.test_result['uboot_time'] = uboot_time
        self.data.test_result['boot_time_and_additional_check'] = boot_time_and_additional_check



    def is_device_pingable(self):
        command = 'nc -zv -w 1 {0} 80 > /dev/null 2>&1'.format(self.adb.uut_ip)
        response = os.system(command)
        if response == 0:
            return True
        else:
            return False


    def wait_device_back(self):
        starting_time = time.time()
        while True:
            try:
                self.adb.connect(timeout=10)
            except Exception:
                self.log.info('adb not connecting')
                time.sleep(1)
            if self.adb.connected:
                time.sleep(3)
                try:
                    boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed')[0]
                    if '1' in boot_completed:
                        print 'Boot completed'
                        break
                except Exception as ex:
                    self.log.info(ex)
                    self.log.info('Try again...')
            if time.time() - starting_time > 120:
                raise self.err.TestError('Device is not ready after trying 120 seconds to reconnect')


    def get_reboot_time(self):
        max_boot_time = 600
        starting_time = time.time()
        self.log.info('Start Rebooting..')
        self.adb.executeShellCommand('busybox nohup reboot')
        while self.is_device_pingable():
            self.log.info('Waiting device power off ...')
            time.sleep(1)
            if time.time() - starting_time >= max_boot_time:
                raise self.err.TestError('Device failed to power off within {} seconds'.format(max_boot_time))
        while not self.is_device_pingable():
            self.log.info('Waiting device boot up ...')
            time.sleep(1)
            if time.time() - starting_time > max_boot_time:
                raise self.err.TestError('Timed out waiting to boot within {} seconds'.format(max_boot_time))
        self.wait_device_back()
        reboot_time = time.time() - starting_time
        return int(reboot_time)


    def get_uboot_time(self):
        loop = 1
        while True:
            uboot_time = self.adb.executeShellCommand('cat {}'.format(self.uboot_time_path))[0]
            if 'No such file or directory' in uboot_time:
                uboot_time = 0
                break
            else:
                uboot_time = uboot_time.strip('\x00')
            if uboot_time and int(uboot_time) > 0:
                break
            elif loop == 120:
                raise self.err.TestError('Failed to get uboot_time after retry {} times'.format(loop))
            time.sleep(1)
            loop += 1
        return int(uboot_time)


    def get_boot_time(self):
        loop = 1
        while True:
            Android_boot_time = self.adb.executeShellCommand('cat {}'.format(self.boot_time_path))[0]
            if Android_boot_time and int(Android_boot_time) > 0:
                break
            elif loop == 120:
                raise self.err.TestError('Failed to get "cat /proc/boot_time" after retry {} times'.format(loop))
            self.log.info('Boot_time not exist, try again.. loop {}'.format(loop))
            time.sleep(1)
            loop += 1

        # Calculate the duration time until major services finished starting.
        starting_time = time.time()
        if 'yoda' in self.uut.get('model'):
            while True:
                #stdout, stderr = self.adb.executeShellCommand('logcat -d | grep BTWifiConfigService')
                stdout, stderr = self.adb.executeShellCommand('logcat -d | grep Advertising && logcat -d | grep LeAdvStarted')
                if self.uut.get('firmware').startswith('5.2.0'):
                    if 'Advertising started' in stdout and 'success' in stdout:
                        break
                elif not self.uut.get('firmware').startswith('5.2.0'):
                    if 'startAdvertising' in stdout and 'success' in stdout:
                        break
                elif time.time() - starting_time > 120:
                    raise self.err.TestError('Although /proc/time occurred, "startAdvertising" and "success" aren\'t displayed in logcat after 120 seconds..')
                time.sleep(1)
            '''
            Special request from James
            '''
            print "Original Android_boot_time: {}".format(Android_boot_time)
            Android_boot_time = int(Android_boot_time) + (time.time() - starting_time)
            print "Original Android_boot_time plus BT launched time: {}".format(Android_boot_time)

        while True:
            if self.uut['model'] in ['yoda', 'yodaplus']:
                result = self.adb.executeShellCommand("ps | egrep 'otaclient|appmgr|restsdk'")[0]
                if 'otaclient' in result and \
                    'appmgr' in result and \
                    'restsdk-server' in result:
                    break
                elif time.time() - starting_time > 120:
                    raise self.err.TestError('Although /proc/time occurred, one of otaclient|appmgr|restsdk still doesn\'t work after 120 seconds.')
            else:
                result = self.adb.executeShellCommand("ps | egrep 'otaclient|appmgr|restsdk|avahi'")[0]
                if 'otaclient' in result and \
                    'appmgr' in result and \
                    'restsdk-server' in result and \
                    'avahi' in result:
                    break
                elif time.time() - starting_time > 120:
                    raise self.err.TestError('Although /proc/time occurred, one of otaclient|appmgr|restsdk|avahi still doesn\'t work after 120 seconds.')
            time.sleep(1)

        #boot_time = int(Android_boot_time) + (time.time() - starting_time)
        boot_time = int(Android_boot_time)

        # cloud check after DUT rebooting
        # Because there is no device side status that can be queried so far, what script can only do 
        # is attaching a user to device.
        starting_time = time.time()
        while True:
            try:
                # Attaching a user to device can check auth cloud and device cloud at the same time
                REST_API = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username='{}_boot_time_kpi_{}@gmail.com'.format(self.env.username.split('@')[0], self.env.iteration), password=self.env.password, client_settings={'config_url': self.uut['config_url']})
                device_info = self.uut_owner.get_device_info()
                cloud_connected_value = None
                for k, v in device_info.items():
                    if k == 'cloudConnected':
                        cloud_connected_value = str(v)
                if cloud_connected_value != 'True':
                    raise self.err.TestError('*** FAIL: cloudConnected: {} while executing boot_time.py'.format(cloud_connected_value))
                break
            except Exception as e:
                print e
                time.sleep(1)
                if time.time() - starting_time > 1200:
                    raise self.err.TestError('Additional check failed after 1200 seconds.')
        cloud_check_time = time.time() - starting_time
        boot_time_and_additional_check = boot_time + cloud_check_time
        return int(boot_time), int(boot_time_and_additional_check)


if __name__ == '__main__':

    parser = InputArgumentParser("""\
        *** time_machine_throughput test on Kamino Android ***
        Examples: ./run.sh performance_tests/boot_time.py --uut_ip 10.92.224.13 \
        --cloud_env qa1 --loop_times 4 --debug_middleware --dry_run\
        """)
    parser.add_argument('--wifi_mode', help='type of wifi mode, by default is None', choices=['None','2.4G', '5G'], default='None')

    test = boot_time(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)