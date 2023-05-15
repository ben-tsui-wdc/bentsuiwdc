# -*- coding: utf-8 -*-

__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"
__compatible__ = 'KDP'

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class NoP2p0Check(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-434 - No p2p0 interface in ifconfig'
    # Popcorn
    TEST_JIRA_ID = 'KDP-434'

    def test(self):
        exitcode, output = self.ssh_client.execute("ifconfig")
        assert exitcode == 0, 'Failed to execute "ifconfig"'
        assert 'p2p0' not in output, 'Found p2p0 interface'


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** No p2p0 interface in ifconfig test ***
        """)

    test = NoP2p0Check(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)