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


class usbSlurpDeleteTest(object):

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
            self.usb_mount = self.adb.executeShellCommand('ls {}'.format(self.mount_path))[0].split()[0]
            usb_path = '{0}{1}/'.format(self.mount_path, self.usb_mount)
            usb_files = self.adb.executeShellCommand('find {0} -type f'.format(usb_path))[0]
            lists = [path.split(usb_path).pop() for path in usb_files.split()]
            user_id = self.owner.get_user_id()
            if 'auth0|' in user_id:
                user_id = user_id.replace('auth0|', 'auth0\|')
            copy_id, usb_info, resp = self.owner.usb_slurp()
            self.usb_name = usb_info.get('name')
            usb_name = self.usb_name.replace(' ', '\ ')
            usb_path = os.path.join(self.root_folder, user_id, usb_name)
            usb_sync_files1 = self.adb.executeShellCommand('find {0} -type f'.format(usb_path))[0]
            sync_lists = [path.split(usb_path).pop() for path in usb_sync_files1.split('\r\n')]
            sync_lists.pop()
            self.log.info('Current Sync Files: {}'.format(sync_lists))
            num_file = len(sync_lists)

            # Delete Files
            delete = 0
            for file in sync_lists:
                usb_folder, search_time = self.owner.search_file_by_parent_and_name(parent_id='root', name=self.usb_name)
                folder_id = usb_folder['id']
                folder_name = file.split(self.usb_name)[1].split('/')[1]
                file = file.split(self.usb_name+'/')[1]
                while '/' in file:
                    folder, search_time = self.owner.search_file_by_parent_and_name(parent_id=folder_id, name=folder_name)
                    folder_id = folder['id']
                    file = file.split(folder_name+'/')[1]
                    folder_name = file.split('/')[0]
                self.log.info("Deleting file: {}".format(file))
                file_info, search_time = self.owner.search_file_by_parent_and_name(parent_id=folder_id, name=file)
                file_id = file_info['id']
                result, timing = self.owner.delete_file(file_id)
                if result:
                    self.log.info('{} has been deleted'.format(file))
                    delete += 1
                else:
                    self.error("Delete file: {} failed!".format(file))
            time.sleep(10)

            # Check usb sync folder files status
            usb_sync_files2 = self.adb.executeShellCommand('find {0} -type f'.format(usb_path))[0]
            sync_lists = [path.split(usb_path).pop() for path in usb_sync_files2.split('\r\n')]
            sync_lists.pop()
            self.log.info('Current Sync Files: {}'.format(sync_lists))
            for item in sync_lists:
                if item in lists:
                    self.error('USB Slurp Delete Files FAILED!! {} is not DELETED!!'.format(item))
            else:
                self.log.info('There have {} files, Total Delete {} files'.format(num_file, delete))
                self.log.info('USB Slurp Delete Files Test PASSED!!')
                testcase = TestCase(name='Usb Slurp Delete Files Test', classname='BAT', elapsed_sec=time.time()-start_time)
        except Exception as ex:
            testcase = TestCase(name='Usb Slurp Delete Files Test', classname='BAT', elapsed_sec=time.time()-start_time)
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

    testrun = usbSlurpDeleteTest(adb=adb, env=env)
    testrun.run()
