# -*- coding: utf-8 -*-
""" Test cases to check cloud environment.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.constants import GlobalConfigService as GCS


class CloudEnvCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Cloud Environment Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13973'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        cloudEnv = self.adb.executeShellCommand('cat /system/etc/restsdk-server.toml | grep "configURL"')[0]
        check_list = GCS.get(self.env.cloud_env)
        check_list2 = ''
        if 'betamch' in cloudEnv:
            check_list = GCS.get('beta')
        self.log.info('Check URL = {}'.format(check_list))
        if not self.env.cloud_env == 'prod':
            check_list2 = GCS.get('{}_v2'.format(self.env.cloud_env))
            self.log.info('Check URL V2 = {}'.format(check_list2))
        if check_list not in cloudEnv and check_list2 not in cloudEnv:
            raise self.err.TestFailure('Cloud Environment Check Failed !! Build URL: {}'.format(cloudEnv))

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Cloud Environment Check Script ***
        Examples: ./run.sh bat_scripts_new/cloud_environment_check.py --uut_ip 10.92.224.68 --cloud_env dev1\
        """)

    test = CloudEnvCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
