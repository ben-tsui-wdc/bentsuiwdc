# -*- coding: utf-8 -*-
""" Test for getting APP list.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class GetAppList(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-2065 - Get all apps list info'
    TEST_JIRA_ID = 'KDP-2065'

    def init(self):
        self.disable_all_not_installed_check = False

    def test(self):
        id_list_to_verify = ['com.elephantdrive.elephantdrive']
        if 'yodaplus' not in self.uut.get('model'):
            id_list_to_verify += ['com.plexapp.mediaserver.smb', 'com.wdc.nasslurp']

        self.log.info('Getting all APP list')
        resp = self.uut_owner.get_all_app_info_kdp()
        for app in resp['apps']:
            if app['id'] in id_list_to_verify:
                self.log.info('Found APP: {} in list'.format(app['id']))
                id_list_to_verify.remove(app['id'])
                if not self.disable_all_not_installed_check:
                    assert app['state'] == 'notInstalled', \
                        'APP status is not "notInstalled", it shows "{}"'.format(app['state'])
        assert not id_list_to_verify, 'Not found APP in info list: {}'.format(id_list_to_verify)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get all apps list info test ***
        """)
    parser.add_argument('-danic', '--disable_all_not_installed_check',
                        help='Not to check all of APPs are not installed', action='store_true')

    test = GetAppList(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
