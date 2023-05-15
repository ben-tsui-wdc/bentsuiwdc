# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v2/system/clientLogs - 401
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.test_utils import api_negative_test


class WriteSystemLog401(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Write new log entry to system logs - 401 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-4983'

    def test(self):
        api_negative_test(
            test_method=self.nasadmin.write_client_logs,
            data_dict={'level': 'info', 'message': {}},
            expect_status=401,
            pre_handler=self.nasadmin.hide_access_token,
            finally_handler=self.nasadmin.reveal_access_token
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Write system log test for 401 status ***
        """)

    test = WriteSystemLog401(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
