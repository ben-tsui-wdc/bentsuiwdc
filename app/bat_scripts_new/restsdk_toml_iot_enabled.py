# -*- coding: utf-8 -*-
""" Test cases to verify restsdk-server config toml file IoT is enabled
    https://jira.wdmv.wdc.com/browse/KAM-36558
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class RestsdkConfigIoTEnabledCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'KAM-36558 - Verify restsdk-server config file IoT is enabled'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-36558'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        IoT_enabled_check = self.adb.executeShellCommand('cat /etc/restsdk-server.toml | grep IoT')[0]
        check_list1 = ['true']
        if not all(word in IoT_enabled_check for word in check_list1):
            raise self.err.TestFailure('Restsdk-server config file IoT is not enabled, test failed !!!'.format(word))

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Verify restsdk-server config file IoT is enabled Script ***
        Examples: ./run.sh bat_scripts_new/restsdk_toml_iot_enabled.py --uut_ip 10.200.141.68\
        """)

    test = RestsdkConfigIoTEnabledCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
