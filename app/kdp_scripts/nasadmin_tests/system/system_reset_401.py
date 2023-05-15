# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v2/system/reset - 401
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.test_utils import api_negative_test


class SystemReset401(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Initiate system reset - 401 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-4971'

    def test(self):
        api_negative_test(
            test_method=self.nasadmin.system_reset,
            data_dict={'rtype': 'eraseSettings'},
            expect_status=401,
            pre_handler=self.nasadmin.hide_access_token,
            finally_handler=self.nasadmin.reveal_access_token
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** System reset log test for 401 status ***
        """)

    test = SystemReset401(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
