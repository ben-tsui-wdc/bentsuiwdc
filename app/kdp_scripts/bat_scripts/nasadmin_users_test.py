# -*- coding: utf-8 -*-
""" Users management test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.assert_utls import nsa_assert_user
# 3rd party modules
from deepdiff import DeepDiff


class NasAdminUsersTest(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-5513 - nasAdmin - Users Management Test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5513'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.lite_mode = False

    def test(self):
        owner_cloud_user = self.uut_owner.get_cloud_user()

        if self.lite_mode:
            token = self.nasadmin.login_owner()
            owner = self.nasadmin.get_user(token['userID'])
        else:
            owner = self.nasadmin.get_owner()
        nsa_assert_user(owner_cloud_user, cmp_user=owner, localAccess=False, username="", description="")

        if not self.lite_mode:
            resp = self.nasadmin.get_user(owner['id'])
            diff = DeepDiff(resp, owner)
            assert not diff, "Owner information is changed: {}".format(diff)

            resp = self.nasadmin.get_users()
            assert len(resp) == 1, "Total number of users is more than 1"
            diff = DeepDiff(resp[0], owner)
            assert not DeepDiff(resp[0], owner), "Owner information is changed: {}".format(diff)

        try:
            resp = self.nasadmin.update_user(owner['id'], spaceName='NasOwner', description='OwnerInTest')
            target = owner.copy()
            target['description'] = u'OwnerInTest'
            diff = DeepDiff(resp, target)
            assert not DeepDiff(resp, target), "Owner information is not correct: {}".format(diff)

            resp = self.nasadmin.get_user(owner['id'])
            diff = DeepDiff(resp, target)
            assert not DeepDiff(resp, target), "Owner information is not correct: {}".format(diff)

            if not self.lite_mode:
                resp = self.nasadmin.get_space(owner['spaceID'])
                assert resp['name'] == 'NasOwner', 'Space name is not NasOwner'
        finally:
            self.log.info('Recovering owner info')
            self.nasadmin.update_user(
                owner['id'], spaceName=owner_cloud_user['user_metadata']['first_name'], description=''
            )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** nasAdmin - Users Management Test ***
        """)
    parser.add_argument('-lite', '--lite_mode', help='Execute for lite mode', action='store_true')

    test = NasAdminUsersTest(parser)
    resp = test.main()
    print 'test result: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
