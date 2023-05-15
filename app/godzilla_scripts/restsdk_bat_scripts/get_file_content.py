# -*- coding: utf-8 -*-
""" Test for API: GET /v2/files/id/content (KAM-16647).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from platform_libraries.compare import local_md5sum, md5sum
# test case
from godzilla_scripts.restsdk_bat_scripts.get_data_by_id import GetDataByIDTest


class GetFileContentTest(GetDataByIDTest):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Get File Content'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1754'
    PRIORITY = 'Blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.file_id = None # Use file_id or file_name to get file
        self.file_name = None
        self.file_size = None # Verify file content by file size if it is supplied.
        self.source_file = None # Verify file content by md5sum if it is supplied.
        self.parent_id = None # Use parent_id or parent_name to set parent ID
        self.parent_name = None

    def init(self):
        if not self.file_name and not self.file_id:
            raise self.err.StopTest('Need file_name or file_id')

    def before_test(self):
        if self.file_id:
            return
        self.parent_id = self.get_parent_id()
        self.file_id = self.get_data_id(name=self.file_name, parent_id=self.parent_id)

    def test(self):
        content = self.uut_owner.get_file_content_v3(file_id=self.file_id).content
        self.verify_result(content)

    def verify_result(self, content):
        content_size = len(content)
        self.log.info('Content size: {}'.format(content_size))

        if not self.file_size is None:
            if self.file_size != content_size:
                self.log.info('Verify content size: FAILED.')
                raise self.err.TestFailure('Content size is incorrect.')
            self.log.info('Verify content size: PASSED.')

        if self.source_file:
            remote_md5 = md5sum(content)
            self.log.info('MD5 of remote file: {}'.format(remote_md5))
            source_md5 = local_md5sum(self.source_file)
            self.log.info('MD5 of source file: {}'.format(source_md5))

            if remote_md5 != source_md5:
                self.log.info('Verify md5sum: FAILED.')
                raise self.err.TestFailure('Content md5sum is incorrect.')
            self.log.info('Verify md5sum: PASSED.')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** GET_File_Content test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/get_file_content.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-fid', '--file_id', help='Get remote file by file ID', metavar='ID')
    parser.add_argument('-fn', '--file_name', help='Get remote file by file Name', metavar='NAME')
    parser.add_argument('-fs', '--file_size', help='Verify remote file with file size', metavar='NUMBER', type=int)
    parser.add_argument('-sf', '--source_file', help='Verify remote file with local file by md5sim', metavar='NAME')
    parser.add_argument('-pid', '--parent_id', help='ID of parent folder', metavar='ID')
    parser.add_argument('-pname', '--parent_name', help='Name of parent folder', metavar='Name')


    test = GetFileContentTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
