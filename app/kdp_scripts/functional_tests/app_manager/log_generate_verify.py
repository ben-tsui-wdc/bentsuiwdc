# -*- coding: utf-8 -*-
""" Log generate verify for app manager service test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class LogGenerateVerify(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-2064 - Log generate verify for app manager service'
    TEST_JIRA_ID = 'KDP-2064'

    def test(self):
        self.log.info('Check kdpappmgr...')
        exitcode, kdpappmgr_pid = self.ssh_client.execute('pidof kdpappmgr')
        assert exitcode == 0 and kdpappmgr_pid, 'Failed to find kdpappmgr'

        self.log.info('Check kdpappmgrd...')
        exitcode, kdpappmgrd_pid = self.ssh_client.execute('pidof kdpappmgrd')
        assert exitcode == 0 and kdpappmgrd_pid, 'Failed to find kdpappmgrd'

        self.log.info('Deleting device logs...')
        exitcode, _ = self.ssh_client.execute('rm -rf /var/log/appMgr.log*')
        assert exitcode == 0, 'Failed to delete logs'

        self.log.info('Reload rsyslog service...')
        exitcode, _ = self.ssh_client.execute('rsyslog.sh reload')
        assert exitcode == 0, 'Failed to reload rsyslog service'

        self.log.info('Restarting app manager...')
        self.serial_client.serial_cmd('kdpappmgr.sh restart')
        time.sleep(10)

        self.log.info('Check device logs...')
        exitcode, _ = self.ssh_client.execute('ls /var/log/appMgr.log')
        assert exitcode == 0, 'Failed to find logs'

        self.log.info('Check kdpappmgr...')
        exitcode, output = self.ssh_client.execute('pidof kdpappmgr')
        assert exitcode == 0 and output, 'Failed to find kdpappmgr'
        assert output != kdpappmgr_pid, 'PID of kdpappmgr is not changed, seem failed to restart'

        self.log.info('Check kdpappmgrd...')
        exitcode, output = self.ssh_client.execute('pidof kdpappmgrd')
        assert exitcode == 0 and output, 'Failed to find kdpappmgrd'
        assert output != kdpappmgrd_pid, 'PID of kdpappmgrd is not changed, seem failed to restart'


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Log generate verify for app manager service test ***
        """)

    test = LogGenerateVerify(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
