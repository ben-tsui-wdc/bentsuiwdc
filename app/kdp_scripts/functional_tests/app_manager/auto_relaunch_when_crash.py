# -*- coding: utf-8 -*-
""" App manager auto re-launch check when crashed test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class AutoReLaunchWhenCrash(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-1938 - App manager auto re-launch check when crashed'
    TEST_JIRA_ID = 'KDP-1938'

    def test(self):
        self.log.info('Check kdpappmgr...')
        exitcode, kdpappmgr_pid = self.ssh_client.execute('pidof kdpappmgr')
        assert exitcode == 0 and kdpappmgr_pid, 'Failed to find kdpappmgr'

        self.log.info('Kill kdpappmgr...')
        exitcode, _ = self.ssh_client.execute('kill -9 {}'.format(kdpappmgr_pid))
        assert exitcode == 0, 'Failed to kill kdpappmgr'

        self.log.info('Check kdpappmgr...')
        for idx in xrange(12):
            try:
                exitcode, output = self.ssh_client.execute('pidof kdpappmgr')
                assert exitcode == 0 and output, 'Failed to find kdpappmgr'
                assert output != kdpappmgr_pid, 'PID of kdpappmgr is not changed, seem failed to relaunch'
                break
            except Exception as e:
                if idx == 11:
                    raise
                self.log.info('Got an error: {}'.format(e))
                time.sleep(5)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** App manager auto re-launch check when crashed test ***
        """)

    test = AutoReLaunchWhenCrash(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
