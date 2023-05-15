# -*- coding: utf-8 -*-
""" Test for Delete Cache Resource case (KAM-21150).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# platform modules
from middleware.sub_test import SubTest


class DeleteCacheTest(SubTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Delete_Cache'

    def declare(self):
        self.auth_by_header = True
        self.share_filed = 'shared_file'

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']
        self.access_token = self.share[self.share_filed]['access_token']

    def test(self):
        resp = self.uut_owner.delete_content_from_cache(cache_url=self.cache_url, access_token=self.access_token,
            auth_by_header=self.auth_by_header)
        self.log.info('* Status Code: {}'.format(resp.status_code))

        # Update cache record 
        self.share[self.share_filed]['status'] = None
