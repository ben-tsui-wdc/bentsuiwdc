# -*- coding: utf-8 -*-
""" Test for API: DELETE /v1/device (KAM-19216).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.constants import Kamino


class FactoryRestoreTest(TestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Factory Restore'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-19216'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def test(self):
        self.uut_owner.factory_reset()
        self.verify_result()

    def verify_result(self):
        # Device status: API Call -> Reboot -> Do Factory Restore (~5 min or more without network) -> Reboot -> Boot complete
        self.wait_reboot(timeout=60*5)
        sleep_time = 60*5
        self.log.info('Sleep {}s for waiting factory restore process'.format(sleep_time))
        time.sleep(sleep_time)
        self.wait_boot_completed(timeout=60*30)
        self.check_user_root()
 
    # TODO: Move to lib
    def wait_reboot(self, timeout):
        self.log.info('Expect device do reboot in {}s.'.format(timeout))
        if not self.adb.wait_for_device_to_shutdown(timeout=timeout):
            raise self.err.TestFailure('Reboot device failed')
        self.log.info('Reboot device success.')

    def wait_boot_completed(self, timeout):
        self.log.info('Wait for device boot completed in {}s'.format(timeout))
        if not self.adb.wait_for_device_boot_completed(timeout=timeout):
            raise self.err.TestFailure('Device seems down.')
        self.log.info('Device boot completed.')

    def check_user_root(self):
        stdout, stderr = self.adb.executeShellCommand('ls -al {} | wc -l'.format(Kamino.USER_ROOT_PATH))
        stdout = stdout.strip()
        if not stdout.isdigit():
            raise self.err.TestFailure('Unknown failure when check user root.')
        if int(stdout):
            raise self.err.TestFailure('Wipe user root failed')
        self.log.info('Wipe user root completed.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Factory_Restore test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/factory_restore.py --uut_ip 10.136.137.159\
        """)

    test = FactoryRestoreTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
