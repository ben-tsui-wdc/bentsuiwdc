# -*- coding: utf-8 -*-
""" Wifi Functional Test: KAM-25231, KAM-25239, KAM-25240.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
import time
from uuid import uuid4
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.pyutils import retry


class APConnect(TestCase):

    TEST_SUITE = 'WIFI Functional Tests'
    TEST_NAME = 'AP Connect Test'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        # Original connected AP settings.
        self.original_ssid = None
        self.original_password = None
        self.original_security_mode = 'psk2'
        self.original_wifi_type = '5G'
        # AP settings for this test.
        self.test_ssid = 'functional'
        self.test_password = 'Automation'
        self.test_security_mode = 'psk2'
        self.test_wifi_type = '5G'
        # Test Step controls.
        self.ap_power_port = None
        self.check_wifi_status = False
        self.run_with_on_boarding = False
        self.recover_wifi_changes = False
        self.recover_ap = True
        self.ssid_before_run = None # Check device now should connect to this SSID.
        # For read logcat.
        self._logcat_start_line = None # Logcat checkers read data after this line.
        # Flag to record ap status.
        self._poweroff_ap = False

    def init(self):
        # These setting is not supplied when it's as sub-case runs, we take values from parent integration test.
        if not self.original_ssid:
            self.original_ssid = self.env.ap_ssid
        if not self.original_password:
            self.original_password = self.env.ap_password
        # For read logcat.
        self.reset_logcat_start_line()

    def before_test(self):
        self._poweroff_ap = False
        self.check_device_network(check_ssid=self.ssid_before_run)
        self.serial_client.debug_system_timestamps()
        return # Disable Workaround.
        # Workaround for KAM200-1463.
        self.log.warning('Work-around fixes...')
        self.serial_client.re_enable_wifi()
        if self.__class__.__name__ == 'APConnect':   
            self.connect_ap(
                ssid=self.env.ap_ssid, password=self.env.ap_password, security_mode='psk'
            )
        else:
            self.log.warning('Reset Wi-Fi setting...')
            APConnect.test(self)
        #self.serial_client.re_enable_wifi()
        #self.clean_logcat()
        self.log.warning('Done, and start to run test.')

    def test(self):
        self.reset_logcat_start_line()
        self.log.test_step('Configure AP (SSID:{}, Password:{}, Security Mode:{}({}))'.format(
            self.test_ssid, self.test_password, self.test_security_mode, self.ap.security_key_mapping(self.test_security_mode))
        )
        self.set_ap(
            ssid=self.test_ssid, password=self.test_password, security_mode=self.test_security_mode, wifi_type=self.test_wifi_type
        )

        self.log.test_step('Test device connect AP & Reconnect ADB')
        self.connect_ap(
            ssid=self.test_ssid, password=self.test_password, security_mode=self.test_security_mode
        )

        if self.check_wifi_status: # Logcat logs may missing.
            self.log.test_step('Check system log: "Wifi Connected"')
            retry( # Retry 30 mins.
                func=self.check_wifi, wifi_status='Wifi Connected',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )

        # NEED BTLE ONBOADING
        if self.run_with_on_boarding:
            self.log.test_step('Check system log: LED is "Full Solid"')
            retry( # Retry 30 mins.
                func=self.check_serial_led, light_pattern='Full Solid',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )

    def after_test(self):
        if self._poweroff_ap:
            self.power_switch.power_on(self.ap_power_port)
            self._poweroff_ap = False

        if not self.recover_wifi_changes:
            return

        self.reset_logcat_start_line()
        if self.recover_ap:
            self.log.test_step('Recover AP (SSID:{}, Password:{}, Security Mode:{}({}))'.format(
                self.original_ssid, self.original_password, self.original_security_mode, self.ap.security_key_mapping(self.original_security_mode))
            )
            self.set_ap(
                ssid=self.original_ssid, password=self.original_password, security_mode=self.original_security_mode, wifi_type=self.original_wifi_type
            )

        self.log.test_step('Recover test device connect AP & Reconnect ADB')
        self.connect_ap(
            ssid=self.original_ssid, password=self.original_password, security_mode=self.original_security_mode
        )

        if self.check_wifi_status: # Logcat logs may missing.
            self.log.test_step('Check system log: "Wifi Connected"')
            retry( # Retry 30 mins.
                func=self.check_wifi, wifi_status='Wifi Connected',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )

        # NEED BTLE ONBOADING
        if self.run_with_on_boarding:
            self.log.test_step('Check system log: LED is "Full Solid"')
            retry( # Retry 30 mins.
                func=self.check_serial_led, light_pattern='Full Solid',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )

    def check_device_network(self, check_ssid=None, retry_to_fix_ssid=True, raise_if_no_ip=True):
        self.log.info('Check device network...')
        if check_ssid:
            self.log.info('Currect SSID should be "{}"'.format(check_ssid))
            if not self.serial_client.list_network(filter_keyword=check_ssid):
                self.log.warning('SSID is not currect')
                if retry_to_fix_ssid:
                    self.log.info('Retry to fix SSID...')
                    wifi_settings = { # Recovry it.
                        self.original_password: (self.original_password, self.original_password, self.original_security_mode),
                        self.test_ssid: (self.test_ssid, self.test_password, self.test_security_mode)
                    }.get(check_ssid)
                    if not wifi_settings:
                        raise self.err.TestError('SSID is not currect') # NOTEXCUTED
                    self.connect_ap(*wifi_settings) # Reconnect AP.
                else:
                    raise self.err.TestError('SSID is not currect') # NOTEXCUTED
        else: # Just print out
            self.serial_client.list_network()
        ip = self.serial_client.get_ip()
        self.log.info('Device IP: {}'.format(ip))
        if not ip and raise_if_no_ip:
            raise self.err.TestError('No device IP') # NOTEXCUTED

    def set_ap(self, ssid, password, security_mode, wifi_type='5G', cleanup_device=False):
        # Choose Wi-Fi type.
        ap_setter = {
            '2.4G': self.ap.set_2_4G,
            '5G': self.ap.set_5G
        }[wifi_type]
        # Clear all WiFi setrtings.
        if cleanup_device: self.serial_client.remove_all_network(restart_wifi=False)
        # Recover AP settings.
        ap_setter(ssid, password, security_mode, apply_it=True)

    def connect_ap(self, ssid, password, security_mode, update_ip=True, via_btle=True):
        # Connect to AP.
        if via_btle:
            self.env.connect_with_btle(ssid, password, testcase=self, retry_times=60, reboot_ap=self.reboot_ap)
        else:
            self.serial_client.remove_all_network(restart_wifi=False)
            self.serial_client.connect_WiFi(ssid, password, security_mode=self.ap.security_key_mapping(security_mode),
                timeout=60*30, reboot_after=60*10, restart_wifi=False, raise_error=True)
        if update_ip: self.update_device_ip()

    def update_device_ip(self, restart_adbd=True):
        if not self.serial_client.wait_for_ip(timeout=60):
            self.log.error('No device IP!')
        # Update IP.
        self.env.check_ip_change_by_console()
        if self.adb:
            # Reconnect ADB.
            self.log.info('Reconnect ADB...')
            self.adb.disconnect()
            if restart_adbd:
                self.log.info('Re-start adbd to make sure ADB is good...')
                self.serial_client.restart_adbd()
            self.adb.connect(timeout=60*5)

    def reboot_ap(self):
        if not self.ap_power_port:
            return
        self.poweroff_ap()
        self.poweron_ap()

    def poweroff_ap(self):
        self.log.info('Power off AP...')
        self.power_switch.power_off(self.ap_power_port)
        self._poweroff_ap = True
        self.ap.wait_for_ap_shutdown(delay=5, max_retry=60)
        self.ap.close()

    def poweron_ap(self):
        self.log.info('Power on AP...')
        self.power_switch.power_on(self.ap_power_port)
        self._poweroff_ap = False
        self.ap.wait_for_ap_boot_up(delay=5, max_retry=60)
        self.ap.connect()

    #
    # Logcat Readers
    #
    def set_logcat_start_line(self):
        message = 'AutomationTest-' + uuid4().hex
        self.log.info('Set logcat start line: {}'.format(message))
        self.serial_client.write_logcat(message, priority='V', tag='LedServer', buffer='system')
        return message

    def reset_logcat_start_line(self):
        self._logcat_start_line = self.set_logcat_start_line()

    def read_after_start_line(self, logs):
        is_found = False
        filter_led_logs = []
        if not self._logcat_start_line:
            return logs
        # Filter lines.
        for line in logs:
            if self._logcat_start_line in line:
                is_found = True
            if is_found:
                filter_led_logs.append(line)
        if filter_led_logs:
            return filter_led_logs
        return logs

    def get_led_logs(self, print_logs=True):
        led_logs = self.adb.get_led_logs(log_filter=self.read_after_start_line)
        if print_logs: self.adb.print_led_info(led_logs)
        return led_logs

    def check_led(self, light_pattern, led_logs=None):
        if not led_logs:
            led_logs = self.get_led_logs()

        for i, led_info in enumerate(led_logs):
            if all([led_info.get('type') == 'LED', led_info.get('after') == light_pattern]):
                return True
        return False

    def check_wifi(self, wifi_status, led_logs=None):
        if not led_logs:
            led_logs = self.get_led_logs()

        for i, led_info in enumerate(led_logs):
            if all([led_info.get('type') == 'SYS', led_info.get('after') == wifi_status]):
                return True
        return False

    def get_serial_led_logs(self, print_logs=True):
        led_logs = self.serial_client.get_led_logs(log_filter=self.read_after_start_line)
        led_logs = self.read_after_start_line(logs=led_logs)
        if print_logs: self.adb.print_led_info(led_logs)
        return led_logs

    def check_serial_led(self, light_pattern, use_logcat_logs=False, led_logs=None):
        if not use_logcat_logs: # Use sampling hardware value.
            led_state = self.serial_client.get_led_state()
            self.log.info('Led State: {}'.format(led_state))
            if led_state != light_pattern:
                return False
            return True
        else: 
            if not led_logs:
                led_logs = self.get_serial_led_logs()

            for i, led_info in enumerate(led_logs):
                if all([led_info.get('type') == 'LED', led_info.get('after') == light_pattern]):
                    return True
            return False

    def check_serial_wifi(self, wifi_status, led_logs=None):
        if not led_logs:
            led_logs = self.get_serial_led_logs()

        for i, led_info in enumerate(led_logs):
            if all([led_info.get('type') == 'SYS', led_info.get('after') == wifi_status]):
                return True
        return False

    #
    # Other features
    #
    def clean_logcat(self, export_logcat_name=None):
        original_name = self.env.logcat_name

        if not export_logcat_name:
            # Export logcat and save a new name with a local count.
            if not hasattr(self, '_export_num'):
                self._export_num = 1
            # TEST_NAME.logcat-1
            export_logcat_name = '{}-{}'.format(original_name, self._export_num)
            self._export_num += 1
        
        self.env.logcat_name = export_logcat_name
        self.data.export_logcat_log(clean_logcat=True)
        self.env.logcat_name = original_name

    def set_ap_network_mode(self, mode, wifi_type='5G'):
        # Choose Wi-Fi type.
        ap_setter = {
            '2.4G': self.ap.set_2_4G_network_mode,
            '5G': self.ap.set_5G_network_mode
        }[wifi_type]
        # Recover AP settings.
        ap_setter(mode, apply_it=True)


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** APConnect test on Kamino Android ***
        Examples: ./run.sh functional_tests/ap_connect.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-app', '--ap_power_port', help='AP port on power switch', metavar='PORT', type=int)
    parser.add_argument('-original_wifi_type', '--original_wifi_type', help='Original Wi-Fi type', default='5G', choices=['2.4G', '5G'])
    parser.add_argument('-test_ssid', '--test_ssid', help='AP SSID for test', metavar='SSID')
    parser.add_argument('-test_password', '--test_password', help='AP password for test', metavar='PWD')
    parser.add_argument('-test_security_mode', '--test_security_mode', help='Security mode for test', metavar='MODE', default='psk2')
    parser.add_argument('-test_wifi_type', '--test_wifi_type', help='Wi-Fi type for test', default='5G', choices=['2.4G', '5G'])
    parser.add_argument('-cws', '--check_wifi_status', help='Test device with verify wifi status', action='store_true', default=False)
    parser.add_argument('-rwob', '--run_with_on_boarding', help='Test device has already on setting up AP with BLTE', action='store_true', default=False)

    test = APConnect(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
