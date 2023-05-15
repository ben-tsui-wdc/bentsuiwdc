# -*- coding: utf-8 -*-
""" Wifi Functional Test: KAM-24659.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from platform_libraries.pyutils import retry
# test case
from ap_connect import APConnect


class AutoConnectAfterWANRecovered(APConnect):

    TEST_SUITE = 'WIFI Functional Tests'
    TEST_NAME = 'Auto Connect After WAN Recovered Test'

    def before_test(self):
        super(AutoConnectAfterWANRecovered, self).before_test()
        self._disable_wan = False # Flag to record wan status.

    def test(self):
        self.reset_logcat_start_line()
        self.log.test_step('Disable AP WAN')
        self.log.debug('WAN is shared on br0')
        self._disable_wan = True
        self.ap.disable_network_interface('br0')

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

        self.log.test_step('Enable AP WAN')
        self.log.debug('WAN is shared on br0')
        self.ap.enable_network_interface('br0')
        self._disable_wan = False

        self.log.test_step('Test device connect to Wi-Fi')
        self.adb.disconnect()
        self.serial_client.restart_adbd()
        self.adb.connect(timeout=60*5)

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
        if self._disable_wan:
            self.ap.enable_network_interface('br0')
            self._disable_wan = False


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** AutoConnectAfterWANRecovered test on Kamino Android ***
        Examples: ./run.sh functional_tests/auto_connect_after_wan_recovered.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-rwob', '--run_with_on_boarding', help='Test device has already on setting up AP with BLTE', action='store_true', default=False)

    test = AutoConnectAfterWANRecovered(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
