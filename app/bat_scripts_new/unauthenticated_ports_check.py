# -*- coding: utf-8 -*-
""" Case to confirm user should not be able to access unauthenticalted ports.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import urllib2

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class UnauthenticatedPortsCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Unauthenticated Ports Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-29774'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.component_33284_url = 'http://{}:33284/cgi-bin/logs.sh'.format(self.env.uut_ip)
        self.component_80_url = 'http://{}:80/cgi-bin/logs.sh'.format(self.env.uut_ip)
        self.component_81_url = 'http://{}:81/cgi-bin/logs.sh'.format(self.env.uut_ip)
        self.component_21_url = 'http://{}:21/cgi-bin/logs.sh'.format(self.env.uut_ip)
        self.component_22_url = 'http://{}:22/cgi-bin/logs.sh'.format(self.env.uut_ip)
        self.component_23_url = 'http://{}:23/cgi-bin/logs.sh'.format(self.env.uut_ip)
        self.component_8081_url = 'http://{}:8081/cgi-bin/logs.sh'.format(self.env.uut_ip)

    def test(self):
        self.log.info('Start to check 80 port ...')
        if self.check_url_file_exists(self.component_80_url):
            raise self.err.TestFailure('Unauthenticated ports check failed, 80 port can access !!')
        self.log.info('Start to check 81 port ...')
        if self.check_url_file_exists(self.component_81_url):
            raise self.err.TestFailure('Unauthenticated ports check failed, 81 port can access !!')
        self.log.info('Start to check 21 port ...')
        if self.check_url_file_exists(self.component_21_url):
            raise self.err.TestFailure('Unauthenticated ports check failed, 21 port can access !!')
        self.log.info('Start to check 22 port ...')
        if self.check_url_file_exists(self.component_22_url):
            raise self.err.TestFailure('Unauthenticated ports check failed, 22 port can access !!')
        self.log.info('Start to check 23 port ...')
        if self.check_url_file_exists(self.component_23_url):
            raise self.err.TestFailure('Unauthenticated ports check failed, 23 port can access !!')
        self.log.info('Start to check 8081 port ...')
        if self.check_url_file_exists(self.component_8081_url):
            raise self.err.TestFailure('Unauthenticated ports check failed, 8081 port can access !!')
        self.log.info('Start to check 33284 port ...')
        if not self.check_url_file_exists(self.component_33284_url):
            raise self.err.TestFailure('Unauthenticated ports check failed, 33284 port cannot access !!')

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
    parser = InputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh bat_scripts/unauthenticated_ports_check.py --uut_ip 10.92.224.68\
        """)

    test = UnauthenticatedPortsCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
