# -*- coding: utf-8 -*-
""" Test for Single Access: Access Renamed File case. (KAM-21164).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# test case
from cloud_acceleration_tests.subtests.access_modified_file import AccessModifiedFileTest


class AccessMovedFileTest(AccessModifiedFileTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Access_Moved_File'

    def declare(self):
        self.auth_by_header = True
        self.share_filed = 'shared_file'

    def test(self):
        # Move test file
        self.adb.executeShellCommand(cmd='mv {0} {0}.moved'.format(self.file_nas_path))
        self.share[self.share_filed]['moved_file_name'] = '{0}.moved'.format(self.file_nas_path)
        # Test request
        resp = self.test_access(cache_url=self.cache_url, access_token=self.access_token, status_codes=[200],
            close_after_ckeck=True, auth_by_header=self.auth_by_header) # We don't check content, so close it for performance.
        # Update cache record 
        self.share[self.share_filed]['status'] = 'caching'
