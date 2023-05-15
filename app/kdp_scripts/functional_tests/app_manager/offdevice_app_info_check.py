# -*- coding: utf-8 -*-
""" Test case to check apps logs is save to disk.
    https://jira.wdmv.wdc.com/browse/KDP-4064
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import os
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class OffDeviceAppInfoCheck(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-4064 - OffDevice info can get from device'
    TEST_JIRA_ID = 'KDP-4064'

    def declare(self):
        self.app_id = 'com.wdc.mycloud.sonos.offdevice'

    def test(self):
        self.log.info('Start to get offdevice app info...')
        app_info = self.uut_owner.get_app_info_kdp(self.app_id)
        if app_info == 404:
            raise self.err.TestFailure('cannot found {}, test failed !!!'.format(self.app_id))
        get_id = app_info.get('id')
        get_type = app_info.get('info').get('type')
        if get_id != self.app_id:
            raise self.err.TestFailure('app id is not match, test failed !!!')
        if get_type != 'offDevice':
            raise self.err.TestFailure('app type is not offDevice, test failed !!!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** OffDevice info can get from device Test Script ***
        Examples: ./run.sh kdp_scripts/functional_tests/app_manager/offdevice_app_info_check.py --uut_ip 10.92.224.68 -appid com.wdc.mycloud.sonos.offdevice\
        """)

    parser.add_argument('-appid', '--app_id', help='OffDevice App ID ', default='com.wdc.mycloud.sonos.offdevice')

    test = OffDeviceAppInfoCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
