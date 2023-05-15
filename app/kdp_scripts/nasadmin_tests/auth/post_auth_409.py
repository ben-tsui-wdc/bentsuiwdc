# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v3/auth - 409 status
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.test_utils.kdp_test_utils import attach_user, reset_device
from platform_libraries.test_utils import api_negative_test


class PostAuth409(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Login user test - 409 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3381'

    def test(self):
        try:
            reset_device(self)
            api_negative_test(
                test_method=self.nasadmin.login_with_cloud_token,
                data_dict={'cloud_token': 'BadCloudToken'},
                expect_status=409
            )
        except Exception as e:
            raise e
        finally:
            try:
                self.log.info("Recover test device - attaching owner")
                attach_user(self)
            except Exception as e:
                self.log.warning(e)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Login user test for 409 status ***
        """)

    test = PostAuth409(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
