# -*- coding: utf-8 -*-
""" Default S3 bucket URL check for config service test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class DefaultS3BucketUrlCheck(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-5856 - Default S3 bucket URL check'
    TEST_JIRA_ID = 'KDP-5856'

    def test(self):
        self.log.info('Check URL...')
        urls = self.uut_owner.environment.get_service_urls()
        self.log.info(urls['data']['componentMap']['com.wdc.appmanager']['appstore.url'])
        assert {
            'dev1': 'https://dev1-appmanager.wdtest1.com',
            'qa1': 'https://staging-appmanager.dev.wdckeystone.com',
            'prod': 'https://prod-appmanager.wdckeystone.com'
        }[self.uut.get('environment')] == urls['data']['componentMap']['com.wdc.appmanager']['appstore.url'], \
            'URL in config service is not correct'


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Default S3 bucket URL check for config service test ***
        """)

    test = DefaultS3BucketUrlCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
