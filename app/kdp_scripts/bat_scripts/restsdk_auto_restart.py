# -*- coding: utf-8 -*-
""" Test case for RestSDK service auto restart when crashed
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.bat_scripts.check_cloud_service import CheckCloudService


class RestSDKAutoRestart(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-1022 - Restsdk server auto-restart when crash'
    TEST_JIRA_ID = 'KDP-1022, KDP-204'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.timeout = 60

    def test(self):
        pid_old = self.get_restsdk_pid()
        self.log.info("Step 1: Get the restsdk service pid(old): {}".format(pid_old))

        self.log.info("Step 2: Kill the restsdk service to simulate it is crashed")
        self.ssh_client.execute_cmd("kill -9 {}".format(pid_old))

        self.log.info("Step 3: Waiting for the restsdk-server to restart automatically")
        start_time = time.time()
        while self.timeout > time.time() - start_time:
            pid_new = self.get_restsdk_pid()
            if pid_new: break
            time.sleep(5)
        self.log.info("pid(new): {}".format(pid_new))
        if pid_old == pid_new:
            raise self.err.TestFailure("The pid of RestSDK service should not be the same after it's restarted!")

        self.log.info("Simple check to confirm restsdk service is working properly")
        self.ssh_client.check_restsdk_service()
        check_cloud_service = CheckCloudService(self)
        check_cloud_service.test()

    def get_restsdk_pid(self):
        restsdk_pid = self.ssh_client.execute_cmd('pidof restsdk-server')[0]
        if restsdk_pid: return restsdk_pid
        else: return None


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** RestSDK Service Auto Restart When Crash test for Godzilla devices ***
        Examples: ./run.sh kdp_scripts/bat_scripts/restsdk_auto_restart.py --uut_ip 10.136.137.159\
        """)

    test = RestSDKAutoRestart(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
