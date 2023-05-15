# -*- coding: utf-8 -*-
""" Test for Single Access: File permission changed from deny to access.  (KAM-21161).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# test case
from cloud_acceleration_tests.subtests.single_1st_access import SingleFisrtAccessTest


class FilePermAllowTest(SingleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'File_Perm-Not_Allow_To_Allow'

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']
        self.access_token = self.share[self.share_filed]['access_token']
        self.file_id = self.share[self.share_filed]['file_id']
        self.auth_id = self.share[self.share_filed]['auth_id']
        if self.share[self.share_filed].get('permission_id'):
            raise self.err.StopTest('File permission still existing')

    def test(self):
        # Set test file permission
        self.uut_owner.set_permission(self.file_id, user_id=self.auth_id, entity_type='cloudShare', permission='ReadFile')
        # Update cache record 
        perm_resp = self.uut_owner.get_permission(file_id=self.file_id, entity_id=self.auth_id, entity_type='cloudShare')
        self.share[self.share_filed]['status'] = 'caching'
        self.share[self.share_filed]['permission_id'] = perm_resp['filePerms'][0]['id']
        # Start single access
        resp = self.test_access(cache_url=self.cache_url, access_token=self.access_token, status_codes=[200, 303],
            close_after_ckeck=True, auth_by_header=self.auth_by_header) # We don't check content, so close it for performance.
