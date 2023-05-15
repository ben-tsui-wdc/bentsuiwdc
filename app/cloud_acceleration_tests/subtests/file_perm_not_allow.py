# -*- coding: utf-8 -*-
""" Test for Single Access: File permission changed to access deny case. (KAM-21160).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# test case
from cloud_acceleration_tests.subtests.single_1st_access import SingleFisrtAccessTest


class FilePermNotAllowTest(SingleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'File_Perm-Allow_To_Not_Allow'

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']
        self.access_token = self.share[self.share_filed]['access_token']
        if not self.share[self.share_filed]['permission_id']:
            raise self.err.StopTest('No permission_id in share')
        self.permission_id = self.share[self.share_filed]['permission_id']

    def test(self):
        # Delete test file permission
        self.uut_owner.delete_permission(permission_id=self.permission_id)
        # Update cache record 
        self.share[self.share_filed]['permission_id'] = None
        # Start single access
        resp = self.test_access(cache_url=self.cache_url, access_token=self.access_token, status_codes=[404],
            auth_by_header=self.auth_by_header)
