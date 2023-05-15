# -*- coding: utf-8 -*-
""" Test for Multiple Access Modified File case. (KAM-21159).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# platform modules
from platform_libraries.constants import Kamino
# test case
from cloud_acceleration_tests.subtests.access_modified_file import AccessModifiedFileTest
from cloud_acceleration_tests.subtests.multiple_1st_access import MultipleFisrtAccessTest


class MultipleAccessModifiedFileTest(AccessModifiedFileTest, MultipleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Multiple_Access_Modified_File'

    def test(self):
        # Modify test file.
        self.adb.executeShellCommand(cmd='echo {} >> {}'.format(self.text_to_append, self.file_nas_path))
        # Start multiple access.
        self.test_multiple_access(target=self.test_access, kwargs={
            'cache_url': self.cache_url,
            'access_token': self.access_token,
            'status_codes': [200, 303],
            'auth_by_header': self.auth_by_header
        })
        # Update cache record 
        self.share[self.share_filed]['status'] = 'caching'
        # Start verify ETAG with multiple access.
        self.test_multiple_access(target=self.verify_etag, kwargs={
            'comp_etag': self.share[self.share_filed]['etag'],
            'cache_url': self.cache_url,
            'access_token': self.access_token,
            'share_filed': self.share_filed,
            'auth_by_header': self.auth_by_header
        })
        # Update cache record 
        self.share[self.share_filed]['status'] = 'cached'
