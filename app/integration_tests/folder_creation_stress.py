# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import os
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from datetime import datetime

class StressFolderCreation(TestCase):

    TEST_SUITE = 'Sharing_Stress_Tests'
    TEST_NAME = 'Stress_Create_Folders'
    # Popcorn
    TEST_JIRA_ID = 'KAM-10971'
    REPORT_NAME = 'Stress'

    def init(self):
        self.home_name = 'Family'
        self.home_id = None

        try:
            home_folder = self.uut_owner.search_file_by_parent_and_name(self.home_name)
            self.home_id = home_folder[0].get('id')
            self.log.debug("Owner's home ID: {}".format(self.home_id))
        except Exception as e:
            self.log.warning("Cannot find the owner's home, response:{}. It's a normal case.".format(repr(e)))

        self.product = self.adb.getModel()
        self.build = ''
        # Test info
        self.root_folder = '/data/wd/diskVolume0/restsdk/userRoots/'
        self.file_name = 'test_file.jpg'
        self.file_size = '1024'  # 1 KB

    def before_loop(self):
        self.log.info('Preparing test file: {}'.format(self.file_name))
        try:
            with open(self.file_name, 'wb') as f:
                f.write(os.urandom(int(self.file_size)))
        except Exception as e:
            self.log.error('Failed to create file: {0}, error message: {1}'.format(self.file_name, repr(e)))
            raise

    def before_test(self):
        pass

    def test(self):

        self.build = self.adb.getFirmwareVersion()
        init_time = datetime.now()

        self.log.info('=== Step 1: Owner creates {} folders on NAS directory ===\n'.format(self.folder_number))
        for folder_num in range(int(self.folder_number)):
            folder_name = 'test{}'.format(folder_num)
            self.log.debug('Creating folder: {}'.format(folder_name))
            self.uut_owner.commit_folder(folder_name)

        folder_create_time = (datetime.now() - init_time).seconds
        self.log.info('Folder create elapsed time: {} secs'.format(folder_create_time))

        # Default data search is 1000 data per page
        total_page = int(self.folder_number) / 1000
        folder_id_list = {}
        page_token = ''
        for i in range(int(total_page) + 1):
            folder_id, page_token = self.uut_owner.get_data_id_list(page_token=page_token)
            folder_id_list.update(folder_id)

        if self.home_id:
            folder_id_list.pop(self.home_name, None)
            self.log.info('Found {} folder and remove it from test folder list'.format(self.home_name))

        init_time = datetime.now()
        self.log.info('=== Step 2: Owner upload files to each of the {} folders created ===\n'.format(self.folder_number))
        with open(self.file_name, 'rb') as f:
            folder_num = 0
            for folder_name, folder_id in folder_id_list.iteritems():
                self.log.debug('Uploading test file into test folder {0}'.format(folder_name))
                self.uut_owner.chuck_upload_file(file_object=f, file_name=self.file_name, parent_id=folder_id)
                folder_num += 1
                # self.log.debug('Already upload {} files'.format(folder_num))

        file_upload_time = (datetime.now() - init_time).seconds
        self.log.info('File upload elapsed time: {} secs'.format(file_upload_time))

        self.log.info('=== Step 3: Owner delete all the {} folders ===\n'.format(self.folder_number))
        init_time = datetime.now()
        for folder_id in folder_id_list.values():
            self.uut_owner.delete_file(data_id=folder_id)

        folder_delete_time = (datetime.now() - init_time).seconds
        self.log.info('Delete folder elapsed time: {} secs'.format(folder_delete_time))

        if not self.env.dry_run:
            self.log.info('=== Step 4: Upload report to logstash server ===\n')
            
        build_itr = self.env.UUT_firmware_version + "_itr_%02d" % (self.env.iteration,)
        self.log.warning("Test {} complete.".format(build_itr))
        self.data.test_result['build_itr'] = build_itr
        self.data.test_result['folder_create_number'] = int(self.folder_number)
        self.data.test_result['folder_create_elapsed_time'] = folder_create_time
        self.data.test_result['file_upload_elapsed_time'] = file_upload_time
        self.data.test_result['folder_delete_elapsed_time'] = folder_delete_time

        self.log.info("Add 3 mins interval to ensure the folders are fully deleted")
        time.sleep(60 * 3)
        self.log.info("Already wait for 3 mins")

    def after_test(self):
        pass

    def after_loop(self):
        self.log.info("Delete local test file")
        if os.path.isfile(self.file_name):
            os.remove(self.file_name)

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Stress Test for folder creation on Kamino Android ***\
        """)
    parser.add_argument('--folder_number', help='Create folder numbers', default='2800')
    test = StressFolderCreation(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)