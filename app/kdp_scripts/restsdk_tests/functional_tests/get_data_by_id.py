# -*- coding: utf-8 -*-
""" Test for API: GET /v2/files/id (KAM-18159).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class GetDataByIDTest(KDPTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Get Data By ID'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-1020'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }

    def declare(self):
        self.data_id = None # Use data_id or data_name to get data info
        self.data_name = None
        self.parent_id = None # Use parent_id or parent_name to set parent ID
        self.parent_name = None

    def init(self):
        if not any([self.data_id, self.data_name]):
            raise self.err.StopTest('Need data_id or data_name')

    def before_test(self):
        if self.data_id:
            return
        self.parent_id = self.get_parent_id()
        self.data_id = self.get_data_id(name=self.data_name, parent_id=self.parent_id)

    def get_parent_id(self):
        if self.parent_id:
            return self.parent_id
        elif self.parent_name:
            try:
                self.log.info('Get parent ID by search name...')
                folder, elapsed = self.uut_owner.search_file_by_parent_and_name(name=self.parent_name)
                return folder['id']
            except:
                raise
        else:
            return 'root'

    def get_data_id(self, name, parent_id):
        item, elapsed = self.uut_owner.search_file_by_parent_and_name(name, parent_id)
        return item['id']

    def test(self):
        data = self.uut_owner.get_data_by_id(data_id=self.data_id)
        self.log.info('API Response: {}'.format(pformat(data)))
        # Test passed if it response HTTP status code 200


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get_Data_By_ID test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/get_data_by_id.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-did', '--data_id', help='Get data info by file/folder ID', metavar='ID')
    parser.add_argument('-dname', '--data_name', help='Get data info by file/folder Name', metavar='NAME')
    parser.add_argument('-pid', '--parent_id', help='ID of parent folder', metavar='ID')
    parser.add_argument('-pname', '--parent_name', help='Name of parent folder', metavar='Name')

    test = GetDataByIDTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
