# -*- coding: utf-8 -*-
""" Network Connectivity Test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class NasAdminNetworkConnectivityTest(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-5515 - nasAdmin - Network Connectivity Test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5515'
    ISSUE_JIRA_ID = None

    def test(self):
        network_connection = self.nasadmin.get_network_connection()
        assert network_connection['connected'], 'connected != true'

        assert self.ssh_client.ping('8.8.8.8'), 'Cannot ping 8.8.8.8 from device'


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** nasAdmin - Network Connectivity Test ***
        """)

    test = NasAdminNetworkConnectivityTest(parser)
    resp = test.main()
    print 'test result: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
