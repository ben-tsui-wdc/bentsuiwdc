# -*- coding: utf-8 -*-
""" Test case to uninstall app to test app manager.
    https://jira.wdmv.wdc.com/browse/KDP-208
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import os
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class UninstallApp(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-208 - Uninstall App'
    TEST_JIRA_ID = 'KDP-208,KDP-2012,KDP-2066,KDP-3907'

    def declare(self):
        self.app_id = None
        self.container_clean_check = False
        self.app_bring_up_verify = False

    def init(self):
        if self.app_bring_up_verify:
            self.TEST_JIRA_ID = '{},KDP-2062'.format(self.TEST_JIRA_ID)

    def before_test(self):
        if self.uut_owner.get_app_state_kdp(self.app_id) == 'notInstalled':
            raise self.err.TestSkipped('There are no App({0}) installed ! Skipped the Uninstall App test !'.format(self.app_id))

    def test(self):
        self.uut_owner.uninstall_app_kdp(self.app_id)
        if not self.uut_owner.wait_for_app_uninstall_completed(self.app_id):
            raise self.err.TestFailure('App({}) uninstallation failed ! Test Failed !!!'.format(self.app_id))
        self.logs_removed_check()
        if self.container_clean_check:
            self.docker_container_clean_check()
        self.log.info('App({}) has been uninstalled. Test PASSED !!!'.format(self.app_id))

        if self.app_bring_up_verify:
            self.log.info('Additional checks with reboot device...')
            self.ssh_client.reboot_device()
            self.ssh_client.wait_for_device_to_shutdown()
            self.ssh_client.wait_for_device_boot_completed()
            self.docker_container_clean_check()
            app_state = self.uut_owner.get_app_state_kdp(self.app_id)
            assert 'notInstalled' in app_state, 'App({}) is not notInstalled'.format(self.app_id)

    def docker_container_clean_check(self):
        self.log.info("Check docker container is not exist after app uninstalled ...")
        docker_container_list = self.ssh_client.execute_cmd('docker ps -a | grep -v "CONTAINER ID"')[0]
        if docker_container_list:
            raise self.err.TestFailure('Container is not clean, test failed !!!')

    def logs_removed_check(self):
        self.log.info("Check logs has been removed after app uninstalled...")
        owner_cloud_user = self.uut_owner.get_cloud_user()
        cloud_id = owner_cloud_user['user_id']
        time.sleep(5)
        logs_to_disk = self.ssh_client.get_app_log_type(self.app_id)
        if logs_to_disk:
            exit_status, output = self.ssh_client.execute(
                "ls /data/wd/diskVolume0/kdpappmgr/logs/{} | grep '{}'".format(self.app_id, cloud_id))
        else:
            exit_status, output = self.ssh_client.execute(
                "ls /var/log/apps/{} | grep '{}'".format(self.app_id, cloud_id))
        if exit_status == 0:
            raise self.err.TestFailure('logs files are exist, test failed !!!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Uninstall App Test Script ***
        Examples: ./run.sh kdp_scripts/functional_tests/app_manager/uninstall_app.py --uut_ip 10.92.224.68\
        """)

    parser.add_argument('-appid', '--app_id', help='App ID to uninstalled')
    parser.add_argument('-ccc', '--container_clean_check', help='check docker container has been clean up', action='store_true')
    parser.add_argument('-abuv', '--app_bring_up_verify', help='APP uninstall check after reboot device', action='store_true')


    test = UninstallApp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
