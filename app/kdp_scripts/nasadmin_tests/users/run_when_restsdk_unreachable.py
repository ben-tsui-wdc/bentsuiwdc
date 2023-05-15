# -*- coding: utf-8 -*-
""" user/space works when RestSDK unreachable test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class RunWhenRestsdkUnreachable(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-5947 - user/space works when RestSDK unreachable'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5947'

    def declare(self):
        self.test_pass = False

    def test(self):
        cloud_token = self.uut_owner.owner_access_token
        self.log.info('Simulating nasAdmin works when RestSDK unreachable')
        self.ssh_client.stop_restsdk_service()
        self.ssh_client.restart_nasadmin_service()
        self.nasadmin.wait_for_nasAdmin_works()
        token = self.nasadmin.login_with_cloud_token(cloud_token)
        self.nasadmin.get_user(token['userID'])
        self.log.info('Simulating nasAdmin works when RestSDK is responsible')
        self.ssh_client.start_restsdk_service()
        self.log.info('Checking message: "start polling sdk" in logs')
        for idx in xrange(6*5):
            exit_status, output = self.ssh_client.execute('grep -r "start polling sdk" /var/log/')
            if exit_status is 0:
                self.test_pass = True
                break
            time.sleep(10)
        else:
            raise AssertionError('Not found message: "start polling sdk" in logs')

    def after_test(self):
        if not self.test_pass:
            self.ssh_client.restart_restsdk_service()
            self.uut_owner.wait_for_restsdk_works()
            self.ssh_client.restart_nasadmin_service()
            self.nasadmin.wait_for_nasAdmin_works()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** User/space works when RestSDK unreachable test ***
        """)
    test = RunWhenRestsdkUnreachable(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
