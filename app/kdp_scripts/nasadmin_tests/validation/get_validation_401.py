# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: GET /v2/validation - 401
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.test_utils import api_negative_test


class GetValidation401(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Fetch validation information - 401 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5335'

    def test(self):
        api_negative_test(
            test_method=self.nasadmin.get_validation_info,
            data_dict={},
            expect_status=401,
            pre_handler=self.nasadmin.hide_access_token,
            finally_handler=self.nasadmin.reveal_access_token
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get validation test for 401 status ***
        """)

    test = GetValidation401(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
