# -*- coding: utf-8 -*-
""" Test for Multiple Access: Access Renamed File case (KAM-21165).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# test case
from cloud_acceleration_tests.subtests.access_moved_file import AccessMovedFileTest
from cloud_acceleration_tests.subtests.multiple_1st_access import MultipleFisrtAccessTest


class MultipleAccessMovedFileTest(AccessMovedFileTest, MultipleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Multiple_Access_Moved_File'

    def test(self):
        # Move test file
        self.adb.executeShellCommand(cmd='mv {0} {0}.moved'.format(self.file_nas_path))
        self.share[self.share_filed]['moved_file_name'] = '{0}.moved'.format(self.file_nas_path)
        # Start multiple access
        self.test_multiple_access(target=self.test_access, kwargs={
            'cache_url': self.cache_url,
            'access_token': self.access_token,
            'status_codes': [200, 303],
            'close_after_ckeck': True,
            'auth_by_header': self.auth_by_header
        })
        # Update cache record 
        self.share[self.share_filed]['status'] = 'caching'
