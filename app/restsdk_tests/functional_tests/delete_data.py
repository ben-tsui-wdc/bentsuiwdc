# -*- coding: utf-8 -*-
""" Test for API: DEL /v2/files (KAM-16646).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
# test case
from restsdk_tests.functional_tests.get_data_by_id import GetDataByIDTest
# 3rd party modules
import requests


class DeleteDataTest(GetDataByIDTest):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Delete Data'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-16646'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def test(self):
        success, elapsed = self.uut_owner.delete_file(data_id=self.data_id)
        self.verify_result()

    def verify_result(self):
        try: # Expect data not found.
            self.uut_owner.get_data_by_id(data_id=self.data_id)
            self.log.info('Data has been deleted: FAILED.')
            raise self.err.TestFailure('Delete data failed.')
        except requests.HTTPError, e:
            if 404 != e.response.status_code:
                raise
            self.log.info('Data has been deleted: PASSED.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** DELTET_DATA test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/delete_data.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-did', '--data_id', help='Delete data by file/folder ID', metavar='ID')
    parser.add_argument('-dname', '--data_name', help='Delete data by file/folder Name', metavar='NAME')
    parser.add_argument('-pid', '--parent_id', help='ID of parent folder', metavar='ID')
    parser.add_argument('-pname', '--parent_name', help='Name of parent folder', metavar='Name')

    test = DeleteDataTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
