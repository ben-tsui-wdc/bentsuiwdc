# -*- coding: utf-8 -*-
""" Cloud Acceleration KPI test.
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import datetime
import sys
from pprint import pformat
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
# Sub-tests
from cloud_acceleration_tests.functional_tests.create_share import CreateShareTest
from cloud_acceleration_tests.subtests.kpi_fetch_from_nas_via_proxy import KPIFetchFromNASViaProxy
from cloud_acceleration_tests.subtests.kpi_single_1st_access import KPISingleFisrtAccess
from cloud_acceleration_tests.subtests.kpi_single_2nd_access import KPISingleSecondAccess

class Cloud_Acceleration_KPI(IntegrationTest):

    TEST_SUITE = 'Cloud Acceleration'
    TEST_NAME = 'KPI_Cloud_Acceleration'

    def declare(self):
        self.date_time_format = "%Y-%m-%d" # "%Y-%m-%d %H:%M:%S"

    def init(self):
        # Execute time for this test.
        self.exe_time = datetime.datetime.utcnow()
        # Add sub-tests.
        self.integration.add_testcases(testcases=[
            (CreateShareTest, {'file_url': self.file_url, 'TEST_NAME': 'Share_File'}),
            KPIFetchFromNASViaProxy,
            KPISingleFisrtAccess,
            KPISingleSecondAccess
        ])

    def _upload_test_result(self):
        """ Upload to ELK for each round. """
        for sub_test_result in self.data.test_result:
            # Append label for display.
            utc_string = self.exe_time.strftime(self.date_time_format)
            if self.env.iteration:
                sub_test_result['build_itr'] = sub_test_result['build'] + '_itr_{}'.format(self.env.iteration)
            else:
                sub_test_result['build_itr'] = sub_test_result['build']
            sub_test_result['X-label'] = '{}#{}'.format(utc_string, sub_test_result['build'])
            # Not upload CreateShareTest result.
            if sub_test_result['testName'] == 'Share_File':
                continue
            # Not upload error response
            if any(key in ['error_message', 'failure_message', 'skipped_message', 'failure_message'] for key in sub_test_result):
                continue
            # Upload result.
            self.log.info('Upload data:\n {}'.format(pformat(sub_test_result)))
            sub_test_result.upload_to_logstash(server_url=self.env.logstash_server_url)


if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** Cloud_Acceleration_KPI on Kamino Android ***
        Examples: ./run.sh cloud_acceleration_tests/integration_tests/kpi.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-url', '--file_url', help='URL of test file to download from file server', metavar='URL')

    test = Cloud_Acceleration_KPI(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
