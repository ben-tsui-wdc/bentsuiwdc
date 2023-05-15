# -*- coding: utf-8 -*-
""" Test case to test App Manager Start/Stop.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class AppMgrStopStartTest(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-2058 - App manager start and stop script verify'
    TEST_JIRA_ID = 'KDP-2058'

    def test(self):
        self.log.info('Check kdpappmgr...')
        exitcode, kdpappmgr_pid = self.ssh_client.execute('pidof kdpappmgr')
        assert exitcode == 0 and kdpappmgr_pid, 'Failed to find kdpappmgr'

        self.log.info('Check kdpappmgrd...')
        exitcode, kdpappmgrd_pid = self.ssh_client.execute('pidof kdpappmgrd')
        assert exitcode == 0 and kdpappmgrd_pid, 'Failed to find kdpappmgrd'

        self.log.info('Stopping app manager...')
        self.serial_client.serial_cmd('kdpappmgr.sh stop')
        time.sleep(10)

        self.log.info('Check kdpappmgr...')
        exitcode, output = self.ssh_client.execute('pidof kdpappmgr')
        assert not output, 'kdpappmgr is still running'

        self.log.info('Check kdpappmgrd...')
        exitcode, output = self.ssh_client.execute('pidof kdpappmgrd')
        assert not output, 'kdpappmgrd is still running'

        self.log.info('Starting app manager...')
        self.serial_client.serial_cmd('kdpappmgr.sh start')
        time.sleep(10)

        self.log.info('Check kdpappmgr...')
        exitcode, output = self.ssh_client.execute('pidof kdpappmgr')
        assert exitcode == 0 and output, 'Failed to find kdpappmgr'

        self.log.info('Check kdpappmgrd...')
        exitcode, output = self.ssh_client.execute('pidof kdpappmgrd')
        assert exitcode == 0 and output, 'Failed to find kdpappmgrd'


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** App manager start/stop script verify ***
        """)

    test = AppMgrStopStartTest(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
