# -*- coding: utf-8 -*-
""" Test for desktop sync tool: install app (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# platform modules
from middleware.test_case import TestCase


class InstallApp(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'Install_App'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']
        self.app_version = self.share['app_version']
        self.cloud_env = self.share['cloud_env']

    def test(self):
        self.log.info("Installing Desktop Sync tool, version: {}".format(self.app_version))
        result = self.ds_obj.install_app(self.app_version, self.cloud_env)
        if result:
            self.log.info("Install Desktop Sync tool passed")
        else:
            raise self.err.TestFailure("Failed to install Desktop Sync tool!")

