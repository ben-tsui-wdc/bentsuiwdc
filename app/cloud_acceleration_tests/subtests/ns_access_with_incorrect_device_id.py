# -*- coding: utf-8 -*-
""" Negative scenario: Test for Access with Incorrect Device ID case. (KAM-21090).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# test case
from cloud_acceleration_tests.subtests.single_1st_access import SingleFisrtAccessTest


class AccessCacheWithIncorrectDeviceIDTest(SingleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Access_With_Incorrect_Device_ID'

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']
        self.access_token = self.share[self.share_filed]['access_token']

    def test(self):
        incorrect_device_id = 'X' * 36 # Lenth of device ID is 36
        self.log.info('Use incorrect_device_id: {}'.format(incorrect_device_id))
        incorrect_url = self.gen_incorrect_url(incorrect_device_id, self.cache_url)
        self.log.info('Use incorrect_url: {}'.format(incorrect_url))
        resp = self.test_access(cache_url=incorrect_url, access_token=self.access_token, status_codes=[400],
            auth_by_header=self.auth_by_header)

    def gen_incorrect_url(self, device_id, cache_url):
        sub_string, post_part = cache_url.split('/sdk/v2/files/')
        prefix_part, _ = sub_string.rsplit('/', 1)
        return '{}/{}/sdk/v2/files/{}'.format(prefix_part, device_id, post_part)
