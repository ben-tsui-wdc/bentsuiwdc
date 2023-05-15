# -*- coding: utf-8 -*-
""" Test for desktop sync tool: create sync (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# platform modules
from middleware.test_case import TestCase


class CreateSync(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'Add_Sync'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']
        self.src_path = self.share['src_path']
        self.dst_folder_name = self.share['dst_folder_name']

    def test(self):
        self.log.info("Start create sync test")
        # Todo: replace name with rest api methods
        dst_path = self.ds_obj.get_nas_mount_path('Ben', self.dst_folder_name)
        result = self.ds_obj.create_sync(self.src_path, dst_path)
        if result:
            self.log.info("Create sync test passed")
        else:
            raise self.err.TestFailure("Failed to create sync!")
