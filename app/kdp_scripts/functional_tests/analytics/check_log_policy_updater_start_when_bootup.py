# -*- coding: utf-8 -*-
""" Case to check the log policy updater job is executed when device boot up
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckLogPolicyUpdaterStartWhenBootUp(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-2007 - [ANALYTICS] Check the log policy updater execute when device boot up'
    TEST_JIRA_ID = 'KDP-2007'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.test_log_file = '/var/log/analyticpublic.log'

    def test(self):
        self.log.info("*** Step 1: Trigger log force rotate and force upload to make sure no log file exist")
        self.ssh_client.log_rotate_kdp(force=True)
        self.ssh_client.log_upload_kdp()
        if self.ssh_client.check_file_in_device("{}.1".format(self.test_log_file)):
            raise self.err.TestFailure('The rotated file was not cleaned up after log upload!')

        self.log.info("*** Step 2: Restart logpp with debug mode ON")
        self.ssh_client.restart_logpp(debug_mode=True)

        self.log.info("*** Step 3: Check the log clearner execute after logpp restart")
        stdout, stderr = self.ssh_client.execute_cmd(
            'grep -r \'"msgid":"LogPP","work":"PolicyScheduler","message":"successfully added"\' {}'.format(self.test_log_file))
        if not stdout:
            raise self.err.TestFailure('LogClearer task was not executed after logpp restart!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_log_policy_updater_start_when_bootup.py --uut_ip 10.92.224.68\
        """)

    test = CheckLogPolicyUpdaterStartWhenBootUp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
