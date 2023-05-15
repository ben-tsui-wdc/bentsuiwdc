# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v3/auth - 415 status
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.test_utils import api_negative_test


class PostAuth415(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Login user test - 415 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3381'

    def test(self):
        api_negative_test(
            test_method=self.nasadmin._login_nasAdmin,
            data_dict={
                'data': '{"passcodeType": "cloudToken", "passcode": "BadCloudToken"}"',
                'headers': {'Content-Type': 'application/xml'}
            },
            expect_status=415
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Login user test for 415 status ***
        """)

    test = PostAuth415(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
