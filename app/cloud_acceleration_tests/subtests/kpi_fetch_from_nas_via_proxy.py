# -*- coding: utf-8 -*-
""" KPI Test for Fetch File From NAS case. (KAM-21268, KAM-21271).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"


# platform modules
from middleware.sub_test import SubTest
import platform_libraries.request_timing as rt

class KPIFetchFromNASViaProxy(SubTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'KPI_Fetch_From_NAS_Via_Proxy'

    def declare(self):
        self.share_filed = 'shared_file'

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']
        self.headers = 'Authorization: Bearer {}'.format(self.share[self.share_filed]['access_token'])

    def test(self):
        parse_url = self.cache_url.split("/")
        device_id = parse_url[4]
        file_id = parse_url[8]
        url = "{}/{}/sdk/v2/files/{}/content".format(self.uut_owner.environment.get_external_uri(),
                                                     device_id, file_id)
        resp = rt.get_request(url, headers=[self.headers])
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
