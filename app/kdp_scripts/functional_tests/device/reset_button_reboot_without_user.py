# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"
__author_2__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.bat_scripts.factory_reset import FactoryReset
from platform_libraries.restAPI import RestAPI
from platform_libraries.constants import KDP


class ResetButtonRebootWithoutUser(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-898 - MCH - Press Reset Button 1~29 secs : Device reboot - without user associated'
    # Popcorn
    TEST_JIRA_ID = 'KDP-898'
    REPORT_NAME = 'Functional'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        pass

    def before_loop(self):
        pass

    def before_test(self):
        try:
            self._check_user_root(user_number_expected=0)
        except Exception as e:
            self.log.warning('User already exist before testing, run factory reset to clean up devices')
            env_dict = self.env.dump_to_dict()
            env_dict['Settings'] = ['uut_owner=False']
            factory_reset = FactoryReset(env_dict)
            factory_reset.run_rest_api = False
            factory_reset.main()
            self.ssh_client.lock_otaclient_service_kdp()
            self._check_user_root(user_number_expected=0, err_msg='user still exists after factory_reset.')

    def test(self):
        # This is to prevent sometimes device become pingable before rebooting
        if self.ssh_client.check_file_in_device('/tmp/system_ready'):
            self.log.info('Remove the /tmp/system_ready before rebooting the device')
            self.ssh_client.execute_cmd('rm /tmp/system_ready')
        # "reset_button.sh short" is equal to pressing reset_button for 1~29 seconds.
        self.ssh_client.execute_background('reset_button.sh short')
        self.log.info('Expect device do rebooting ...')
        if not self.ssh_client.wait_for_device_to_shutdown():
            raise self.err.TestFailure('Device rebooting Failed !!')
        self.log.info('Device rebooting ...')
        if not self.ssh_client.wait_for_device_boot_completed():
            raise self.err.TestFailure('Device bootup Failed !!')

        if self.env.cloud_env == 'prod':
            with_cloud_connected = False
        else:
            with_cloud_connected = True

        self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env,
                                 username=self.env.username, password=self.env.password,
                                 init_session=False, stream_log_level=self.env.stream_log_level)
        self.uut_owner.id = 0
        self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']},
                                    with_cloud_connected=with_cloud_connected)
        self._check_user_root(user_number_expected=1, err_msg='It\'s failed to onboarding after rebooting device.')

    def _check_user_root(self, user_number_expected=None, err_msg=None):
        self.log.info("Checking the existing user numbers")
        stdout, stderr = self.ssh_client.execute_cmd('ls -Al {} | grep auth0 | wc -l'.format(KDP.USER_ROOT_PATH))
        if int(stdout.strip()) != user_number_expected:
            raise self.err.TestFailure(err_msg)

    def after_test(self):
        pass

    def after_loop(self):
        pass


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Reset Button test on Kamino Android ***
        Examples: ./run.sh functional_tests/reset_button_reboot_without_user.py --uut_ip 10.0.0.28 --cloud_env qa1 --dry_run --debug_middleware\
         --disable_clean_logcat_log """)

    test = ResetButtonRebootWithoutUser(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)