# -*- coding: utf-8 -*-
""" Test case to test App auto update Test - Same app with multiple containers case
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from kdp_scripts.functional_tests.app_manager.app_update import AppUpdateCheck
from kdp_scripts.test_utils.test_case_utils import \
    nsa_declare_2nd_user, nsa_after_test_user, nsa_add_argument_2nd_user, nsa_init_2nd_user


class AppUpdateCheckMultipleUser(AppUpdateCheck):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-2304 - App auto update Test - Same app with multiple containers case'
    TEST_JIRA_ID = 'KDP-2304'

    def declare(self):
        super(AppUpdateCheckMultipleUser, self).declare()
        nsa_declare_2nd_user(self)

    def before_test(self):
        nsa_init_2nd_user(self)
        if not self.check_app_install:
            return
        if self.uut_owner.get_app_state_kdp(self.app_id) == 'installed':
            self.uut_owner.uninstall_app(self.app_id)
            if not self.uut_owner.wait_for_app_uninstall_completed(self.app_id):
                raise self.err.TestFailure('APP({}) is failed to uninstall'.format(self.app_id))
        if self.rest_2nd.get_app_state_kdp(self.app_id) == 'installed':
            self.rest_2nd.uninstall_app(self.app_id)
            if not self.rest_2nd.wait_for_app_uninstall_completed(self.app_id):
                raise self.err.TestFailure('APP({}) is failed to uninstall'.format(self.app_id))

    def test(self):
        self.clean_app_mgr_log()

        self.install_app()
        owner_user_id = self.get_user_id()
        self.install_app(client=self.rest_2nd)
        user_2nd_id = self.get_user_id(ignore_id=owner_user_id)

        self.modify_app_version()
        self.restart_app_mgr()
        self.check_app_version_from_call(version='1.0.0')
        self.check_app_version_from_call(version='1.0.0', client=self.rest_2nd)

        self.downgrade_app_version()
        self.restart_app_mgr()
        self.check_app_version_from_call(version='1.0.1')
        self.check_app_version_from_call(version='1.0.1', client=self.rest_2nd)
        time.sleep(10)
        self.check_update_logs(user_id=owner_user_id)
        self.check_update_logs(user_id=user_2nd_id)

    def after_test(self):
        if self.uninstall_app:
            self.log.info('Start to Uninstall App({}) for 2nd user...'.format(self.app_id))
            self.rest_2nd.uninstall_app(self.app_id)
            if not self.rest_2nd.wait_for_app_uninstall_completed(self.app_id):
                self.log.error('Failed to uninstall app for 2nd user...')
        super(AppUpdateCheckMultipleUser, self).after_test()
        nsa_after_test_user(self)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** App Update Test Script ***
        """)

    nsa_add_argument_2nd_user(parser)
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test',
                        action='store_true')
    parser.add_argument('-uninstall_app', '--uninstall_app', help='Uninstall installed app after test',
                        action='store_true')

    test = AppUpdateCheckMultipleUser(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
