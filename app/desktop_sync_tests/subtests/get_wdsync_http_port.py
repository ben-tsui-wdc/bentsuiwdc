# -*- coding: utf-8 -*-
""" Test for desktop sync tool: get wdsync http port (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# platform modules
from middleware.test_case import TestCase


class Get_WDSync_HTTP_Port(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'Get_WDSync_HTTP_Port'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']

    def test(self):
        self.log.info("Getting WDSync HTTP port")
        wdsync_http_port = self.ds_obj.get_sync_http_port()
        if wdsync_http_port:
            self.log.info("Get WDSync HTTP port passed. Port: {}".format(wdsync_http_port))
        else:
            raise self.err.TestFailure("Get WDSync HTTP port failed!")