# -*- coding: utf-8 -*-
""" Test for API: DELETE /v2/files/id/copy (KAM-19920).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
# 3rd party modules
import requests


class AbortFileCopyTest(TestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Abort File Copy'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-19920'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def before_test(self):
        self.log.info("Clean UUT owner's home directory...")
        self.uut_owner.clean_user_root()
        self.copy_id, usb_info, resp = self.uut_owner.usb_slurp(wait_until_done=False)

    def test(self):
        self.uut_owner.delete_file_copy(copy_id=self.copy_id)
        self.verify_result()

    def verify_result(self):
        try:
            response = self.uut_owner.get_file_copy(copy_id=self.copy_id)
            if response['status'] == 'aborting' or response['status'] == 'aborted':
                self.log.info('Abort file copy: PASSED.')
                return
            self.log.info('Abort file copy: FAILED.')
            raise self.err.TestFailure('Abort file copy failed.')
        except requests.HTTPError, e:
            if 404 != e.response.status_code:
                raise
            self.log.info('Abort file copy: PASSED.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Abort_File_Copy test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/abort_file_copy.py --uut_ip 10.136.137.159\
        """)

    test = AbortFileCopyTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
