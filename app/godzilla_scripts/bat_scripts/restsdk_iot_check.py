# -*- coding: utf-8 -*-
""" Test case to check the samba service
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class IoTCheckInRestSDK(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'IoT Check In RestSDK Config'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-8609'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        stdout, stderr = self.ssh_client.execute_cmd('cat /usr/local/modules/restsdk/etc/restsdk-server.toml | grep IoT | grep -v grep')
        # From RestSDK 2.13.0-2036, the realIoT is disabled in all devices
        verify_string = ['realIoT', 'false']
        if not all(x in stdout for x in verify_string):
            raise self.err.TestFailure('Check IoT support in RestSDK config failed! '
                                       'Not all the string: {} can be found in toml file!'.format(verify_string))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Nas Admin Service Check test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/nasadmin_service_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = IoTCheckInRestSDK(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
