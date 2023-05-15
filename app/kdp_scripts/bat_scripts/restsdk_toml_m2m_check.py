# -*- coding: utf-8 -*-
""" Test cases to verify restsdk config toml file to support m2m token
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class RestsdkConfigM2MCheck(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-197 - restsdk config toml file check of m2m token support'
    TEST_JIRA_ID = 'KDP-197'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        stdout, stderr = self.ssh_client.execute_cmd('cat /usr/local/modules/restsdk/etc/restsdk-server.toml | grep m2m | grep -v grep')
        check_list = ['m2mClientID', 'm2mClientSecret', 'rsdk']
        if not all(word in stdout for word in check_list):
            raise self.err.TestFailure('restsdk config toml file check of m2m token support failed!! {} is not in the list'.format(word))

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Restsdk toml file check m2m support Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/restsdk_toml_m2m_check.py --uut_ip 10.200.141.68\
        """)

    test = RestsdkConfigM2MCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
