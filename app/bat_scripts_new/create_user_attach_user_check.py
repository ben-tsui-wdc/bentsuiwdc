# -*- coding: utf-8 -*-
""" Test cases to check user can attach to device.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>", "Estvan Huang <estvan.huang@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class CreateUserAttachUser(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Create User & Attach User Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13980'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': True
    }

    def test(self):
        self.uut_owner.wait_until_cloud_connected(60)
        users, next_page_token = self.uut_owner.get_users(limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(users)))
        self.verify_result(users)

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
    parser = InputArgumentParser("""\
        *** Create User & Attach User Check Script ***
        Examples: ./run.sh bat_scripts/create_user_attach_user_check.py --uut_ip 10.92.224.68\
        """)

    test = CreateUserAttachUser(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
