# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"
__compatible__ = 'KDP,RnD'

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class DockerNetworkVerify(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-1153 - docker_network_verify'
    # Popcorn
    TEST_JIRA_ID = 'KDP-1153,KDP-1174'
    SETTINGS = { # Disable all utilities.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        self.container = 'busybox'
        self.ping_count = 10

    def before_test(self):
        # kill running container "busybox" if any
        if self.ssh_client.execute_cmd('docker ps -a | grep {} | grep Up'.format(self.container))[0]:
            self.ssh_client.execute_cmd("docker ps -a | grep {} | grep Up | awk '{{print $1}}' | xargs docker kill".format(self.container))
        if self.ssh_client.execute_cmd('docker ps -a | grep Exit')[0]: 
            self.ssh_client.execute_cmd("docker ps -a | grep Exit | awk '{print $1}' | xargs docker rm")
        stdout, stderr = self.ssh_client.execute_cmd('docker ps -a | grep {}'.format(self.container))
        if stdout:
            raise self.err.TestError('There is still running container "{}".'.format(self.container))
        # pull busybox image
        stdout, stderr = self.ssh_client.execute_cmd('docker pull {}'.format(self.container))

    def test(self):
        self.ssh_client.execute_cmd('docker run -itd --rm {}'.format(self.container))
        stdout, stderr = self.ssh_client.execute_cmd("docker ps -a | grep {}| awk '{{print $1}}'".format(self.container))
        if not stdout:
            raise self.err.TestFailure('There is no running container "{}".'.format(self.container))
        else:
            stdout, stderr = self.ssh_client.execute_cmd('docker exec {} ping www.google.com -c {}'.format(stdout, self.ping_count))
            count = 0
            for line in stdout.splitlines():
                self.log.warning(line)
                if '64 bytes from' in line and 'seq=' in line:
                    count = count + 1
            if float(count)/float(self.ping_count) < 0.8:
                raise self.err.TestFailure("The ping_count is set {}, however, the count of successful ping is {}.".format(self.ping_count, count))

    def after_test(self):
        # kill running container "busybox" if any
        self.ssh_client.execute_cmd("docker ps -a | grep {} | grep Up | awk '{{print $1}}' | xargs docker stop".format(self.container))

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** docker test on KDP ***
        Examples: ./run.sh kdp_scripts/functional_tests/docker/docker_monit.py --uut_ip 10.92.224.71 --cloud_env  qa1 --dry_run --debug_middleware
        """)
    test = DockerNetworkVerify(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
