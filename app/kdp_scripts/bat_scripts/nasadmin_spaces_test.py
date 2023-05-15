# -*- coding: utf-8 -*-
""" Spaces management test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.assert_utls import assert_dict
# 3rd party modules
import requests


class NasAdminSpacesTest(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-5514 - nasAdmin - Spaces Management Test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5514'
    ISSUE_JIRA_ID = None

    def test(self):
        space = None
        owner_cloud_user = self.uut_owner.get_cloud_user()
        owner = self.nasadmin.get_owner()
        try:
            space = self.nasadmin.create_space('localSpace')
            expected_space = {
                'userID': '',
                'name': 'localSpace',
                'systemName': '',
                'allUsers': False,
                'localPublic': False,
                'usageBytes': 0,
                'timeMachine': False
            }
            assert_dict(space, expected_space)

            resp = self.nasadmin.get_space(space['id'])
            assert_dict(resp, expected_space)

            resp = self.nasadmin.get_spaces()
            assert len(resp) == 3, "Total number of space is not 3"
            for s in resp:
                if s['systemName']:  # Family space
                    assert_dict(s, {
                        'userID': '',
                        'name': 'Family',
                        'systemName': 'Family',
                        'allUsers': True,
                        'localPublic': False,
                        'usageBytes': 0,
                        'timeMachine': False
                    })
                elif s['userID']:  # Owner space
                    assert_dict(s, {
                        'id': owner['spaceID'],
                        'userID': owner['id'],
                        'name': owner_cloud_user['user_metadata']['first_name'],
                        'systemName': '',
                        'allUsers': False,
                        'localPublic': False,
                        'usageBytes': 0,
                        'timeMachine': False
                    })
                else:  # local space
                    assert_dict(s, expected_space)

            resp = self.nasadmin.update_space(space['id'], name='Space2', allUsers=True)
            expected_space['name'] = 'Space2'
            expected_space['allUsers'] = True
            assert_dict(resp, expected_space)

            resp = self.nasadmin.get_space(space['id'])
            assert_dict(resp, expected_space)

            self.nasadmin.delete_spaces(space['id'])

            try:
                self.nasadmin.get_space(space['id'])
            except requests.HTTPError as e:
                if e.response.status_code != 404:
                    raise self.err.TestFailure('Status code is not 404, response: {}'.format(e))
                self.log.info("Got 404 error as expected")
                space = None
        finally:
            if space:
                self.log.info('Remove existing local space')
                self.nasadmin.delete_spaces(space['id'])


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** nasAdmin - Spaces Management Test ***
        """)

    test = NasAdminSpacesTest(parser)
    resp = test.main()
    print 'test result: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
