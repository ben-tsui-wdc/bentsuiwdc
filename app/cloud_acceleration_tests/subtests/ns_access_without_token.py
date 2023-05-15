# -*- coding: utf-8 -*-
""" Negative scenario: Test for Access Without Authorization header case. (KAM-21093).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# platform modules
from middleware.sub_test import SubTest


class AccessCacheWithoutTokenTest(SubTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Access_Without_Token'

    def declare(self):
        self.share_filed = 'shared_file'

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']

    def test(self):
        resp = self.uut_owner.send_request(
            method='GET',
            url=self.cache_url,
            allow_redirects=False,
            stream=True
        )
        self.log.info('* Status Code: {}'.format(resp.status_code))

        if resp.status_code != 401:
            self.log.error('Status Code should be 401, but it is {}'.format(resp.status_code))
            self.uut_owner.log_response(response=resp, logger=self.log.error)
            raise self.err.TestFailure('API reponse is not expected')
