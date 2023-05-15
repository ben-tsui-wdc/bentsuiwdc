# -*- coding: utf-8 -*-
""" Test for desktop sync tool: Unsync (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# platform modules
from middleware.test_case import TestCase


class Unsync(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'Remove_Sync'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']
        self.src_path = self.share['src_path']

    def test(self):
        self.log.info("Start unsync test")
        result = self.ds_obj.delete_sync(self.src_path)
        if result:
            self.log.info("Unsync test passed")
        else:
            raise self.err.TestFailure("Failed unsync!")
