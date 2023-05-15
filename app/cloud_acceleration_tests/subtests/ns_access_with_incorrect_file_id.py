# -*- coding: utf-8 -*-
""" Negative scenario: Test for Access with Incorrect File ID case. (KAM-21092).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# test case
from cloud_acceleration_tests.subtests.single_1st_access import SingleFisrtAccessTest


class AccessCacheWithIncorrectFileIDTest(SingleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Access_With_Incorrect_File_ID'

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']
        self.access_token = self.share[self.share_filed]['access_token']

    def test(self):
        incorrect_file_id = 'X' * 36 # Lenth of file ID is 40
        self.log.info('Use incorrect_file_id: {}'.format(incorrect_file_id))
        incorrect_url = self.gen_incorrect_url(incorrect_file_id, self.cache_url)
        self.log.info('Use incorrect_url: {}'.format(incorrect_url))
        resp = self.test_access(cache_url=incorrect_url, access_token=self.access_token, status_codes=[404],
            auth_by_header=self.auth_by_header)

    def gen_incorrect_url(self, file_id, cache_url):
        prefix_part, sub_string = cache_url.split('/sdk/v2/files/')
        _, post_part = sub_string.split('/', 1)
        return '{}/sdk/v2/files/{}/{}'.format(prefix_part, file_id, post_part)
