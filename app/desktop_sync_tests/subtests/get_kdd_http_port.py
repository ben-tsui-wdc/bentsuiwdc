# -*- coding: utf-8 -*-
""" Test for desktop sync tool: get kdd http port (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# platform modules
from middleware.test_case import TestCase


class Get_KDD_HTTP_Port(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'Get_KDD_HTTP_Port'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']

    def test(self):
        self.log.info("Getting KDD HTTP port")
        kdd_http_port = self.ds_obj.get_kdd_http_port()
        if kdd_http_port:
            self.log.info("KDD HTTP port passed. Port: {}".format(kdd_http_port))
        else:
            raise self.err.TestFailure("Get KDD HTTP port failed!")