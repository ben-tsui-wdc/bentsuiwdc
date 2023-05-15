# -*- coding: utf-8 -*-
""" Test for Access Modified File case. (KAM-21158).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# platform modules
from platform_libraries.constants import Kamino
# test case
from cloud_acceleration_tests.subtests.single_2nd_access import SingleSecondAccessTest


class AccessModifiedFileTest(SingleSecondAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Access_Modified_File'

    def declare(self):
        self.auth_by_header = True
        self.share_filed = 'shared_file'
        self.text_to_append = 'X'

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']
        self.access_token = self.share[self.share_filed]['access_token']
        self.file_name = self.share[self.share_filed]['file_name']
        self.owner_id = self.share[self.share_filed]['owner_id']
        self.file_nas_path = '{}{}/{}'.format(Kamino.USER_ROOT_PATH, self.owner_id.replace('|', '\|'), self.file_name)

    def test(self):
        # Modify test file.
        self.adb.executeShellCommand(cmd='echo {} >> {}'.format(self.text_to_append, self.file_nas_path))
        # Start single access.
        resp = self.test_access(cache_url=self.cache_url, access_token=self.access_token, status_codes=[200],
            close_after_ckeck=True, auth_by_header=self.auth_by_header) # We don't check content, so close it for performance.
        # Update cache record 
        self.share[self.share_filed]['status'] = 'caching'
        self.verify_etag(comp_etag=self.share[self.share_filed]['etag'], cache_url=self.cache_url, access_token=self.access_token, share_filed=self.share_filed)
        # Update cache record 
        self.share[self.share_filed]['status'] = 'cached'

    def verify_etag(self, comp_etag, cache_url, access_token, share_filed, wait_time=None, auth_by_header=True):
        # Send request and verify content.
        self.test_single_2nd_access(cache_url, access_token, share_filed, wait_time, auth_by_header=auth_by_header)
        resp = self.test_access_redirect_url(self.share[share_filed]['redirect_url'], share_filed)
        # Compare Etag
        new_etag = self.share[share_filed]['etag']
        self.log.info('* ETag before modified: {}'.format(comp_etag))
        self.log.info('* ETag from cache: {}'.format(new_etag))
        if comp_etag == new_etag:
            raise self.err.TestFailure('ETAG is not change')
        resp.close() # We don't check content, so close it for performance.
