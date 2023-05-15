# -*- coding: utf-8 -*-
""" Test for Multiple Access: File permission changed from deny to access. (KAM-21162).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# test case
from cloud_acceleration_tests.subtests.multiple_1st_access import MultipleFisrtAccessTest
from cloud_acceleration_tests.subtests.file_perm_allow import FilePermAllowTest


class MultipleFilePermAllowTest(FilePermAllowTest, MultipleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Multiple: File_Perm-Not_Allow_To_Allow'

    def test(self):
        # Set test file permission
        self.uut_owner.set_permission(self.file_id, user_id=self.auth_id, entity_type='cloudShare', permission='ReadFile')
        # Update cache record 
        perm_resp = self.uut_owner.get_permission(file_id=self.file_id, entity_id=self.auth_id, entity_type='cloudShare')
        self.share[self.share_filed]['status'] = 'caching'
        self.share[self.share_filed]['permission_id'] = perm_resp['filePerms'][0]['id']
        # Start multiple access
        self.test_multiple_access(target=self.test_access, kwargs={
            'cache_url': self.cache_url,
            'access_token': self.access_token,
            'status_codes': [200, 303],
            'close_after_ckeck': True,
            'auth_by_header': self.auth_by_header
        })
