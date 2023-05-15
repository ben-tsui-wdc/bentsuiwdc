# -*- coding: utf-8 -*-
""" Test for desktop sync tool: kdd login (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# platform modules
from middleware.test_case import TestCase


class KDDLogin(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'KDD_Login'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']

    def test(self):
        self.log.info("Start Login KDD test")
        # Check if anyone is logged in before
        status_result = self.ds_obj.kdd_log_status()
        if status_result:
            logout_result = self.ds_obj.kdd_logout()
            if not logout_result:
                raise self.err.TestFailure("Failed to logout KDD before testing!")

        result = self.ds_obj.kdd_login(self.uut_owner.id_token, self.uut_owner.refresh_token)
        if result:
            status_result = self.ds_obj.kdd_log_status()
            if status_result:
                self.log.info("KDD login passed")
            else:
                raise self.err.TestFailure("Cannot get KDD status after login!")
        else:
            raise self.err.TestFailure("KDD login failed!")
