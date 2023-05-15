# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from bat_scripts_new.factory_reset import FactoryReset
from platform_libraries.restAPI import RestAPI
from platform_libraries.constants import Kamino


class ResetButtonRebootWithoutUser(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KAM-23588: MCH - Press Reset Button 1~29 secs : Device reboot - without user associated'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-23588'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {'uut_owner':False}


    def declare(self):
        pass


    def before_loop(self):
        pass


    def before_test(self):
        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=False']
        self.log.info('start factory_reset')
        factory_reset = FactoryReset(env_dict)
        factory_reset.no_rest_api = True
        factory_reset.test()
        self.adb.stop_otaclient()
        self._check_user_root(user_number_expected=0, err_msg='user still exists after factory_reset.')


    def test(self):
        # "reset_button.sh short" is equal to pressing reset_button for 1~29 seconds.
        stdout, stderr = self.adb.executeShellCommand('busybox nohup reset_button.sh short', timeout=120)
        self.log.info('Expect device do rebooting ...')
        if not self.adb.wait_for_device_to_shutdown():
            raise self.err.TestFailure('Device rebooting Failed !!')
        self.log.info('Device rebooting ...')
        if not self.adb.wait_for_device_boot_completed():
            raise self.err.TestFailure('Device bootup Failed !!')
            
        if self.env.cloud_env == 'prod':
            with_cloud_connected = False
        else:
            with_cloud_connected = True
        self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
        self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']}, with_cloud_connected=with_cloud_connected)
        self._check_user_root(user_number_expected=1, err_msg='It\'s failed to onboarding after rebooting device.')


    def _check_user_root(self, user_number_expected=None, err_msg=None):
        stdout, stderr = self.adb.executeShellCommand('ls -al {} | wc -l'.format(Kamino.USER_ROOT_PATH))
        if int(stdout.strip()) != user_number_expected:
            raise self.err.TestFailure(err_msg)


    def after_test(self):
        pass


    def after_loop(self):
        pass


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/reset_button_reboot_without_user.py --uut_ip 10.0.0.28 --cloud_env qa1 --dry_run --debug_middleware\
         --disable_clean_logcat_log """)

    test = ResetButtonRebootWithoutUser(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)