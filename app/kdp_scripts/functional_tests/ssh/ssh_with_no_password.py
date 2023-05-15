# -*- coding: utf-8 -*-

__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"
__compatible__ = 'KDP'

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from ssh_with_password import SshAccessWithPassword


class SshAccessWithNoPassword(SshAccessWithPassword):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-3307 - SSH access with no password'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3307'
    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        super(SshAccessWithNoPassword, self).init()

    def test(self):
        self.reboot()
        assert self.connect_via_ssh(key_filename=self.ssh_client.key_filename, password=None), \
            'Failed to connect to SSH with no password'

    def after_test(self):
        self.ssh_client.close_all()
        self.ssh_client.connect()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** SSH access with private key has no password required test ***
        """)

    test = SshAccessWithNoPassword(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
