# -*- coding: utf-8 -*-
""" Case to confirm that debug logs can be downloaded from local endpoint with 33284 port
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import urllib2
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class LocalEndpointCanExportDebugLogs(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-235 - Local endpoint access to generate and export debug_logs file'
    TEST_JIRA_ID = 'KDP-235'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.test_url = 'http://{}:33284/cgi-bin/logs.sh'.format(self.env.uut_ip)

    def test(self):
        self.log.info('Start to check 33284 port ...')
        if not self.check_url_file_exists(self.test_url):
            raise self.err.TestFailure('Unauthenticated ports check failed, 33284 port cannot access!')

    def check_url_file_exists(self, url):
        request = urllib2.Request(url)
        request.get_method = lambda: 'HEAD'
        try:
            urllib2.urlopen(request)
            return True
        except (urllib2.HTTPError, urllib2.URLError) as e:
            self.log.warning('Message: {}'.format(e))
            return False


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/local_endpoint_export_debug_logs.py --uut_ip 10.92.224.68\
        """)

    test = LocalEndpointCanExportDebugLogs(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
