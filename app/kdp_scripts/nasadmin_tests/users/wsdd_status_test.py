# -*- coding: utf-8 -*-
""" wsdd.sh process status check test
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class WSDDStatusTest(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-5844,KDP-5845 - wsdd.sh process status checks'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5844,KDP-5845'

    def test(self):
        token = self.nasadmin.login_owner()
        for idx in range(1, 11):
            self.nasadmin.update_user(token['userID'], localAccess=True, username='owner', password='password')
            self.nasadmin.update_user(token['userID'], localAccess=False, username='', password='')
        exit_status, output = self.ssh_client.execute("ps | grep wsdd.sh | grep -v grep | grep 'Z'")
        if output.strip():
            raise self.err.StopTest('Found zombie process')  # KDP-5845
        exit_status, output = self.ssh_client.execute('grep -r "failed to wait WSDD done" /var/log/')
        if output.strip():  # KDP-5844
            raise self.err.StopTest('Found error logs')

    def after_test(self):
        self.log.info('Recovering owner setting...')
        token = self.nasadmin.login_owner()
        self.nasadmin.update_user(token['userID'], localAccess=False, username='', password='')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** wsdd.sh process status check test ***
        """)

    test = WSDDStatusTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
