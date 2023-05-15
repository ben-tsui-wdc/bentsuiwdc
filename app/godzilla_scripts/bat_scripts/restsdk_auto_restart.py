# -*- coding: utf-8 -*-
""" Test case for RestSDK service auto restart when crashed
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class RestSDKAutoRestart(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'RestSDK Service Auto Restart When Crash'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1341'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = "GZA-593"

    TIMEOUT = 60

    SETTINGS = {
        'uut_owner': False
    }

    def get_restsdk_pid(self):
        stdout, stderr = self.ssh_client.execute_cmd('ps aux | grep restsdk-server | grep -v grep | grep -v restsdk-serverd')
        if stdout:
            restsdk_pid = stdout.strip().split()[0]
            return restsdk_pid
        else:
            return None

    def test(self):
        pid_old = self.get_restsdk_pid()
        self.log.info("Step 1: Get the restsdk service pid(old): {}".format(pid_old))

        self.log.info("Step 2: Kill the restsdk service to simulate it is crashed")
        self.ssh_client.execute_cmd("kill -9 {}".format(pid_old))

        self.log.info("Step 3: Waiting for the restsdk-server to restart automatically")
        start_time = time.time()
        while self.TIMEOUT > time.time() - start_time:
            pid_new = self.get_restsdk_pid()
            if pid_new:
                break
            time.sleep(5)
        self.log.info("pid(new): {}".format(pid_new))
        if pid_old == pid_new:
            raise self.err.TestFailure("The pid of RestSDK service should not be the same after it's restarted!")

        self.log.info("Restart RestSDK service if it's in minimal mode")
        self.ssh_client.disable_restsdk_minimal_mode()

        # Todo: Create new RestSDK instance after testing?
        """ 
        self.log.info("Step 4: Run simple test to check if restsdk-server works properly")
        self.uut_owner.attach_user_to_device()
        self.uut_owner.get_device_info()
        """


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** RestSDK Service Auto Restart When Crash test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/restsdk_auto_restart.py --uut_ip 10.136.137.159\
        """)

    test = RestSDKAutoRestart(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
