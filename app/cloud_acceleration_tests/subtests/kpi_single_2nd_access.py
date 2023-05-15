# -*- coding: utf-8 -*-
""" KPI Test for Fetch File From S3 case. (KAM-21270, KAM-21273).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import json
import time
# platform modules
from middleware.test_case import TestCase
import platform_libraries.request_timing as rt
# test case
from cloud_acceleration_tests.subtests.kpi_single_1st_access import KPISingleFisrtAccess
from cloud_acceleration_tests.subtests.single_2nd_access import SingleSecondAccessTest


class KPISingleSecondAccess(KPISingleFisrtAccess, SingleSecondAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'KPI_Single_Second_Access'

    def declare(self):
        self.share_filed = 'shared_file'
        self.wait_time = None

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.access_token = self.share[self.share_filed]['access_token']
        self.cache_url = self.share[self.share_filed]['cache_url']

    def test(self):
        # Wait for cahce done and get the redirect_url.
        self.test_single_2nd_access(
            cache_url=self.cache_url, access_token=self.access_token, share_filed=self.share_filed, wait_time=self.wait_time)
        # Measure access time.
        redirect_url = self.share[self.share_filed]['redirect_url']
        self.measuring_access(cache_url=redirect_url, headers=None)
