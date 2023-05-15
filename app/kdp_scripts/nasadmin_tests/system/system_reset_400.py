# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v2/system/reset - 400
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import os
import sys
# platform modules
from kdp_scripts.test_utils.kdp_test_utils import wait_for_device_reboot_completed
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.test_utils import read_lines_to_string, run_test_with_data
from platform_libraries.test_utils import api_negative_test


class SystemReset400(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Initiate system reset - 400 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-4971'

    def test(self):
        run_test_with_data(
            test_data=read_lines_to_string(os.path.dirname(__file__) + '/../test_data/SystemReset400.txt'),
            test_method=self.system_reset_test
        )

    def system_reset_test(self, payload_str):
        handle_success_call = False
        try:
            api_negative_test(
                test_method=self.nasadmin._system_reset,
                data_dict={'data': payload_str},
                expect_status=400
            )
        except self.err.TestFailure as e:
            if 'Success' in str(e):
                handle_success_call = True
            raise
        finally:
            if handle_success_call:
                self.log.info('The test call is success, need to wait for reset completed')
                wait_for_device_reboot_completed(self)
                self.nasadmin.login_owner()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** System reset test for 400 status ***
        """)

    test = SystemReset400(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
