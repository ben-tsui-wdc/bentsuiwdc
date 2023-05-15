# -*- coding: utf-8 -*-
""" Test for Share file and get share information case. (KAM-21258).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.decorator import STATUS_STOP, sub_task_test
# test case
from restsdk_tests.functional_tests.upload_file import UploadFileTest


class CreateShareTest(UploadFileTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Create_Share'

    def declare(self):
        self.file_name = None
        self.file_url = None
        self.check_mime_type = None
        self.cache_prefix_type = 'proxy'
        self.share_filed = 'shared_file'

    @sub_task_test(mapping=[(Exception, STATUS_STOP)], reset=True) # TODO: Move me into main script.
    def test(self):
        # Prepare test file by UploadFileTest.
        try:
            super(CreateShareTest, self).test()
        except:
            raise self.err.TestFailure('Upload test file failed')

        # Create a new public share record of test file.
        try:
            share_info = self.uut_owner.share_file_by_name(file_name=self.file_name, prefix_type=self.cache_prefix_type)
        except:
            self.log.exception('Share file by name failed.')
            raise self.err.TestFailure('Share file by name failed.')

        self.log.info('* Share Inforamtion: \n{}'.format(pformat(share_info)))

        # Save share information for the following subtests.
        perm_resp = self.uut_owner.get_permission(file_id=share_info['file_id'], entity_id=share_info['auth_id'], entity_type='cloudShare')
        share_info['file_name'] = self.file_name
        share_info['permission_id'] = perm_resp['filePerms'][0]['id']
        share_info['prefix_type'] = self.cache_prefix_type
        self.log.info('* {}: \n{}'.format(self.share_filed, pformat(share_info)))
        self.share[self.share_filed] = share_info


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Create_Share test on Kamino Android ***
        Examples: ./run.sh cloud_acceleration_tests/functional_tests/create_share.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-url', '--file_url', help='URL of test file to download from file server', metavar='URL')
    parser.add_argument('-cmt', '--check_mime_type', help='Check file mime type from API reponse if value supplied', metavar='MIMETYPE')
    parser.add_argument('-cpt', '--cache_prefix_type', help='What type of prefix arguemnt to reuqest cache URL', metavar='TYPE', default='proxy')

    test = CreateShareTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
