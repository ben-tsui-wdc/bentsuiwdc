# -*- coding: utf-8 -*-
""" Test cases to verify restsdk-server config toml file IoT is enabled
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class RestsdkConfigIoTEnabledCheck(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-213 - Verify restsdk-server config toml file IoT is enabled'
    TEST_JIRA_ID = 'KDP-213'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        stdout, stderr = self.ssh_client.execute_cmd('cat /usr/local/modules/restsdk/etc/restsdk-server.toml | grep IoT | grep -v grep')
        if 'true' not in stdout:
            raise self.err.TestFailure('Restsdk-server config file IoT is not enabled, test failed !!!')

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Verify restsdk-server config file IoT is enabled Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/restsdk_toml_iot_enabled.py --uut_ip 10.200.141.68\
        """)

    test = RestsdkConfigIoTEnabledCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
