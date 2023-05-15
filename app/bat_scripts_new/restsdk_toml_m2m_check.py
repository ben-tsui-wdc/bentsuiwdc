# -*- coding: utf-8 -*-
""" Test cases to verify restsdk config toml file to support m2m token
    https://jira.wdmv.wdc.com/browse/KAM-36556
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class RestsdkConfigM2MCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'KAM-36556 - restsdk config toml file check of m2m token support'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-36556'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        m2m_check = self.adb.executeShellCommand('cat /etc/restsdk-server.toml | grep m2m')[0]
        check_list1 = ['m2mClientID', 'm2mClientSecret', 'rsdk']
        if not all(word in m2m_check for word in check_list1):
            raise self.err.TestFailure('restsdk config toml file check of m2m token support failed!! {} is not in the list'.format(word))

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Restsdk toml file check m2m support Script ***
        Examples: ./run.sh bat_scripts_new/restsdk_toml_m2m_check.py --uut_ip 10.200.141.68\
        """)

    test = RestsdkConfigM2MCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
