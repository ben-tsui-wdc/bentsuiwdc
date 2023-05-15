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


class SecondUserSharePermissionCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Second User Share Permission Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1455'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.second_username = 'second_user'

    def before_test(self):
        self.log.info("Delete user if it's already existed before testing")
        if self.ssh_client.check_user_in_device(self.second_username):
            self.ssh_client.delete_user(self.second_username)
        self.log.info("Delete share folder if it's already existed before testing")
        if self.ssh_client.check_share_in_device(self.second_username):
            self.ssh_client.delete_share(self.second_username)

    def test(self):
        self.log.info("Create second user")
        self.ssh_client.create_user(username=self.second_username)
        self.log.info("Checking the permissions in samba config")
        share_permissions = self.ssh_client.get_share_permission()
        self.log.info("Folder: {0}, Public permission: {1}".
                      format(self.second_username, share_permissions[self.second_username]['public']))
        if share_permissions[self.second_username]['public'] != "no":
            raise self.err.TestFailure(
                "The default share permission of folder: {} should not be public!".format(self.second_username))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Second User Share Permission Check test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/second_user_share_permission_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = SecondUserSharePermissionCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
