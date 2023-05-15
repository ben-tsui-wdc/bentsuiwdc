# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v2/system/clientLogs - 400
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import os
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.test_utils import read_lines_to_string, run_test_with_data
from platform_libraries.test_utils import api_negative_test


class WriteSystemLog400(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Write new log entry to system logs - 400 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-4983'

    def test(self):
        run_test_with_data(
            test_data=read_lines_to_string(os.path.dirname(__file__) + '/../test_data/WriteSystemLog400.txt'),
            test_method=self.write_client_logs_test
        )

    def write_client_logs_test(self, payload_str):
        api_negative_test(
            test_method=self.nasadmin._write_client_logs,
            data_dict={'data': payload_str},
            expect_status=400
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Write system log test for 400 status ***
        """)

    test = WriteSystemLog400(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
