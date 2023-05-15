# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v2/system/reset - 415
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.test_utils import api_negative_test


class SystemReset415(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Initiate system reset - 415 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-4971'

    def test(self):
        api_negative_test(
            test_method=self.nasadmin._system_reset,
            data_dict={'data': '{"type": "eraseSettings"}', 'headers': {'Content-Type': 'application/xml'}},
            expect_status=415
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** System reset test for 415 status ***
        """)

    test = SystemReset415(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
