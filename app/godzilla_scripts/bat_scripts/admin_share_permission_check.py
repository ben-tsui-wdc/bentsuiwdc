# -*- coding: utf-8 -*-
""" Test case to check the default admin share permission
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import lxml.etree
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class AdminSharePermissionCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Admin Share Permission Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1407'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        self.log.info("Checking the permissions in samba config")
        share_permissions = self.ssh_client.get_share_permission()
        for folder in share_permissions.keys():
            if folder not in ['Public', 'SmartWare', 'TimeMachineBackup'] and "Mass_Storage_Device" not in folder:
                continue
            self.log.info("Folder: {0}, Public permission: {1}".format(folder, share_permissions[folder]['public']))
            if share_permissions[folder]['public'] != "yes":
                raise self.err.TestFailure("The default share permission of folder: {} is incorrect!".format(folder))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** AFP Service Check test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/admin_share_permission_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = AdminSharePermissionCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
