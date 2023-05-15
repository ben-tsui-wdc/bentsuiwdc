# -*- coding: utf-8 -*-
""" Test case to check apps logs is save to disk.
    https://jira.wdmv.wdc.com/browse/KDP-4062
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import os
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class LogsToDiskCheck(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-4062 - Logs To Disk Check'
    TEST_JIRA_ID = 'KDP-4062'

    def declare(self):
        self.uninstall_app = False
        self.app_id = 'com.plexapp.mediaserver.smb'

    def before_test(self):
        if self.uut_owner.get_app_state_kdp(self.app_id) == 'installed':
            self.log.info('{} already installed, no need to install again'.format('self.app_id'))
        else:
            self.uut_owner.install_app_kdp(self.app_id)
            if not self.uut_owner.wait_for_app_install_completed(self.app_id):
                raise self.err.TestSkipped('APP({}) is not install successfully, skipped the test...'.format(self.app_id))

    def test(self):
        self.log.info('Start to check apps logs is save to disk ...')
        user_id = self.uut_owner.get_user_id(escape=True)
        logs_return = self.ssh_client.execute_cmd('ls /data/wd/diskVolume0/kdpappmgr/logs/{0}/{1}'
                                                    .format(self.app_id, user_id))[0]
        if not logs_return:
            raise self.err.TestFailure('logs files are not exist, test failed !!!')

    def after_test(self):
        if self.uninstall_app:
            self.log.info('uninstall_app is true, start to uninstall App({}) ...'.format(self.app_id))
            self.uut_owner.uninstall_app(self.app_id)
            if not self.uut_owner.wait_for_app_uninstall_completed(self.app_id):
                self.log.error('Failed to uninstall app ...')

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Logs To Disk Check Test Script ***
        Examples: ./run.sh kdp_scripts/functional_tests/app_manager/logs_to_disk_check.py --uut_ip 10.92.224.68 -appid com.plexapp.mediaserver.smb\
        """)

    parser.add_argument('-appid', '--app_id', help='App ID to uninstalled', default='com.plexapp.mediaserver.smb')
    parser.add_argument('-uninstall_app', '--uninstall_app', help='Uninstall installed app after test', action='store_true')

    test = LogsToDiskCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
