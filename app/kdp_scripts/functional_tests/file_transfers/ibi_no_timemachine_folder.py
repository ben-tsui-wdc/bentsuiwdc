# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"
__compatible__ = 'KDP,RnD'

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class Yodaplus2TimeMachineVerify(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-5717 - ibi_no_timemachine_folder'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5717' # ibi do not have TimeMachineBackup share folder
    SETTINGS = { # Disable all utilities.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        self.smb_conf_location = '/etc/samba'
        self.smb_default_share_conf = None

    def before_test(self):
        if self.uut.get('model') not in ['yodaplus2']:
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(self.uut.get('model')))

    def test(self):
        stdout, stderr = self.ssh_client.execute_cmd('cat {}/smb.conf'.format(self.smb_conf_location))
        for line in stdout.splitlines():
            if 'timemachine' in line or 'TimeMachine' in line:
                raise self.err.TestFailure('There is timemachine configuration in {}/smb.conf.'.format(self.smb_conf_location))
            if '.conf' in line:
                self.smb_default_share_conf = line.split('/')[-1].strip()
        if self.smb_default_share_conf:
            stdout, stderr = self.ssh_client.execute_cmd('cat {}/{}'.format(self.smb_conf_location, self.smb_default_share_conf))
            for line in stdout.splitlines():
                if 'timemachine' in line or 'TimeMachine' in line:
                    raise self.err.TestFailure('There is timemachine configuration in {}/{}.'.format(self.smb_conf_location, self.smb_default_share_conf))

    def after_test(self):
        pass


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** docker test on KDP ***
        Examples: ./run.sh kdp_scripts/functional_tests/file_transfers/XXX.py --uut_ip 10.92.224.71 --cloud_env  qa1 --dry_run --debug_middleware
        """)
    test = Yodaplus2TimeMachineVerify(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)