# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

import sys
import os
import time
import requests
import json
import argparse
import random
import numpy
import math

from datetime import timedelta

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.compare import compare_images
from platform_libraries.pyutils import save_to_file

class USBSlurpSyncStress(TestCase):

    TEST_SUITE = 'USB_Slurp_Tests'
    TEST_NAME = 'USB_Slurp_Data_Integrity_And_Performance_Test'
    # Popcorn
    TEST_JIRA_ID = 'KAM-10019'
    REPORT_NAME = 'Stress'

    def declare(self):
        self.disable_barrier = False

    def init(self):
        self.product = self.adb.getModel()
        self.root_folder = '/data/wd/diskVolume0/restsdk/userRoots/'
        self.mount_path = '/mnt/media_rw/'
        self.search_file_number = 200
        self.random_choice_num = 500

    def _get_usb_name(self):
        self.usb_mount = self.adb.executeShellCommand('ls {}'.format(self.mount_path))[0].strip()
        if not self.usb_mount:
            raise self.err.TestFailure("USB is not Mounted!!!".format(file))
        usb_info = self.uut_owner.get_usb_info()
        self.usb_id = usb_info.get('id')
        self.usb_name = usb_info.get('name')
        self.log.info('USB Name is: {}'.format(self.usb_name))

    def _get_usb_files_checksum_list(self):
        self.chk_dic = {}
        usb_files = self.adb.executeShellCommand('ls {0}{1}'.format(self.mount_path, self.usb_mount),
                                                 consoleOutput=False)[0]
        lists = usb_files.split()
        self.log.warning(lists)
        for item in lists:
            if any(char.isdigit() for char in item):
                xxx = self.adb.executeShellCommand('busybox md5sum {0}{1}/{2}'
                                                      .format(self.mount_path, self.usb_mount, item),
                                                      consoleOutput=False)[0]
                self.log.warning(xxx)
                md5sum = self.adb.executeShellCommand('busybox md5sum {0}{1}/{2}'
                                                      .format(self.mount_path, self.usb_mount, item),
                                                      consoleOutput=False)[0].split()[0]
                self.chk_dic.update({item: md5sum})
        self.file_list = []
        for key, value in self.chk_dic.iteritems():
            aKey = key
            self.file_list.append(aKey)
        self.log.debug('File_list: {}'.format(self.file_list))

    def before_loop(self):
        self._get_usb_name()
        self._get_usb_files_checksum_list()

        if self.disable_barrier:
            self.log.warning("Try to close the barrier due to Jira ticket: KAM200-605")
            self.adb.executeShellCommand('mount -o remount,barrier=0 /data/wd/diskVolume0', consoleOutput=True)

    def before_test(self):
        pass

    def test(self):

        def _md5_checksum(user_id, file_name):
            usb_name = self.usb_name.replace(' ', '\ ')
            path = os.path.join(self.root_folder, user_id, usb_name, file_name)
            result = self.adb.executeShellCommand('busybox md5sum {}'.format(path), consoleOutput=False, timeout=180)
            self.log.debug(result)
            result = result[0].strip().split()[0]
            return result

        # Trigger usb slurp
        user_id = self.uut_owner.get_user_id(escape=True)
        self.uut_owner.usb_slurp(timeout=3600*3)
        usb_folder, search_time = self.uut_owner.search_file_by_parent_and_name(parent_id='root', name=self.usb_name)
        usb_folder_id = usb_folder['id']

        # Delete 30% of files randomly and measure time
        delete_file_num = int(math.ceil(len(self.file_list) * 0.3))
        delete_file_list = random.sample(self.file_list, delete_file_num)
        self.log.info("Delete file list:{}".format(delete_file_list))

        delete_time_list = []
        for file in delete_file_list:
            self.log.info("Deleting file: {}".format(file))
            file_info, search_time = self.uut_owner.search_file_by_parent_and_name(parent_id=usb_folder_id, name=file)
            file_id = file_info['id']
            result, times = self.uut_owner.delete_file(file_id)
            if result:
                delete_time_list.append(timedelta.total_seconds(times))
            else:
                raise self.err.TestFailure("Delete file: {} failed!".format(file))

        average_delete_time = numpy.mean(delete_time_list)
        self.log.info('Average delete file time: {} secs'.format(average_delete_time))
        time.sleep(10)

        # Start USB Slurp sync to replace missing files
        copy_id, usb_info, resp = self.uut_owner.usb_slurp(timeout=3600*3)
        usb_slurp_elapsed_time = resp['elapsedDuration']
        self.log.info('USB slurp elapsed time: {} secs'.format(usb_slurp_elapsed_time))

        # Check data integrity for 70% existed files and 30% replaced files (Random choose 1000 photos)
        existed_file_list = set(self.file_list) - set(delete_file_list)
        self.log.info('Deleted_file_list: {}'.format(delete_file_list))
        self.log.info('Existed_file_list: {}'.format(existed_file_list))
        if len(delete_file_list) < self.random_choice_num:
            random_choice_number = len(delete_file_list)
        else:
            random_choice_number = self.random_choice_num

        random_choice_existed_list = random.sample(existed_file_list, random_choice_number)
        random_choice_delete_list = random.sample(delete_file_list, random_choice_number)
        existed_files_pass = 0
        existed_files_fail = 0
        delete_files_pass = 0
        delete_files_fail = 0
        for item in random_choice_existed_list:
            chksum = _md5_checksum(user_id, item)
            text_chksum = self.chk_dic[item]
            self.log.info('{} - chksum:{}, text_chksum:{}'.format(item, chksum, text_chksum))
            if chksum == text_chksum:
                existed_files_pass += 1
            else:
                existed_files_fail += 1
        for item in random_choice_delete_list:
            chksum = _md5_checksum(user_id, item)
            text_chksum = self.chk_dic[item]
            self.log.info('{} - chksum:{}, text_chksum:{}'.format(item, chksum, text_chksum))
            if chksum == text_chksum:
                delete_files_pass += 1
            else:
                delete_files_fail += 1

        # Search and Browsing 100 Photos and measure time
        if len(self.file_list) < self.search_file_number:
            search_files = len(self.file_list)
        else:
            search_files = self.search_file_number

        search_file_list = random.sample(self.file_list, search_files)
        self.log.info("Search file list:{}".format(search_file_list))

        search_time_list = []
        for file in search_file_list:
            usb_data_info, search_time = self.uut_owner.search_file_by_parent_and_name(parent_id=usb_folder_id, name=file)
            search_time_list.append(timedelta.total_seconds(search_time))

        average_search_time = numpy.mean(search_time_list)

        self.log.info('EXIST_FILES_PASSED: {}'.format(existed_files_pass))
        self.log.info('EXIST_FILES_FAILED: {}'.format(existed_files_fail))
        self.log.info('DELETE_FILES_PASSED: {}'.format(delete_files_pass))
        self.log.info('DELETE_FILES_FAILED: {}'.format(delete_files_fail))
        self.log.info('Average search file time: {} secs'.format(average_search_time))
        self.log.info('USB slurp elapsed time: {} secs'.format(usb_slurp_elapsed_time))
        self.log.info('Average delete file time: {} secs'.format(average_delete_time))

        build_itr = self.env.UUT_firmware_version + "_itr_%02d" % (self.env.iteration,)

        self.data.test_result['iteration'] = build_itr
        self.data.test_result['delete_file_elapsed_time'] = average_delete_time
        self.data.test_result['usb_copy_elapsed_time'] = usb_slurp_elapsed_time
        self.data.test_result['data_search_time'] = average_search_time
        self.data.test_result['data_integrity_passed_existed_files'] = existed_files_pass
        self.data.test_result['data_integrity_failed_existed_files'] = existed_files_fail
        self.data.test_result['data_integrity_passed_new_copied_files_'] = delete_files_pass
        self.data.test_result['data_integrity_failed_new_copied_files_'] = delete_files_fail

    def after_test(self):
        pass

    def after_loop(self):
        pass

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** USB Slurp sync stress test on Kamino Android ***
        """)
    parser.add_argument('--disable_barrier', '-ds', action='store_true', default=False, help='disable the barrier in test device')
    test = USBSlurpSyncStress(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)