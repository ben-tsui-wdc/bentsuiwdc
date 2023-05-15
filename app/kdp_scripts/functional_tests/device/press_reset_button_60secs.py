# -*- coding: utf-8 -*-
""" Test cases to check [Factory reset] Press Reset Button >= 60 secs : Factory reset.
"""
__author__ = "Ben Lin <ben.lin@wdc.com>"
__author_2__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time

# platform modules
from pprint import pformat
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.restAPI import RestAPI
from platform_libraries.common_utils import ClientUtils
from platform_libraries.constants import KDP
from kdp_scripts.bat_scripts.factory_reset import FactoryReset


class PressResetButton60secs(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-902 - Press Reset Button >= 60 secs : Factory reset'
    # Popcorn
    TEST_JIRA_ID = 'KDP-902'
    REPORT_NAME = 'Functional'

    SETTINGS = {
        'uut_owner': True
    }

    start = time.time()

    def init(self):
        self.client_utils = ClientUtils()
        self.model = self.uut.get('model')
        if not self.model:
            self.model = self.ssh_client.get_model_name()
        if self.model == 'yodaplus2':
            self.test_apps = ["com.elephantdrive.elephantdrive"]
        else:
            self.test_apps = ["com.plexapp.mediaserver.smb", "com.elephantdrive.elephantdrive"]
        self.new_account = ["wdcautotwtest200+qawdc@gmail.com", "wdcautotwtest201+qawdc@gmail.com"]
        self.new_password = ["Auto1234", "Auto1234"]
        self.test_file = 'TEST_DB_LOCK.png'
        self.test_pass = False
        self.timeout = 300

    def test(self):
        # Get firmware version.
        firmware = self.uut.get('firmware')

        self.log.info("Checking the existing user numbers, attach an owner user if there's no any user")
        stdout, stderr = self.ssh_client.execute_cmd('ls -Al {} | grep auth0 | wc -l'.format(KDP.USER_ROOT_PATH))
        if int(stdout.strip()) == 0:
            self.uut_owner.id = 0
            self.uut_owner.init_session()

        # verify DUT associate with a user
        self.check_owner_exist(self.uut_owner)

        # Install APPs
        for app_id in self.test_apps:
            self.uut_owner.install_app_kdp(app_id=app_id)
            if not self.uut_owner.wait_for_app_install_completed(app_id):
                raise self.err.TestFailure('APP({}) is not install successfully, test Failed !!!'.format(app_id))
            self.log.info('App({}) has been installed.'.format(app_id))

        installed_app_list = self.uut_owner.get_installed_app_id_kdp()
        app_not_installed = set(installed_app_list) ^ set(self.test_apps)
        if app_not_installed:
            raise self.err.TestFailure('Apps: {} was not installed successfully!'.format(app_not_installed))

        # Upload files
        self.log.info('Try to upload a new file by device owner')
        self.client_utils.create_random_file(self.test_file)
        with open(self.test_file, 'rb') as f:
            self.uut_owner.chuck_upload_file(file_object=f, file_name=self.test_file)
        user_id = self.uut_owner.get_user_id(escape=True)
        file_path = '{0}/{1}/{2}'.format(KDP.USER_ROOT_PATH, user_id, self.test_file)
        if self.ssh_client.check_file_in_device(file_path):
            self.log.info('Upload test file to device successfully!')
        else:
            raise self.err.TestFailure('Upload test file to device failed!')

        # Invite(Attach) a new user
        RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env,
                username=self.new_account[0], password=self.new_password[0], init_session=True)

        # Add new files under /data
        self.ssh_client.execute('touch /data/wd/diskVolume0/check_reset.txt')

        # Do factory reset
        self.factory_reset()

        # Verify user can not access DUT
        users, next_page_token = self.uut_owner.get_users(limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(users)))
        if users:
            raise self.err.TestFailure('Check user list is not empty.')

        # Onboard and associate DUT with a new email account
        rest_u2 = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env,
                          username=self.new_account[1], password=self.new_password[1], init_session=False)
        rest_u2.id = 0
        rest_u2.init_session()

        # Check users data by user uploaded
        files = self.ssh_client.execute('find {} -type f'.format(KDP.USER_ROOT_PATH))[0]
        if files:
            raise self.err.TestFailure('Found files: {}'.format(str(files).strip()))

        installed_app_list = rest_u2.get_installed_app_id_kdp()
        if installed_app_list:
            raise self.err.TestFailure('Found installed APPs: {}'.format(installed_app_list))

        # Check firmware version.
        if firmware != self.uut.get('firmware'):
            raise self.err.TestFailure('Firmware version is not match')

        self.test_pass = True

    def after_test(self):
        self.client_utils.delete_local_file(self.test_file)
        if self.test_pass:
            self.log.info("Run factory reset after testing to clean the new owner")
            self.factory_reset()
        else:
            self.log.warning("Keep the test environment since the test was failed")

    def factory_reset(self):
        self.log.info('Reset button press 60 secs and start to do factory reset ...')
        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=False']
        factory_reset = FactoryReset(env_dict)
        factory_reset.no_rest_api = True
        factory_reset.main()
        self.ssh_client.lock_otaclient_service_kdp()

    def check_owner_exist(self, user_obj):
        user_obj.wait_until_cloud_connected(60, as_admin=True)
        users, next_page_token = user_obj.get_users(limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(users)))
        # Check owner in list
        owner_id = user_obj.get_user_id()
        for user in users:
            if user['id'] == owner_id:
                self.log.info('Check owner in list: PASSED')
                return
        self.log.error('Check owner in list: FAILED')
        raise self.err.TestFailure('Check owner in list failed.')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** KDP-902: Press Reset Button >= 60 secs : Factory reset Check Script ***
        Examples: ./run.sh functional_tests/press_reset_button_60secs.py --uut_ip 10.92.224.68\
        """)

    test = PressResetButton60secs(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
