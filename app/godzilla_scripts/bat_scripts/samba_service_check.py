# -*- coding: utf-8 -*-
""" Test case to check the samba service
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class SambaServiceCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Samba Service Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1607'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        stdout, stderr = self.ssh_client.execute_cmd('ps aux | grep smbd | grep -v grep')
        if 'smbd -D' not in stdout:
            raise self.err.TestFailure('smbd is not launched on the device!')

        stdout, stderr = self.ssh_client.execute_cmd('ps aux | grep nmbd | grep -v grep')
        if 'nmbd -D' not in stdout:
            raise self.err.TestFailure('nmbd is not launched on the device!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Samba Service Check test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/samba_service_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = SambaServiceCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
