# -*- coding: utf-8 -*-

__author1__ = "Ben Tsui <ben.tsui@wdc.com>"
__author2__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.restAPI import RestAPI


class LEDPowerStateReady(KDPTestCase):

    TEST_SUITE = "Led Test"
    TEST_NAME = "KDP-772 - [LED] Power State Ready"
    # Popcorn
    TEST_JIRA_ID = 'KDP-772'
    SETTINGS = { # Disable all utilities.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }


    def init(self):
        self.led_power_ready = False
        self.sys_power_ready = False
        self.timeout = 600


    def test(self):
        self.log.info("Execute reboot on test device")
        stdout, stderr = self.ssh_client.execute_cmd('do_reboot')
        self.log.info('Wait 10 seconds and then check if boot complete')
        time.sleep(10)
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=self.timeout):
            raise self.err.TestFailure('Device was not shut down successfully!')
        if not self.ssh_client.wait_for_device_boot_completed(timeout=self.timeout):
            raise self.err.TestFailure('Device was not boot up successfully!')
        self.check_device_is_ready()
        led_list = self.ssh_client.get_led_logs(cmd='cat /var/log/analyticpublic.log*  | grep led_ctrl_server | sort')
        self.ssh_client.print_led_info(led_list)
        for i, led_info in enumerate(led_list):
            if self.uut.get('model') in ('yodaplus', 'yodaplus2'):
                # Check sys state change
                if all([led_info.get('type') == 'SYS',
                        led_info.get('before') == 'Power up',
                        led_info.get('after') == 'BLE Started']):
                    self.sys_power_ready = True
                elif all([led_info.get('type') == 'SYS',
                          led_info.get('after') == 'BLE Started']):
                    # When yoda connect wi-fi slower than we expected
                    self.sys_power_ready = True
                # Check led state change
                if all([led_info.get('type') == 'LED',
                          led_info.get('before') == 'Slow Breathing',
                          led_info.get('after') == 'Full Solid']):
                    # http://jira.wdmv.wdc.com/browse/KAM200-3948
                    self.led_power_ready = True
                elif all([led_info.get('type') == 'LED',
                          led_info.get('before') == 'Fast Breathing',
                          led_info.get('after') == 'Full Solid']):
                    # When yoda connects wi-fi slower than we expected
                    # That means DUT doesn't connect to cloud yet which caused PROXY error.
                    # At that time, LED will be "Fast Breathing".
                    self.led_power_ready = True
            else:
                # Check sys state change
                if all([led_info.get('type') == 'SYS',
                        led_info.get('before') == 'System bootup finish',
                        led_info.get('after') == 'Ready']):
                    self.sys_power_ready = True
                elif all([led_info.get('type') == 'SYS',
                        led_info.get('before') == 'Ready',
                        led_info.get('after') == 'System bootup finish']):
                    self.sys_power_ready = True
                # Check led state change
                if all([led_info.get('type') == 'LED',
                          led_info.get('before') == 'Slow Breathing',
                          led_info.get('after') == 'Full Solid']):
                    self.led_power_ready = True
        if self.uut.get('model') in ('yodaplus', 'yodaplus2'):
            if not self.sys_power_ready:
                raise self.err.TestFailure('"sys state change" is the same as expected.')
            if not self.led_power_ready:
                raise self.err.TestFailure('"Switching Led state" is not turned into (Full Solid).')
        else:
            if not self.sys_power_ready:
                raise self.err.TestFailure('"sys state change" is not (Power up) -> (Ready)')
            if not self.led_power_ready:
                raise self.err.TestFailure('"Switching Led state" is not (Slow Breathing)->(Full Solid)')
        self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
        self.uut_owner.id = 0  # Reset uut_owner.id
        self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']})
        self.log.info('Try to attach uut_owner to check if "CloudConnected" is True ...')

    def check_device_is_ready(self):
        self.log.info('Checking if device is ready and proxyConnect is True')
        self.timing.reset_start_time()
        while not self.timing.is_timeout(300):
            try:
                if self.ssh_client.get_device_ready_status() and self.ssh_client.get_device_proxy_connect_status():
                    self.log.info('Device is ready and proxyConnect is True.')
                    break
                else:
                    self.log.warning('Device is not ready, wait for 5 secs and try again ...')
                    time.sleep(5)
            except RuntimeError as e:
                self.log.warning(e)
        else:
            raise self.err.TestFailure('Device status is not ready after retry for 300 secs!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""
        *** LED Check: Power Ready on Kamino Android ***
        """)
    test = LEDPowerStateReady(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)