# -*- coding: utf-8 -*-
""" Test for command “systtem_evnet.sh eraseSettings”
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.test_utils.kdp_test_utils import wait_for_device_reboot_completed
from kdp_scripts.test_utils.test_case_utils import \
    nsa_declare_2nd_user, nsa_after_test_user, nsa_add_argument_2nd_user, nsa_init_2nd_user, \
    nsa_update_device_ip
from platform_libraries.assert_utls import nsa_assert_user_by_dict
from platform_libraries.constants import KDP


class EraseSettingsTest(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Erase settings test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5897'

    def declare(self):
        nsa_declare_2nd_user(self)
        self.file_path_owner = None
        self.file_path_user_2nd = None

    def reset_step(self):
        self.log.info('Erasing device settings by "system_event.sh eraseSettings"')
        self.serial_client.serial_write('system_event.sh eraseSettings')

    def test(self):
        cloud_user_owner = self.uut_owner.get_cloud_user()
        token_owner = self.nasadmin.login_owner()
        nsa_init_2nd_user(self)
        cloud_user_2nd = self.rest_2nd.get_cloud_user()
        token_2nd_user = self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.access_token)

        self.log.info("Enabling users local access and update user information")
        owner_info = {
            'localAccess': True,
            'username': 'owner',
            'password': 'password',
            'spaceName': 'OwnerSpace',
            'description': 'Owner'
        }
        self.nasadmin.update_user(user_id=token_owner['userID'], **owner_info)
        owner = self.nasadmin.get_user(token_owner['userID'])
        owner_info.pop('password')
        owner_info.pop('spaceName')
        nsa_assert_user_by_dict(owner_info, owner)
        exitcode, _ = self.ssh_client.execute("ls '{}OwnerSpace'".format(KDP.SHARES_PATH))
        assert exitcode == 0, 'Cannot find share link for owner space'

        user_2nd_info = {
            'localAccess': True,
            'username': 'user2nd',
            'password': 'password2nd',
            'spaceName': 'User2ndSpace',
            'description': 'User2nd'
        }
        self.nasadmin_2nd.update_user(user_id=token_2nd_user['userID'], **user_2nd_info)
        user_2nd = self.nasadmin_2nd.get_user(token_2nd_user['userID'])
        user_2nd_info.pop('password')
        user_2nd_info.pop('spaceName')
        nsa_assert_user_by_dict(user_2nd_info, user_2nd)
        exitcode, _ = self.ssh_client.execute("ls '{}User2ndSpace'".format(KDP.SHARES_PATH))
        assert exitcode == 0, 'Cannot find share link for 2nd user space'

        self.log.info("Creating test data to user root")
        self.file_path_owner = "{}/{}/test".format(KDP.USER_ROOT_PATH, cloud_user_owner['user_id'])
        exitcode, _ = self.ssh_client.execute("echo owner > '{}'".format(self.file_path_owner))
        self.file_path_user_2nd = "{}/{}/test".format(KDP.USER_ROOT_PATH, cloud_user_2nd['user_id'])
        exitcode, _ = self.ssh_client.execute("echo user2nd > '{}'".format(self.file_path_user_2nd))

        self.reset_step()
        wait_for_device_reboot_completed(self)
        nsa_update_device_ip(self, ip=self.nasadmin.ip)

        self.log.info("Logging users in again")
        token_owner = self.nasadmin.login_owner()
        token_2nd_user = self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.access_token)

        self.log.info("Checking user information")
        default_user_info = {
            'localAccess': False,
            'username': '',
            'description': ''
        }
        owner = self.nasadmin.get_user(token_owner['userID'])
        nsa_assert_user_by_dict(default_user_info, owner)
        user_2nd = self.nasadmin_2nd.get_user(token_2nd_user['userID'])
        nsa_assert_user_by_dict(default_user_info, user_2nd)

        self.log.info("Checking data")
        exitcode, output = self.ssh_client.execute("cat '{}'".format(self.file_path_owner))
        assert exitcode == 0, 'Failed to access test file in owner root'
        assert output == 'owner', 'Test file in owner root seems changed'
        exitcode, output = self.ssh_client.execute("cat '{}'".format(self.file_path_user_2nd))
        assert exitcode == 0, 'Failed to access test file in 2nd user root'
        assert output == 'user2nd', 'Test file in 2nd user root seems changed'

    def after_test(self):
        nsa_after_test_user(self)
        if self.file_path_owner:
            self.ssh_client.execute("ls '{0}' && rm '{0}'".format(self.file_path_owner))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Erase settings test ***
        """)
    nsa_add_argument_2nd_user(parser)

    test = EraseSettingsTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
