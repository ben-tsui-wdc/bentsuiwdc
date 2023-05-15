# -*- coding: utf-8 -*-
""" Test case to check the samba service
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class M2MTokenCheckInOTAcLient(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'M2M Token Check In OTAclient Config'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-8607'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        stdout, stderr = self.ssh_client.execute_cmd('cat /usr/local/modules/otaclient/etc/otaclient.toml | grep m2m | grep -v grep')
        verify_string = ['m2mClientID', 'm2mClientSecret', 'ota_client']
        if not all(x in stdout for x in verify_string):
            raise self.err.TestFailure('Check M2M Token in OTA client config failed! '
                                       'Not all the string: {} can be found in toml file!'.format(verify_string))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Nas Admin Service Check test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/nasadmin_service_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = M2MTokenCheckInOTAcLient(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
