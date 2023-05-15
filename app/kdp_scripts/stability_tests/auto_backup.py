# -*- coding: utf-8 -*-
""" Test for simulate auto backup
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
import time
# platform modules
from platform_libraries.common_utils import execute_local_cmd
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.restAPI import ItemParser
# 3rd party modules
import requests


class AutoBackup(KDPTestCase):

    TEST_SUITE = 'Stability Tests'
    TEST_NAME = 'Auto backup Test'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-380'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.file_url = None
        self.local_path = None
        self.data_set = []

    def init(self):
        if self.file_url:
            self.log.info("Download files...")
            if not self.file_url.endswith('/') and '.' not in self.file_url.split('/').pop():
                self.file_url += '/'
            if not os.path.exists(self.local_path):
                os.mkdir(self.local_path)
            execute_local_cmd(
                'wget -r -nc -np -nd -R "index.html*" {} -P {}'.format(self.file_url, self.local_path),
                consoleOutput=True, timeout=60*30)
        if not os.path.exists(self.local_path):
            raise self.err.TestFailure("need data set")
        self.scan_data_set()
        self.log.info("Data set: {}".format(self.data_set))
        self.log.info("Total files: {}".format(len(self.data_set)))

    def scan_data_set(self):
        self.data_set = []
        stdout, stderr = execute_local_cmd('find {} -type f'.format(self.local_path), utf8=True)
        for path in stdout.split('\n'):
            self.append_file(os.path.normpath(path).split(os.path.sep))

    def append_file(self, splited_path):
        if not splited_path:
            return
        file_name = splited_path.pop()
        if not file_name or file_name in ['.', '..']:
            return
        self.data_set.append(file_name)

    def before_test(self):
        self.log.info("Clean UUT owner's home directory...")
        self.uut_owner.clean_user_root()

    def test(self):
        self.uut_owner.log.info("Upload files to device...")
        self.uut_owner.recursive_upload(path=self.local_path)
        self.verify_result()

    def verify_result(self):
        files_in_device = []
        # Handle root parent.
        file_list, sub_folders = self.uut_owner.walk_folder(search_parent_id='root', item_parser=ItemParser.id_and_name)
        for file in file_list:
            files_in_device.append(file['name'])
        sub_folder_ids = [sub_folder['id'] for sub_folder in sub_folders]

        # Search sub-folders from top to bottom.
        while sub_folder_ids:
            next_round_ids = []
            for folder_id in sub_folder_ids:
                file_list, sub_folders = self.uut_owner.walk_folder(search_parent_id=folder_id, item_parser=ItemParser.id_and_name)
                for file in file_list:
                    files_in_device.append(file['name'])
                next_round_ids+=[sub_folder['id'] for sub_folder in sub_folders] # Collect deeper level sub-folder IDs.
            sub_folder_ids = next_round_ids
            
        # comapre file names
        not_found_files = []
        for file_name in self.data_set:
            if file_name in files_in_device:
                files_in_device.remove(file_name)
            else:
                not_found_files.append(file_name)
        if not_found_files:
            raise self.err.TestFailure("Not found files: {}".format(not_found_files))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Auto back test for KDP ***
        """)

    parser.add_argument('-fu', '--file_url', help='Source file URL', metavar='URL')
    parser.add_argument('-lp', '--local_path', help='Local path to uplaod', metavar='PATH', default='local')

    test = AutoBackup(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
