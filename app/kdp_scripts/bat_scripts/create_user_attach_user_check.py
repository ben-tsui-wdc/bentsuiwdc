# -*- coding: utf-8 -*-
""" Test cases to check user can attach to device.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CreateUserAttachUser(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-192 - Create User & Attach User Check'
    # Popcorn
    TEST_JIRA_ID = 'KDP-192'

    SETTINGS = {
        'uut_owner': True
    }

    def test(self):
        device_ready = self.ssh_client.get_device_ready_status()
        proxy_connected = self.ssh_client.get_device_proxy_connect_status()
        if device_ready and proxy_connected:
            users, next_page_token = self.uut_owner.get_users(limit=1000)
            self.log.info('API Response: \n{}'.format(pformat(users)))
            self.verify_result(users)
        else:
            raise self.err.TestSkipped('Device not ready, Skipped the test !!')

    def verify_result(self, users):
        # Check owner in list
        owner_id = self.uut_owner.get_user_id()
        for user in users:
            if user['id'] == owner_id:
                self.log.info('Check owner in list: PASSED')
                return
        self.log.error('Check owner in list: FAILED')
        raise self.err.TestFailure('Check owner in list failed.')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Create User & Attach User Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/create_user_attach_user_check.py --uut_ip 10.92.224.68\
        """)

    test = CreateUserAttachUser(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
