# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"
__compatible__ = 'KDP,RnD'

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class DockerCgroupMount(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-1151 - docker_cgroup_mount'
    # Popcorn
    TEST_JIRA_ID = 'KDP-1151'
    SETTINGS = { # Disable all utilities.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        self.cgroup_path = '/sys/fs/cgroup'

    def test(self):
        for component in ('memory', 'cpu'):
            self.mnt_path_chk(component=component)
            self.content_chk(component=component)

    def mnt_path_chk(self, component=None):
        stdout, stderr = self.ssh_client.execute_cmd('mount  | grep cgroup | grep "{} "'.format(component))
        if '{}/{}'.format(self.cgroup_path, component) in stdout:
            return True
        else:
            raise self.err.TestFailure('{} doesn\'t exis in mount path ({}) by command "mount"'.format(component, self.cgroup_path))

    def content_chk(self, component=None):
        stdout, stderr = self.ssh_client.execute_cmd('ls {}/{}/docker'.format(self.cgroup_path, component))
        if 'No such file or directory' in stdout:
            raise self.TestFailure('The folder {}/{}/docker doesn\'t exist.'.format(self.cgroup_path, component)) 
        for item in ('tasks', 'cgroup.procs', '{}.stat'.format(component)):
            if item not in stdout:
                raise self.err.TestFailure('The "{}" doesn\'t exist in {}/{}/docker'.format(item, self.cgroup_path, component)) 


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** docker test on KDP ***
        Examples: ./run.sh kdp_scripts/functional_tests/docker/cgroup_mount.py --uut_ip 10.92.224.71 --cloud_env  qa1 --dry_run --debug_middleware
        """)
    test = DockerCgroupMount(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)