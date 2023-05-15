# -*- coding: utf-8 -*-
""" Case to confirm that logs will upload to Splunk server when pip is ON
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.restAPI import RestAPI
from platform_libraries.constants import KDP


class LogWillUploadWhenPipIsOnWithThreeUsers(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-326 - Have 3 users onboarded. Logs upload when PIP is enabled'
    TEST_JIRA_ID = 'KDP-326'

    SETTINGS = {
        'uut_owner': True
    }

    def init(self):
        self.analyticpublic_path = '/var/log/analyticpublic.log'
        self.uploaded_folder_path = '/data/kxlog/uploaded'
        self.new_users = ["wdcautotw+qawdc.kdp_functional_user2@gmail.com",
                          "wdcautotw+qawdc.kdp_functional_user3@gmail.com"]
        self.new_password = ["Auto1234", "Auto1234"]

    def test(self):
        self.log.info("*** Step 1: Check owner exist and invite 2 more users")
        self.log.info("Checking the existing user numbers, attach an owner user if there's no any user")
        stdout, stderr = self.ssh_client.execute_cmd('ls -Al {} | grep auth0 | wc -l'.format(KDP.USER_ROOT_PATH))
        if int(stdout.strip()) == 0:
            self.uut_owner.id = 0
            self.uut_owner.init_session()
        self.log.info('Inviting the first user')
        RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env,
                username=self.new_users[0], password=self.new_password[0], init_session=True)
        self.log.info('Inviting the second user')
        RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env,
                username=self.new_users[1], password=self.new_password[1], init_session=True)
        self.log.info("*** Step 2: Enable the Owner PIP status")
        self.uut_owner.enable_pip()

        self.log.info("*** Step 3: Generate a dummy log, run log rotate and upload")
        self.ssh_client.generate_logs(log_number=5, log_type="INFO", log_messages="dummy_test_pip_on")
        self.ssh_client.log_rotate_kdp(force=True)
        self.ssh_client.log_upload_kdp()

        self.log.info("*** Step 4: Check the PIP status is True in the log")
        stdout, stderr = self.ssh_client.execute_cmd('cat {} | grep pip'.format(self.analyticpublic_path))
        if '"pip":"true"' not in stdout:
            raise self.err.TestFailure('The PIP status should be true but it was false!')

        self.log.info("*** Step 5: Check if logs cannot be found in uploaded folder (if folder exist)")
        if self.ssh_client.check_folder_in_device(self.uploaded_folder_path):
            stdout, stderr = self.ssh_client.execute_cmd('grep -r "dummy_test_pip_on" {}'
                                                         .format(self.uploaded_folder_path))
            if not stdout:
                raise self.err.TestFailure('When PIP is enabled, the logs should be found in uploaded folder!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/log_will_upload_when_pip_is_on.py --uut_ip 10.92.224.68\
        """)

    test = LogWillUploadWhenPipIsOnWithThreeUsers(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
