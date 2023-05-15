# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: GET /v2/device - 200 - owner attached
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

import sys
# platform modules
from kdp_scripts.test_utils.kdp_test_utils import attach_user, reset_device
from middleware.arguments import KDPInputArgumentParser
# test modules
from get_device import GetDeviceInfo


class GetDeviceInfoFreshDevice(GetDeviceInfo):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Fetch general device information - fresh device'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3799'

    def test(self):
        try:
            reset_device(self)
            resp = self.nasadmin.get_device()
            self.verify_device_info(resp, owner_attached=False)
            if resp['redirectURL']:
                self.tls_access_check(url=resp['redirectURL'])
            else:
                self.log.info('redirectURL is empty, skip the link verify"')
        except Exception as e:
            raise e
        finally:
            try:
                self.log.info("Recover test device - attaching owner")
                attach_user(self)
            except Exception as e:
                self.log.warning(e)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get device information test on fresh device ***
        """)

    test = GetDeviceInfoFreshDevice(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
