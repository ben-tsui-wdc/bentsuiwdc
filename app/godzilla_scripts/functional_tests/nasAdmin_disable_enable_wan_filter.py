# -*- coding: utf-8 -*-
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class NasAdminDisableEnableWANFilter(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'nasAdmin Disable and Enable WAN Filter'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-8762'
    PRIORITY = 'Critical'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        self.log.info("Disable the WAN Filter enabled flag and check the status")
        self.ssh_client.set_wan_filter_enabled_flag(enabled=False)
        result = self.ssh_client.get_wan_filter_enabled_flag()
        if result.get("enabled"):
            raise self.err.TestFailure('Failed to change the WAN Filter enabled flag!')

        self.log.info("Enable the WAN Filter enabled flag and check the status")
        self.ssh_client.set_wan_filter_enabled_flag(enabled=True)
        result = self.ssh_client.get_wan_filter_enabled_flag()
        if not result.get("enabled"):
            raise self.err.TestFailure('Failed to change the WAN Filter enabled flag!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Add Public Share And Check Samba RW on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/nasAdmin_disable_enable_wan_filter.py.py --uut_ip 10.136.137.159 -env qa1 \
        """)
    test = NasAdminDisableEnableWANFilter(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
