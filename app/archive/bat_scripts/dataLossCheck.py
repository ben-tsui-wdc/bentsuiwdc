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


class dataLossCheck(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env
        self.log = common_utils.create_logger(overwrite=False)
        self.device_init()
        self.username = 'wdctestbat01@test.com'
        self.password = 'Test1234'
        self.root_folder = '/data/wd/diskVolume0/restsdk/userRoots/'
        self.mount_path = '/mnt/media_rw/'

    def run(self):
        start_time = time.time()
        testcase = None
        try:
            self.owner = RestAPI(self.adb.uut_ip, self.env, self.username, self.password)
            # Generate checksum list for the files in USB
            bat_chk_dic = {}
            self.usb_mount = self.adb.executeShellCommand('ls {}'.format(self.mount_path))[0].split()[0]
            usb_path = '{0}{1}/'.format(self.mount_path, self.usb_mount)
            usb_files = self.adb.executeShellCommand('find {0} -type f'.format(usb_path))[0]
            lists = [path.split(usb_path).pop() for path in usb_files.split()]
            for item in lists:
                if any(char.isdigit() for char in item) and not item.startswith('.'):
                    md5sum = self.adb.executeShellCommand('busybox md5sum {0}{1}/{2}'
                                                          .format(self.mount_path, self.usb_mount, item),
                                                          consoleOutput=False)[0].split()[0]
                    bat_chk_dic.update({item: md5sum})
            user_id = self.owner.get_user_id()
            if 'auth0|' in user_id:
                user_id = user_id.replace('auth0|', 'auth0\|')
            copy_id, usb_info, resp = self.owner.usb_slurp()
            self.usb_name = usb_info.get('name')

            # Execute move_upload_logs.sh -d
            time.sleep(5)
            self.adb.executeShellCommand('move_upload_logs.sh -d')
            time.sleep(3)

            PASSED = 0
            FAILED = 0
            for key, value in bat_chk_dic.iteritems():
                sync_chksum = self._md5_checksum(user_id, key)
                source_chksum = bat_chk_dic[key]
                self.log.info('{} - sync_chksum:{}, source_chksum:{}'.format(key, sync_chksum, source_chksum))
                if sync_chksum == source_chksum:
                    PASSED += 1
                else:
                    FAILED += 1
            if FAILED > 0:
                self.error('Data Compare FAILED!! PASSED_FILES: {0}, FAILED_FILES: {1}'
                           .format(PASSED, FAILED))
            else:
                self.log.info('Data Loss Check!!!! Test PASSED!!!!')
                testcase = TestCase(name='Data Loss Check', classname='BAT', elapsed_sec=time.time()-start_time)
        except Exception as ex:
            testcase = TestCase(name='Data Loss Check', classname='BAT', elapsed_sec=time.time()-start_time)
            testcase.add_failure_info('Test Failed. Err: {}'.format(ex))
        finally:
            return testcase

    def _md5_checksum(self, user_id, file_name):
        usb_name = self.usb_name.replace(' ', '\ ')
        path = os.path.join(self.root_folder, user_id, usb_name, file_name)
        result = self.adb.executeShellCommand('busybox md5sum {}'.format(path), consoleOutput=False, timeout=180)
        self.log.debug(result)
        result = result[0].strip().split()[0]
        return result

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

    testrun = dataLossCheck(adb=adb, env=env)
    testrun.run()
