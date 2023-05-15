# -*- coding: utf-8 -*-
""" Test for API: GET   /v1/fileCopies/id (KAM-16651).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# platform modules
from middleware.test_case import TestCase


class GetFileCopyTest(TestCase):
    """ Base on File_Copy_From_USB test.

    Not support single run.
    """

    TEST_SUITE = 'RESTSDK_Functional_Tests'
    TEST_NAME = 'Get File Copy'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-862'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.case_name_to_check = 'File Copy From USB'

    def test(self):
        if self.share.get(self.case_name_to_check):
            self.log.info('Base on {}: PASSED'.format(self.case_name_to_check))
        else:
            self.log.error('Base on {}: FAILED'.format(self.case_name_to_check))
            raise self.err.TestFailure('Test failed.')
