# -*- coding: utf-8 -*-
""" Test for API: POST /v2/files/id/copy (KAM-16650).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class FileCopyFromUsbTest(TestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'File Copy From USB'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-16650'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.file_name = '1K.data'
        self.file_size = 1024
        self.do_clean_usb = False
        self.existed_file_name = None
        self.verify_by_any_file = False

    def before_test(self):
        self.log.info('whoami: {}'.format(self.adb.whoami())) # for debug
        self.log.info("Clean UUT owner's home directory...")
        self.uut_owner.clean_user_root()

        # Use existed file and specify name
        if self.existed_file_name:
            self.file_name = self.existed_file_name
            return

        # Use existed file
        if self.verify_by_any_file:
            files = self.uut_owner.get_files_of_usb(adb_inst=self.adb, max_depth=2)
            file_names = [f.split('/').pop() for f in files]
            # Filter out hidden files.
            filtered_file_names = [fn for fn in file_names if fn and not fn.startswith('.')]
            if not filtered_file_names:
                raise self.err.TestFailure('USB disk is empty')
            self.file_name = filtered_file_names.pop()
            self.log.info("Choose file: {}".format(self.file_name))
            return

        # Create test file
        if self.do_clean_usb:
            self.log.info("Clean USB disk...")
            self.uut_owner.clean_usb_by_rm(adb_inst=self.adb)
        self.log.info("Create data...")
        success = self.uut_owner.gen_file_to_usb(adb_inst=self.adb, name=self.file_name, size=self.file_size)
        if not success:
            raise self.err.TestFailure('Create random file failed.')

    def test(self):
        self.uut_owner.usb_slurp()
        self.verify_result()

    def verify_result(self):
        parent_id = self._verify_usb_folder()
        self._verify_file(self.file_name, parent_id)
        self.record_pass()

    def _verify_usb_folder(self):
        usb_info = self.uut_owner.get_usb_info()
        usb_folder = usb_info['name']
        try:
            folder, elapsed = self.uut_owner.search_file_by_parent_and_name(name=usb_folder)
            self.log.info('Check USB folder: PASSED')
            return folder['id']
        except:
            self.log.error('Check USB folder: FAILED')
            raise

    def _verify_file(self, name, parent_id):
        try:
            file, elapsed = self.uut_owner.search_file_by_parent_and_name(name, parent_id)
            self.log.info('Check file: PASSED')
            return file['id']
        except:
            self.log.error('Check file: FAILED')
            raise

    def record_pass(self):
        """ Workaround way to create multiple test case report (Get_File_Copy). """
        self.share[self.TEST_NAME] = True
        self.log.info('self.share: {}'.format(self.share))


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** File_Copy_From_USB test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/file_copy.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-dcu', '--do_clean_usb', help='Clean USB disk before run test', action='store_true', default=False)
    parser.add_argument('-efn', '--existed_file_name', help='Existed file name in USB disk, replacing to create new one', metavar='NAME')
    parser.add_argument('-vbaf', '--verify_by_any_file', help='Verify USB copy by any file', action='store_true', default=False)

    test = FileCopyFromUsbTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
