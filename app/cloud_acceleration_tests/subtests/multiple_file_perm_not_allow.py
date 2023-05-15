# -*- coding: utf-8 -*-
""" Test for Multiple Access: File permission changed to access deny case. (KAM-21163).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# test case
from cloud_acceleration_tests.subtests.multiple_1st_access import MultipleFisrtAccessTest
from cloud_acceleration_tests.subtests.file_perm_not_allow import FilePermNotAllowTest


class MultipleFilePermNotAllowTest(FilePermNotAllowTest, MultipleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Multiple: File_Perm-Allow_To_Not_Allow'

    def test(self):
        # Delete test file permission
        self.uut_owner.delete_permission(permission_id=self.permission_id)
        # Update cache record 
        self.share[self.share_filed]['permission_id'] = None
        # Start multiple access
        self.test_multiple_access(target=self.test_access, kwargs={
            'cache_url': self.cache_url,
            'access_token': self.access_token,
            'status_codes': [404],
            'auth_by_header': self.auth_by_header
        })
