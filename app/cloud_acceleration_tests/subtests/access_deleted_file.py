# -*- coding: utf-8 -*-
""" Test for Single Access: Access after file is deleted. (KAM-21169).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# test case
from cloud_acceleration_tests.subtests.access_modified_file import AccessModifiedFileTest


class AccessDeletedFileTest(AccessModifiedFileTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Access_Deleted_File'

    def declare(self):
        self.auth_by_header = True
        self.share_filed = 'shared_file'

    def test(self):
        # Move test file
        moved_file_name = self.share[self.share_filed].get('moved_file_name', self.file_nas_path)
        self.adb.executeShellCommand(cmd='rm {}'.format(moved_file_name))
        self.share[self.share_filed].pop('moved_file_name', None) # clean value
        # Start single access
        resp = self.test_access(cache_url=self.cache_url, access_token=self.access_token, status_codes=[404],
            auth_by_header=self.auth_by_header)
        # Update cache record 
        self.share.pop(self.share_filed)
