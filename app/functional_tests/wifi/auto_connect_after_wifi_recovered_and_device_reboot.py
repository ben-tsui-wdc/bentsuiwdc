# -*- coding: utf-8 -*-
""" Wifi Functional Test: KAM-25774, KAM-25775.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from platform_libraries.pyutils import retry
# test case
from ap_connect import APConnect
from restsdk_tests.functional_tests.reboot_device import RebootDeviceTest


class AutoConnectAfterWiFiRecoveredAndDeviceReboot(APConnect, RebootDeviceTest):

    TEST_SUITE = 'WIFI Functional Tests'
    TEST_NAME = 'Auto Connect After Wi-Fi Recovered and Device Reboot Test'

    SETTINGS = {
        'uut_owner': True
    }

    def test(self):
        self.reset_logcat_start_line()
        self.log.test_step('Power off AP')
        self.poweroff_ap()

        self.log.test_step('Test device disconnect from Wi-Fi')
        self.log.debug('Here we use devcice shutdown check as Wi-Fi disconnect check...')
        if not self.adb.wait_for_device_to_shutdown():
            raise self.TestFailure('AP Wi-Fi disable failed')

        if self.check_wifi_status: # Logcat logs may missing.
            self.log.test_step('Check system log: "Wifi Disconnected"')
            retry( # Retry 30 mins.
                func=self.check_serial_wifi, wifi_status='Wifi Disconnected',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )

        # NEED BTLE ONBOADING
        if self.run_with_on_boarding:
            self.log.test_step('Check system log: LED is "Fast Breathing"')
            retry( # Retry 30 mins.
                func=self.check_serial_led, light_pattern='Fast Breathing',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )

        self.log.test_step('Reboot test device')
        self.serial_client.serial_write('reboot')

        self.log.test_step('Power on AP')
        self.poweron_ap()

        self.log.test_step('Test device boot completed')
        self.wait_device = True
        RebootDeviceTest.after_test(self)

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


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** AutoConnectAfterWiFiRecoveredAndDeviceReboot test on Kamino Android ***
        Examples: ./run.sh functional_tests/auto_connect_after_wifi_recovered_and_device_reboot.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-app', '--ap_power_port', help='AP port on power switch', metavar='PORT', type=int)

    test = AutoConnectAfterWiFiRecoveredAndDeviceReboot(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
