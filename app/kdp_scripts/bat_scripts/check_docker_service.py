# -*- coding: utf-8 -*-
""" Check docker service is launch on the device
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckDockerService(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-1011 - Check Docker service'
    TEST_JIRA_ID = 'KDP-1011'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        exitcode, _ = self.ssh_client.execute('pidof dockerd')
        if exitcode != 0: raise self.err.TestFailure("dockerd process not found")
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60): # Wait for containerd start up
            exitcode, _ = self.ssh_client.execute('pidof containerd')
            if exitcode != 0: 
                self.log.warning("containerd process is not found, wait for 5 secs and try again...")
                time.sleep(5)
            else:
                break
        else:
            raise self.err.TestFailure("containerd process still not found after retry for 1 min")

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Check Docker Service Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/check_docker_service.py --uut_ip 10.92.224.68\
        """)

    test = CheckDockerService(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
