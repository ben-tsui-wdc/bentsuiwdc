# -*- coding: utf-8 -*-
""" Test case to check the samba service
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class NasAdminServiceCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'NasAdmin Service Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-5282'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        stdout, stderr = self.ssh_client.execute_cmd('ps aux | grep nasAdmin | grep -v grep')
        verify_string = ['nasAdmin', '/etc/nasAdmin.toml']
        if not all(x in stdout for x in verify_string):
            raise self.err.TestFailure('nasAdmin service is not launched on the device!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Nas Admin Service Check test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/nasadmin_service_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = NasAdminServiceCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
