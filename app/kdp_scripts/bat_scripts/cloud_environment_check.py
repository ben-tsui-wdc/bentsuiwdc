# -*- coding: utf-8 -*-
""" Test cases to check cloud environment.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import GlobalConfigService as GCS


class CloudEnvCheck(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-212 - Environment config Check for Cloud Server'
    TEST_JIRA_ID = 'KDP-212'

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
    parser = KDPInputArgumentParser("""\
        *** Cloud Environment Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/cloud_environment_check.py --uut_ip 10.200.141.103 -env qa1\
        """)

    test = CloudEnvCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
