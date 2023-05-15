# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"
__compatible__ = 'KDP,RnD'

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class DockerRootDirMountVerify(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-1149 - docker_root_directory_mount_verify'
    # Popcorn
    TEST_JIRA_ID = 'KDP-1149'
    SETTINGS = { # Disable all utilities.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        pass

    def test(self):
        device_vol_path = self.ssh_client.getprop(name='device.feature.vol.path')
        docker_mount_path = '{}/Nas_Prog/_docker'.format(device_vol_path)
        stdout, stderr = self.ssh_client.execute_cmd('df | grep {} | grep docker'.format(device_vol_path))
        if docker_mount_path not in stdout:
            raise self.err.TestFailure('"Nas_Prog/_docker" doesn\'t exist in {} by "df" command.'.format(device_vol_path))
        stdout, stderr = self.ssh_client.execute_cmd('ls -al   /var/lib | grep docker')
        if "docker -> {}".format(docker_mount_path) not in stdout:
            raise self.err.TestFailure('The symbolic link of docker doesn\'t exist in /var/lib.')
        stdout, stderr = self.ssh_client.execute_cmd('ls -al {}'.format(docker_mount_path))
        for check_item in ('buildkit', 'containers' ,'containerd' ,'image'):
            check_flag = False
            for item in stdout.splitlines():
                if item.split()[-1] == check_item:
                    check_flag = True
                    break
            if not check_flag:
                raise self.err.TestFailure('The {} doesn\'t exist in {}'.format(check_item, docker_mount_path))

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** docker test on KDP ***
        Examples: ./run.sh kdp_scripts/functional_tests/docker/docker_auto_restart.py --uut_ip 10.92.224.71 --cloud_env  qa1 --dry_run --debug_middleware
        """)
    test = DockerRootDirMountVerify(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)