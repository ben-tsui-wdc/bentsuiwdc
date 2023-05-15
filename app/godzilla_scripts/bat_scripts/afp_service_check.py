# -*- coding: utf-8 -*-
""" Test case to check the AFP service
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class AFPServiceCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'AFP Service Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1144'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        """ Removed from 5.19.105
        result = self.ssh_client.execute_cmd('ps aux | grep afp | grep -v grep')[0]
        afp_check_list = ['/usr/sbin/netatalk', '/usr/sbin/afpd', '/usr/sbin/cnid_metad']
        for service in afp_check_list:
            if service not in result:
                raise self.err.TestFailure('AFP Service Check Failed! Cannot find {}'.format(service))
        """
        result = self.ssh_client.execute_cmd('ps aux | grep avahi | grep -v grep')[0]
        if 'avahi-daemon: running' not in result:
            raise self.err.TestFailure('Avahi Service Check Failed')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** AFP Service Check test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/afp_service_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = AFPServiceCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
