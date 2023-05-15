# -*- coding: utf-8 -*-
""" Test for Multiple Access: Access after file is deleted. (KAM-21170).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# test case
from cloud_acceleration_tests.subtests.access_deleted_file import AccessDeletedFileTest
from cloud_acceleration_tests.subtests.multiple_1st_access import MultipleFisrtAccessTest


class MultipleAccessDeletedFileTest(AccessDeletedFileTest, MultipleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Multiple_Access_Deleted_File'

    def test(self):
        # Move test file
        moved_file_name = self.share[self.share_filed].get('moved_file_name', self.file_nas_path)
        self.adb.executeShellCommand(cmd='rm {}.moved'.format(self.file_nas_path))
        self.share[self.share_filed].pop('moved_file_name', None) # clean value
        # Start multiple access.
        self.test_multiple_access(target=self.test_access, kwargs={
            'cache_url': self.cache_url,
            'access_token': self.access_token,
            'status_codes': [404],
            'auth_by_header': self.auth_by_header
        })
        # Update cache record 
        self.share.pop(self.share_filed)
