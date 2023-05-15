# -*- coding: utf-8 -*-
""" KPI Test for Fetch File While Caching case. (KAM-21269, KAM-21272).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"


# platform modules
from middleware.sub_test import SubTest
import platform_libraries.request_timing as rt


class KPISingleFisrtAccess(SubTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'KPI_Single_Fisrt_Access'

    def declare(self):
        self.share_filed = 'shared_file'

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']
        self.headers = 'Authorization: Bearer {}'.format(self.share[self.share_filed]['access_token'])

    def test(self):
        self.measuring_access(cache_url=self.cache_url, headers=[self.headers])

    def measuring_access(self, cache_url, headers):
        resp = rt.get_request(cache_url, headers)
        self.log.info('* Status Code: {}'.format(resp.get('status_code')))
        if resp.get('status_code') != 200:
            self.log.error('Status Code should be 200, but it is {}'.format(resp.get('status_code')))
            raise self.err.TestFailure('API response is not expected')
        else:
            self.log.info('* Latency: {}'.format(resp.get('TTFB_time')))
            self.log.info('* Download Time: {}'.format(resp.get('total_time')))
            self.save_result(latency=resp.get('TTFB_time'), download_time=resp.get('total_time'))

    def save_result(self, latency, download_time):
        """ Save data to test result. """
        self.data.test_result['{} Latency'.format(self.TEST_NAME)] = latency
        self.data.test_result['{} Download Time'.format(self.TEST_NAME)] = download_time
