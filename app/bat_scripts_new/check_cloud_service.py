# -*- coding: utf-8 -*-
""" Check cloud services via RestAPI by verifying "cloudConnected" field.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class CheckCloudService(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Check Cloud Service'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13979'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': True
    }

    def test(self):
        try:
            self.uut_owner.wait_until_cloud_connected()
        except Exception as ex:
            self.log.exception(str(ex))
            raise self.err.TestFailure(str(ex))

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Check Cloud Service Script ***
        Examples: ./run.sh bat_scripts/check_cloud_service.py --uut_ip 10.92.224.68\
        """)

    test = CheckCloudService(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
