# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v3/auth - 400 status
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import os
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.test_utils import \
    read_lines_to_string, run_test_with_data, api_negative_test


class PostAuth400(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Login user test - 400 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3381'

    def test(self):
        run_test_with_data(
            test_data=read_lines_to_string(os.path.dirname(__file__) + '/../test_data/PostAuth400.txt'),
            test_method=self.post_auth_400_test
        )

    def post_auth_400_test(self, payload_str):
        api_negative_test(
            test_method=self.nasadmin._login_nasAdmin,
            data_dict={'data': payload_str},
            expect_status=400
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Login user test for 400 status ***
        """)

    test = PostAuth400(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
