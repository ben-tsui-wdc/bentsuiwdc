# -*- coding: utf-8 -*-
""" Test cases to check otaclient service is loaded.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class LoadOTAClient(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-194 - OTA Client Daemon Check'
    # Popcorn
    TEST_JIRA_ID = 'KDP-194'

    SETTINGS = {
        'uut_owner': False,
        'enable_auto_ota': True
    }

    def test(self):
        self.log.info("Checking OTA client module")
        ota_client = self.ssh_client.get_otaclient_service()
        if not ota_client:
            raise self.err.TestFailure('Cannot find OTA client service!')

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Load OTA Client Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/load_otaclient.py --uut_ip 10.92.224.68\
        """)

    test = LoadOTAClient(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
