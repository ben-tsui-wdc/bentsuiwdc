# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"
__compatible__ = 'KDP,RnD'

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class DockerAutoRestart(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-1180 - docker_auto_restart'
    # Popcorn
    TEST_JIRA_ID = 'KDP-1180'   # The dockerd should be restarted by process "monit" once it is crashed..
    SETTINGS = { # Disable all utilities.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        #self.restsdk_version = False
        self.timeout = 90
        self.proc_tuple = ('dockerd', 'containerd')

    def before_test(self):
        pass

    def test(self):
        for proc in self.proc_tuple:
            self.kill_proc(proc=proc)
            self.check_proc(proc=proc)
            for proc_else in self.proc_tuple:
                if proc_else == proc:
                    pass
                else:
                    self.check_proc(proc=proc_else)

    def kill_proc(self, proc=None):
        stdout, stderr = self.ssh_client.execute_cmd('pidof {}'.format(proc))
        old_pid_proc = stdout.strip()
        self.ssh_client.execute_cmd('kill {}'.format(old_pid_proc))
        stdout, stderr = self.ssh_client.execute_cmd('pidof {}'.format(proc))
        if stdout:
            raise self.err.StopTest("The {} was not killed successfully".format(proc))
        self.log.warning("The {} was killed.".format(proc))

    def check_proc(self, proc=None):
        self.timing.reset_start_time()
        while not self.timing.is_timeout(self.timeout):
            stdout, stderr = self.ssh_client.execute_cmd('pidof {}'.format(proc))
            if stdout:
                break
            else:
                self.log.warning('Did\'t find {} yet, wait for 10 secs and try again ...'.format(proc))
                time.sleep(10)
        else:
            raise self.err.TestFailure("The {} is not re-launched successfully after {} seconds.".format(proc, self.timeout))

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** docker test on KDP ***
        Examples: ./run.sh kdp_scripts/functional_tests/docker/docker_auto_restart.py --uut_ip 10.92.224.71 --cloud_env  qa1 --dry_run --debug_middleware
        """)
    #parser.add_argument('--raid_type', help='The raid type to be tested. Multiple raid types can be used at the same time, separated by comma, for example: span,stripe,mirror. By default is span,stripe,mirror.', default='span,stripe,mirror')


    test = DockerAutoRestart(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)