# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"
__compatible__ = 'KDP,RnD'

# std modules
import re
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class DockerMonit(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-1152 - docker_monit'
    # Popcorn
    TEST_JIRA_ID = 'KDP-1152'
    SETTINGS = { # Disable all utilities.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        pass

    def test(self):
        monit_dic = self.get_monit(component='dockerd')
        if monit_dic['status'] != 'OK':
            raise self.err.TestFailure('The status of dockerd is not OK.')
        if monit_dic['monitoring status'] != 'Monitored':
            raise self.err.TestFailure('The monitoring status of dockerd is not Monitored.')
        if monit_dic['monitoring mode'] != 'active':
            raise self.err.TestFailure('The monitoring mode of dockerd is not active.')

    def get_monit(self, component=None):
        stdout, stderr = self.ssh_client.execute_cmd('monit status {}'.format(component))
        if 'not found' in stdout:
            raise self.err.TestFailure('"{}" doesn\'t exist in "monit status"'.format(component))
        monit_dic = {}
        for item in stdout.split("Process '{}'".format(component))[1].splitlines():
            if item:
                monit_dic.update({item.split('        ')[0].strip(): item.split('        ')[-1].strip()})
        return monit_dic

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** docker test on KDP ***
        Examples: ./run.sh kdp_scripts/functional_tests/docker/docker_monit.py --uut_ip 10.92.224.71 --cloud_env  qa1 --dry_run --debug_middleware
        """)
    test = DockerMonit(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)