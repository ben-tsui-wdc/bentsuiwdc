# -*- coding: utf-8 -*-
""" Test for API: POST /v2/files (KAM-16645).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class UploadDataTest(TestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Upload Data'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-16645'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def declare(self):
        # Set default attributes
        self.file_name = None
        self.random_file_name = '1K.data'
        self.random_file_size = 1024
        self.overwrite_file = False
        self.parent_name = None
        self.do_create_file = False
        if self.parent_name == 'root':
            self.parent_name = None

    def init(self):
        # Handle arguments
        if not any([self.file_name, self.random_file_name, self.parent_name]):
            raise self.err.StopTest('Need file_name or or random_file_name, parent_name')
        # Need to create file?
        if not self.file_name and self.random_file_name:
            self.do_create_file = True
        # Use random_file_name if it need to create file.
        if self.do_create_file:
            self.file_name = self.random_file_name

    def before_test(self):
        # Delete remote data
        try:
            if self.parent_name:
                self.uut_owner.delete_file_by_name(name=self.parent_name)
            else:
                self.uut_owner.delete_file_by_name(name=self.file_name)
        except Exception, e:
            if '404' in str(e):
                self.log.info('Since data not found, nothing can be deleted.')
            else:
                raise

        if self.do_create_file:
            if not self.overwrite_file:
                if os.path.isfile(self.file_name):
                    return
            self.create_random_file(file_name=self.file_name, file_size=self.random_file_size)

    def create_random_file(self, file_name, local_path='', file_size=1024):
        # TODO: Move me to library.
        self.log.info("Creating file: {}...".format(file_name))
        with open(os.path.join(local_path, file_name), 'wb') as f:
            f.write(os.urandom(file_size))

    def test(self):
        if self.parent_name: self.upload_folder_test()
        if self.file_name: self.upload_file_test()

    def upload_folder_test(self):
        self.log.info("Uploading folder(name={}) to home directory...".format(self.parent_name))
        self.uut_owner.upload_data(data_name=self.parent_name)
        self.log.info('Checking folder exist or not...')
        try:
            folder, elapsed = self.uut_owner.search_file_by_parent_and_name(name=self.parent_name)
            self.parent_id = folder['id']
            self.log.info('Check Folder: PASSED')
        except:
            self.log.error('Check Folder: FAILED')
            raise

    def upload_file_test(self):
        with open(self.file_name, 'rb') as f:
            if self.parent_name:
                self.log.info('Uploading file(name={0}) to folder(name={1})...'.format(self.file_name, self.parent_name))
                self.uut_owner.upload_data(data_name=self.file_name, file_content=f.read(), parent_folder=self.parent_name)
            else:
                self.log.info('Uploading file(name={0}) to home directory...'.format(self.file_name))
                self.uut_owner.upload_data(data_name=self.file_name, file_content=f.read())
        try:
            self.log.info('Checking file exist or not...')
            parent_id = self.parent_id if hasattr(self, 'parent_id') else 'root'
            self.uut_owner.search_file_by_parent_and_name(name=self.file_name, parent_id=parent_id)
            self.log.info('Check file: PASSED')
        except:
            self.log.error('Check file: FAILED')
            raise
        # Do data comparison by get_file_content() test.


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Upload_Data test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/upload_data.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-fname', '--file_name', help='Name of upload file', metavar='NAME')
    parser.add_argument('-rfname', '--random_file_name', help='Random file name which be create for uploading', metavar='NAME')
    parser.add_argument('-rfsize', '--random_file_size', help='Size of random file', metavar='NUMBER', type=int, default='1024')
    parser.add_argument('-overwrite', '--overwrite_file', help='Overwrite local file', action='store_true')
    parser.add_argument('-pname', '--parent_name', help='Name of parent folder', metavar='NAME', default='')

    test = UploadDataTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
