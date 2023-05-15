# -*- coding: utf-8 -*-
""" Test case to check the cloud environment
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.constants import GlobalConfigService as GCS


class CloudEnvCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Cloud Environment Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1309'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        self.log.info("Checking cloud environment")
        cloud_env = self.ssh_client.get_restsdk_configurl()

        check_list = GCS.get(self.env.cloud_env)
        self.log.info('Check URL = {}'.format(check_list))

        check_list2 = ''
        if not self.env.cloud_env == 'prod':
            check_list2 = GCS.get('{}_v2'.format(self.env.cloud_env))
            self.log.info('Check URL V2 = {}'.format(check_list2))

        if check_list not in cloud_env and check_list2 not in cloud_env:
            raise self.err.TestFailure('Cloud environment check Failed! Build URL: {}'.format(cloud_env))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Cloud Environment Check test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/cloud_environment_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = CloudEnvCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
