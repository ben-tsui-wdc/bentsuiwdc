# -*- coding: utf-8 -*-
""" Test case to Install/uninstall app with wrong user authenticated.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class InstallUnistallAppWithWorngToken(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-2350 - Install and uninstall app with wrong user authenticated'
    TEST_JIRA_ID = 'KDP-2350'

    def test(self):
        self.log.info('Install APP with bad token...')
        try:
            self.hide_rest_token()
            code = self.uut_owner.install_app_kdp(app_id='com.plexapp.mediaserver.smb')
            assert code == 401, 'Code is {} which is not 401'.format(code)
        finally:
            self.reveal_rest_token()

        self.log.info('Uninstall APP with bad token...')
        try:
            self.hide_rest_token()
            code = self.uut_owner.uninstall_app_kdp(app_id='com.plexapp.mediaserver.smb')
            assert code == 401, 'Code is {} which is not 401'.format(code)
        finally:
            self.reveal_rest_token()

    def hide_rest_token(self):
        self.save_token = self.uut_owner.id_token
        self.uut_owner.id_token = 'BADTOKEN'

    def reveal_rest_token(self):
        if self.save_token:
            self.uut_owner.id_token = self.save_token
        else:
            self.log.warning('No save token found')
        self.save_token = None


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Install/uninstall app with wrong user authenticated ***
        """)

    test = InstallUnistallAppWithWorngToken(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
