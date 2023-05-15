# -*- coding: utf-8 -*-
""" Test for API: POST /v2/files/id/copy (KAM-16650).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class FileCopyFromUsbTest(KDPTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'File Copy From USB'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-858,KDP-862'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.file_name = None
        self.verify_by_any_file = True
        self.mount_path = '/mnt/USB'

    def before_test(self):
        self.log.info("Clean UUT owner's home directory in before_test()...")
        self.uut_owner.clean_user_root()

        # Use existed file
        if self.verify_by_any_file:

            self.log.info("Get files of USB disk.")
            stdout, stderr = self.ssh_client.execute_cmd('ls {}'.format(self.mount_path))
            self.usb_mount_name = stdout.strip()
            if not self.usb_mount_name:
                raise self.err.StopTest("USB is not Mounted!!!")

            # find /mnt/USB/USB1_a1/* -type f  -maxdepth 2
            stdout, stderr = self.ssh_client.execute_cmd('find {}/{}/* -type f -maxdepth 0'.format(self.mount_path, self.usb_mount_name))
            files = stdout.split('\n')
            file_names = [f.split('/').pop() for f in files]
            # Filter out hidden files.
            filtered_file_names = [fn for fn in file_names if fn and not fn.startswith('.') and "$" not in fn]
            if not filtered_file_names:
                raise self.err.StopTest('USB disk is empty')
            self.file_name = filtered_file_names.pop()
            self.log.info("Choose file: {}".format(self.file_name))
            
    def test(self):
        self.uut_owner.usb_slurp()
        self.verify_result()

    def after_test(self):
        self.log.info("Clean UUT owner's home directory in after_test() ...")
        self.uut_owner.clean_user_root()

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
    parser = KDPInputArgumentParser("""\
        *** File_Copy_From_USB test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/file_copy.py --uut_ip 10.136.137.159\
        """)

    parser.add_argument('-vbaf', '--verify_by_any_file', help='Verify USB copy by any file', action='store_true', default=True)

    test = FileCopyFromUsbTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
