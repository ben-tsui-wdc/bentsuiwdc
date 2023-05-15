# -*- coding: utf-8 -*-
""" Test cases to verify otaclient config toml file to support m2m token
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class OtaclientConfigM2MCheck(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-206 - otaclient config toml file check of m2m token support'
    # Popcorn
    TEST_JIRA_ID = 'KDP-206'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        stdout, stderr = self.ssh_client.execute_cmd('cat /usr/local/modules/otaclient/etc/otaclient.toml | grep m2m | grep -v grep')
        check_list = ['m2mClientID', 'm2mClientSecret', 'ota_client']
        if not all(word in stdout for word in check_list):
            raise self.err.TestFailure('Check M2M Token in OTA client config failed! '
                                       'Not all the string: {} can be found in toml file!'.format(check_list))

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** otaclient toml file check m2m support Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/otaclient_toml_m2m_check.py --uut_ip 10.200.141.68\
        """)

    test = OtaclientConfigM2MCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp: sys.exit(0)
    sys.exit(1)
