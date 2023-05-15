# -*- coding: utf-8 -*-
""" Test for API: GET /v1/device (KAM-24290).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class GetFeatureFlags(TestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Get Feature Flags'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-24290'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def test(self):
        ret_val = self.uut_owner.get_uut_info()
        self.log.info('API Response: \n{}'.format(pformat(ret_val)))
        self.verify_response(ret_val)

    def verify_response(self, resp):
        if 'features' not in resp:
            raise self.err.TestFailure('No features flags.')
        self.verify_flags(flags=resp['features'])

    def verify_flags(self, flags):
        expected_flags = {}
        # Get expected flags.
        if self.uut['model'] == 'yodaplus':
            expected_flags = {
                'bluetooth': True,
                'ethernetPort': False,
                'hwTranscoding': True,
                'multiDrive': False,
                'powerButton': False,
                'usbPort': True,
                'wifi': True
            }
        elif self.uut['model'] == 'yoda':
            expected_flags = {
                'bluetooth': True,
                'ethernetPort': False,
                'hwTranscoding': False,
                'multiDrive': False,
                'powerButton': False,
                'usbPort': False,
                'wifi': True
            }
        elif self.uut['model'] == 'monarch':
            expected_flags = {
                'bluetooth': False,
                'ethernetPort': True,
                'hwTranscoding': True,
                'multiDrive': False,
                'powerButton': False,
                'usbPort': True,
                'wifi': False
            }
        elif self.uut['model'] == 'pelican':
            expected_flags = {
                'bluetooth': False,
                'ethernetPort': True,
                'hwTranscoding': True,
                'multiDrive': True,
                'powerButton': True,
                'usbPort': True,
                'wifi': False
            }
        else:
            raise self.err.TestSkipped('Unknown model')

        # Check flags
        for k, v in expected_flags.iteritems():
            if k not in flags:
                raise self.err.TestFailure('Field "{}" not found.'.format(k))
            if flags[k] != v:
                raise self.err.TestFailure('Flag vlaue of "{}" is not correct.'.format(k))
        self.log.info('All flags is correct.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** GetFeatureFlags test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/get_feature_flags.py --uut_ip 10.136.137.159\
        """)

    test = GetFeatureFlags(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
