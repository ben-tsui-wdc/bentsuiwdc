# -*- coding: utf-8 -*-
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class NasAdminDisableEnableTLSRedirect(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'nasAdmin Disable and Enable TLS Redirect'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-8761'
    PRIORITY = 'Critical'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        self.log.info("Disable the TLS redirect flag and check the url is empty")
        self.ssh_client.set_tls_redirect_enabled_flag(enabled=False)
        result = self.ssh_client.get_tls_redirect_enabled_flag()
        if result.get("enabled"):
            raise self.err.TestFailure('Failed to change the TLS redirect enabled flag!')

        result = self.ssh_client.get_tls_info()
        if result.get("redirect_url"):
            raise self.err.TestFailure('The TLS redirect_url should have been empty after it is disabled!')

        self.log.info("Enable the TLS redirect flag and check the url is not empty")
        self.ssh_client.set_tls_redirect_enabled_flag(enabled=True)
        result = self.ssh_client.get_tls_redirect_enabled_flag()
        if not result.get("enabled"):
            raise self.err.TestFailure('Failed to change the TLS redirect enabled flag!')

        result = self.ssh_client.get_tls_info()
        if not result.get("redirect_url"):
            raise self.err.TestFailure('The TLS redirect_url should not have been empty after it is enabled!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Add Public Share And Check Samba RW on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/nasAdmin_disable_enable_tls_redirect.py.py --uut_ip 10.136.137.159 -env qa1 \
        """)
    test = NasAdminDisableEnableTLSRedirect(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
