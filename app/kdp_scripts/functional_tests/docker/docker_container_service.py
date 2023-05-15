# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"
__compatible__ = 'KDP,RnD'

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class DockerContainerService(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-1176 - docker_contianer_service'
    # Popcorn
    TEST_JIRA_ID = 'KDP-1176'
    SETTINGS = { # Disable all utilities.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        self.container = 'ubuntu'
        self.timestamp = time.time()

    def before_test(self):
        pass

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
        # touch a timestamp file
        stdout, stderr = self.ssh_client.execute_cmd('touch /var/log/{}'.format(self.timestamp))

    def test(self):
        self.ssh_client.execute_cmd('docker run -dit -P --rm --name ubuntu_test_mount -v /var/log:/log {}'.format(self.container))
        stdout, stderr = self.ssh_client.execute_cmd("docker ps -a | grep {}| awk '{{print $1}}'".format(self.container))
        if not stdout:
            raise self.err.TestFailure('There is no running container "{}".'.format(self.container))
        else:
            # Get the items in /var/log of DUT
            items_DUT, stderr = self.ssh_client.execute_cmd("ls /var/log")
            self.log.warning(items_DUT)
            # Get the items in /log of container
            items_container, stderr = self.ssh_client.execute_cmd('docker exec {} ls /log'.format(stdout))
            if items_DUT != items_container:
                raise self.err.TestFailure('The items is different between "/var/log of DUT" and "/log of container".')

    def after_test(self):
        # kill running container "busybox" if any
        self.ssh_client.execute_cmd("docker ps -a | grep {} | grep Up | awk '{{print $1}}' | xargs docker stop".format(self.container))
        # Remove the touch file which is only for this test case
        stdout, stderr = self.ssh_client.execute_cmd('rm -f /var/log/{}'.format(self.timestamp))

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** docker test on KDP ***
        Examples: ./run.sh kdp_scripts/functional_tests/docker/docker_monit.py --uut_ip 10.92.224.71 --cloud_env  qa1 --dry_run --debug_middleware
        """)
    test = DockerContainerService(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)