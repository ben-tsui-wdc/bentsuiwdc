# -*- coding: utf-8 -*-
""" Test for API: GET /v1/device (KAM-16642).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class GetDeviceInfoTest(KDPTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Get device information testing'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-923'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }

    def test(self):
        ret_val = self.uut_owner.get_uut_info()
        self.log.info('API Response: \n{}'.format(pformat(ret_val)))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get_Device_info test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/get_device_info.py --uut_ip 10.136.137.159\
        """)

    test = GetDeviceInfoTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
