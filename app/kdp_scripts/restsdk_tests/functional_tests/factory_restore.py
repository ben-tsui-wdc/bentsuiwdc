# -*- coding: utf-8 -*-
""" Test for API: DELETE /v1/device (KAM-19216).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP


class FactoryRestoreTest(KDPTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Factory Restore'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-917'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = 'KDP-1079'

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }

    def test(self):
        self.uut_owner.factory_reset()
        self.verify_result()

    def verify_result(self):
        # Device status: API Call -> Reboot -> Do Factory Restore (Wait for 30 min at most without network) -> Reboot -> Boot complete
        self.wait_reboot(timeout=60*30)
        sleep_time = 60*5
        self.log.info('Sleep {}s for waiting factory restore process'.format(sleep_time))
        time.sleep(sleep_time)
        self.wait_boot_completed(timeout=60*30)
        self.check_user_root()
 
    # TODO: Move to lib
    def wait_reboot(self, timeout):
        self.log.info('Expect device do reboot in {}s.'.format(timeout))
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=timeout):
            raise self.err.TestFailure('Reboot device failed')
        self.log.info('Reboot device success.')

    def wait_boot_completed(self, timeout):
        self.log.info('Wait for device boot completed in {}s'.format(timeout))
        if not self.ssh_client.wait_for_device_boot_completed(timeout=timeout):
            raise self.err.TestFailure('Device seems down.')
        self.log.info('Device boot completed.')

    def check_user_root(self):
        stdout, stderr = self.ssh_client.execute_cmd('ls -l {} | wc -l'.format(KDP.USER_ROOT_PATH))
        stdout = stdout.strip()
        if not stdout.isdigit():
            raise self.err.TestFailure('Unknown failure when check user root.')
        if int(stdout) > 2:
            # check on 8.10.0-116:
            # root@MyCloud-69TA6K  # ls -l /data/wd/diskVolume0/userStorage
            # -rw-------    1 root     restsdk          2 Aug 19 05:57 devicePermBackup.json
            # drwx------    2 root     restsdk       4096 Aug 19 05:57 trash
            raise self.err.TestFailure('Wipe user root failed')
        self.log.info('Wipe user root completed.')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Factory_Restore test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/factory_restore.py --uut_ip 10.136.137.159\
        """)

    test = FactoryRestoreTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
