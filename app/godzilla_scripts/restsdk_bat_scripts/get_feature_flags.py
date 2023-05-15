# -*- coding: utf-8 -*-
""" Test for API: GET /v1/device (KAM-24290).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class GetFeatureFlags(GodzillaTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Get Feature Flags'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1739'
    PRIORITY = 'Blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def before_test(self):
        if self.env.model in ("PR2100", "PR4100"):
            self.hw_transcoding = True
        elif self.env.model == "Sequoia":
            self.hw_transcoding = False
        else:
            self.hw_transcoding = False

    def test(self):
        # Todo: there's no model field in the response right now
        ret_val = self.uut_owner.get_uut_info()
        self.log.info('API Response: \n{}'.format(pformat(ret_val)))
        self.verify_response(ret_val)

    def verify_response(self, resp):
        if 'features' not in resp:
            raise self.err.TestFailure('No features flags.')
        self.verify_flags(flags=resp['features'])

    def verify_flags(self, flags):
        expected_flags = {
            'bluetooth': False,
            'ethernetPort': True,
            'hwTranscoding': self.hw_transcoding,
            'multiDrive': True,
            'powerButton': False,
            'usbPort': True,
            'wifi': False
        }

        # Check flags
        for k, v in expected_flags.iteritems():
            if k not in flags:
                raise self.err.TestFailure('Field "{}" not found.'.format(k))
            if flags[k] != v:
                raise self.err.TestFailure('Flag vlaue of "{}" is not correct.'.format(k))
        self.log.info('All flags is correct.')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** GetFeatureFlags test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/get_feature_flags.py --uut_ip 10.136.137.159\
        """)

    test = GetFeatureFlags(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
