# -*- coding: utf-8 -*-
""" Case to check if /var/log/dockerd.log is generated in the test device
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import urllib2
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckDockerLogExist(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-1181 - Confirm docker logs are generated'
    TEST_JIRA_ID = 'KDP-1181'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.dockerd_log_path = '/var/log/dockerd.log'

    def test(self):
        self.log.info('Check if the dockerd log file exists in the test device')
        if self.ssh_client.check_file_in_device(self.dockerd_log_path):
            self.log.info("Dockerd log file exist, test passed!")
        else:
            raise self.err.TestFailure('Cannot find dockerd log file in the test device!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_docker_log_exist.py --uut_ip 10.92.224.68\
        """)

    test = CheckDockerLogExist(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
