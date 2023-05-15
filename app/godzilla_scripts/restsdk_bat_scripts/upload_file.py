# -*- coding: utf-8 -*-
""" Test for API: POST /v2/files (KAM-19803, KAM-19804, KAM-19805).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
from pprint import pformat
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.common_utils import execute_local_cmd


class UploadFileTest(GodzillaTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Upload File'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1738'
    PRIORITY = 'Blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.file_name = None
        self.file_url = None
        self.check_mime_type = None

    def init(self):
        if not self.file_url and not self.file_name: raise self.err.StopTest('Need file_url or file_name')
        if not self.file_name:
            self.file_name = self.file_url.rsplit('/', 1).pop()

    def before_test(self):
        # Delete remote data
        try:
            self.uut_owner.delete_file_by_name(name=self.file_name)
        except Exception, e:
            if '404' in str(e):
                self.log.info('Since data not found, nothing can be deleted.')
            else:
                raise

        # Download photo from file server
        if self.file_url:
            cmd = 'wget "{}"'.format(self.file_url)
            print(cmd)
            execute_local_cmd(cmd=cmd, consoleOutput=True, timeout=60 * 30)

    def test(self):
        self.upload_file_test()
        self.verify_result()

    def upload_file_test(self):
        with open(self.file_name, 'rb') as f:
            self.log.info('Uploading file(name={0}) to home directory...'.format(self.file_name))
            self.uut_owner.upload_data(data_name=self.file_name, file_content=f.read())

    def verify_result(self):
        # Check file exist or not
        try:
            self.log.info('Checking file exist or not...')
            file, _ = self.uut_owner.search_file_by_parent_and_name(name=self.file_name)
            self.log.info('File info: \n{}'.format(pformat(file)))
            self.log.info('* Check file: PASSED')
        except:
            self.log.error('* Check file: FAILED')
            raise self.err.TestFailure('File not found.')

        # Check file size
        file_size = os.path.getsize(self.file_name)
        self.log.info('Local file size: {}'.format(file_size))
        if file.get('size') == file_size:
            self.log.info('* Check file size: PASSED')
        else:
            self.log.error('* Check file size: FAILED')
            raise self.err.TestFailure('File size is incorrect.')

        # Cehck file MIME type
        if self.check_mime_type:
            self.log.info('Expect MIME type: {}'.format(self.check_mime_type))
            if file.get('mimeType') == self.check_mime_type:
                self.log.info('* Check MIME type: PASSED')
            else:
                self.log.error('* Check MIME type: FAILED')
                raise self.err.TestFailure('File MIME type is incorrect.')

    def after_test(self):
        # Clean temporal file.
        if os.path.exists(self.file_name):
            self.log.info('Clean local file: {}'.format(self.file_name))
            os.remove(self.file_name)


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Upload_File test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/upload_file.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-url', '--file_url', help='URL of test file to download from file server', metavar='URL')
    parser.add_argument('-fn', '--file_name', help='Local file to upload', metavar='URL')
    parser.add_argument('-cmt', '--check_mime_type', help='Check file mime type from API reponse if value supplied', metavar='MIMETYPE')

    test = UploadFileTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
