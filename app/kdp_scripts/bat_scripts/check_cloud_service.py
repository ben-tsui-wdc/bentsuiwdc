# -*- coding: utf-8 -*-
""" Check cloud services via RestAPI by verifying "cloudConnected" field.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckCloudService(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-204 - Check Cloud Service'
    # Popcorn
    TEST_JIRA_ID = 'KDP-204'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        device_ready = self.ssh_client.get_device_ready_status()
        proxy_connected = self.ssh_client.get_device_proxy_connect_status()
        if not device_ready or not proxy_connected:
            raise self.err.TestFailure('Device is not ready or proxyConnected is not True, test failed !!!')

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Check Cloud Service Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/check_cloud_service.py --uut_ip 10.92.224.68\
        """)

    test = CheckCloudService(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
