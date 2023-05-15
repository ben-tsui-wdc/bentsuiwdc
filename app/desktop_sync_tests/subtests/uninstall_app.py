# -*- coding: utf-8 -*-
""" Test for desktop sync tool: uninstall app (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# platform modules
from middleware.test_case import TestCase


class UninstallApp(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'Uninstall_App'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']
        self.app_version = self.share['app_version']

    def test(self):
        self.log.info("Uninstalling Desktop Sync tool, version: {}".format(self.app_version))
        result = self.ds_obj.uninstall_app()
        if result:
            self.log.info("Uninstall Desktop Sync tool passed")
        else:
            raise self.err.TestFailure("Failed to uninstall Desktop Sync tool!")
