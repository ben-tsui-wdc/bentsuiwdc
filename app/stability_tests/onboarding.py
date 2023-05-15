# -*- coding: utf-8 -*-
""" Test for simulate user onboarding.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from kdp_scripts.stability_tests.onboarding import OnBoarding as KDPOnBoarding
from restsdk_tests.functional_tests.factory_restore import FactoryRestoreTest


class OnBoarding(FactoryRestoreTest, KDPOnBoarding):

    TEST_SUITE = 'Stability Tests'
    TEST_NAME = 'Admin On-boarding Test'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-31434,KAM-35957'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def test(self):
        KDPOnBoarding.test(self)

    def after_test(self):
        self.log.info("Reset device...")
        FactoryRestoreTest.test(self)
        

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** On boarding test for Kamino ***
        """)

    parser.add_argument('-sc', '--security_code', help='Security code of the test device', metavar='CODE')

    test = OnBoarding(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
