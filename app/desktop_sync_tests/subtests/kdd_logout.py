# -*- coding: utf-8 -*-
""" Test for desktop sync tool: kdd logout (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# platform modules
from middleware.test_case import TestCase


class KDDLogout(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'KDD_Logout'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']

    def test(self):
        self.log.info("Start Logout KDD test")
        status_result = self.ds_obj.kdd_log_status()
        if status_result:
            logout_result = self.ds_obj.kdd_logout()
            if logout_result:
                # double confirm kdd user is logged out
                status_result = self.ds_obj.kdd_log_status()
                if status_result:
                    raise self.err.TestFailure("KDD user is still logged in after running log out!")
                else:
                    self.log.info("KDD logout passed")
            else:
                raise self.err.TestFailure("Failed to logout KDD!")
        else:
            self.log.warning("No user is logged in, skip the test")
