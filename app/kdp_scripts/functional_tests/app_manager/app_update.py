# -*- coding: utf-8 -*-
""" Test case to test App auto update Test - Simple case (From locally)
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP


class AppUpdateCheck(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-2303 - App auto update Test - Simple case (Locally)'
    TEST_JIRA_ID = 'KDP-2303'

    def declare(self):
        self.app_id = 'com.wdc.filebrowser'
        self.app_config_path = '{}/app_com.wdc.filebrowser_com.wdc.filebrowser-1.0.1.json'.format(KDP.APP_ROOT_PATH)
        self.app_downgrade_config_path = '{}/app_com.wdc.filebrowser_com.wdc.filebrowser-1.0.0.json'.format(
            KDP.APP_ROOT_PATH)
        self.app_mgr_log_path = '/var/log/appMgr.log'
        self.uninstall_app = False
        self.check_app_install = False

    def before_test(self):
        if not self.check_app_install:
            return
        if self.uut_owner.get_app_state_kdp(self.app_id) == 'installed':
            self.uut_owner.uninstall_app(self.app_id)
            if not self.uut_owner.wait_for_app_uninstall_completed(self.app_id):
                raise self.err.TestFailure('APP({}) is failed to uninstall'.format(self.app_id))

    def test(self):
        self.clean_app_mgr_log()

        self.install_app()
        user_id = self.get_user_id()

        self.modify_app_version()
        self.restart_app_mgr()
        self.check_app_version_from_call(version='1.0.0')

        self.downgrade_app_version()
        self.restart_app_mgr()
        self.check_app_version_from_call(version='1.0.1')
        self.check_update_logs(user_id=user_id)

    def clean_app_mgr_log(self):
        self.log.info('Cleaning appMpr.log')
        self.ssh_client.execute('rm {}.*'.format(self.app_mgr_log_path))
        exitcode, output = self.ssh_client.execute('echo "" > {}'.format(self.app_mgr_log_path))
        assert exitcode == 0, 'Failed to clean appMpr.log'

    def install_app(self, client=None):
        if not client:
            client = self.uut_owner
        client.install_app_kdp(self.app_id)
        if not client.wait_for_app_install_completed(self.app_id):
            raise self.err.TestFailure('APP({}) is not install successfully, test Failed !!!'.format(self.app_id))
        self.log.info('*** App({}) has been installed'.format(self.app_id))

    def get_user_id(self, ignore_id=None):
        self.log.info('Finding user ID')
        pattern = 'grep "Install Handler: succeeded" {}'.format(self.app_mgr_log_path)
        if ignore_id:
            pattern = '{} | grep -v "{}"'.format(pattern, ignore_id)
        exitcode, output = self.ssh_client.execute(pattern)
        assert exitcode == 0, 'Failed to find user ID'
        user_id = output.split('"userID":"').pop().split('"')[0]
        self.log.info('User ID: {}'.format(user_id))
        return user_id

    def modify_app_version(self):
        self.log.info('Modifying "version" from "1.0.1" to "1.0.0"')
        exitcode, output = self.ssh_client.execute(
            '''sed -i 's/"version": "1.0.1",/"version": "1.0.0",/g' {}'''.format(self.app_config_path))
        assert exitcode == 0, 'Failed to modify config file'

    def check_app_version_from_call(self, version, client=None):
        self.log.info('Checking APP version is {}'.format(version))
        if not client:
            client = self.uut_owner
        resp = client.get_app_info_kdp(self.app_id)
        assert resp['info']['availableVersion'] == version

    def downgrade_app_version(self):
        self.log.info('Modifying config file from "1.0.1" to "1.0.0"')
        exitcode, output = self.ssh_client.execute(
            '''sed -i 's/com.wdc.filebrowser-1.0.1/com.wdc.filebrowser-1.0.0/g' {}'''.format(self.app_config_path))
        assert exitcode == 0, 'Failed to modify config file'
        exitcode, output = self.ssh_client.execute(
            'mv {} {}'.format(self.app_config_path, self.app_downgrade_config_path))
        assert exitcode == 0, 'Failed to rename config file'

    def check_update_logs(self, user_id):
        self.log.info('Checking update logs')
        exitcode, output = self.ssh_client.execute(
            'grep "Update App For User: start" {} | grep {}'.format(self.app_mgr_log_path, user_id))
        assert exitcode == 0, 'Failed to find start status'
        exitcode, output = self.ssh_client.execute(
            'grep "Image Pull Progress" {} | grep "Pulling from" | grep {}'.format(self.app_mgr_log_path, user_id))
        assert exitcode == 0, 'Failed to find image pull log'
        exitcode, output = self.ssh_client.execute(
            'grep "Update App For User: finished" {} | grep {}'.format(self.app_mgr_log_path, user_id))
        assert exitcode == 0, 'Failed to find finished status'

    def restart_app_mgr(self):
        self.log.info('Restarting app manager...')
        self.serial_client.serial_cmd('kdpappmgr.sh restart')
        time.sleep(10)

    def after_test(self):
        if self.uninstall_app:
            self.log.info('Start to Uninstall App({}) ...'.format(self.app_id))
            self.uut_owner.uninstall_app(self.app_id)
            if not self.uut_owner.wait_for_app_uninstall_completed(self.app_id):
                self.log.error('Failed to uninstall app ...')

        self.log.info('Cleaning test config')
        self.ssh_client.execute('test -e {0} && rm {0}'.format(self.app_downgrade_config_path))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** App Update Test Script ***
        Examples: ./run.sh kdp_scripts/functional_tests/app_manager/app_update.py --uut_ip 10.92.224.68 \
        """)

    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test',
                        action='store_true')
    parser.add_argument('-uninstall_app', '--uninstall_app', help='Uninstall installed app after test',
                        action='store_true')

    test = AppUpdateCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
