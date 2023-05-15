# -*- coding: utf-8 -*-
""" Wifi Functional Test: KAM-25274, KAM-25275.
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


class AutoConnectAfterDeviceReboot(APConnect, RebootDeviceTest):

    TEST_SUITE = 'WIFI Functional Tests'
    TEST_NAME = 'Auto Connect After Device Reboot Test'

    SETTINGS = {
        'uut_owner': True
    }

    def test(self):
        self.log.test_step('Reboot test device')
        RebootDeviceTest.test(self)

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
        *** AutoConnectAfterDeviceReboot test on Kamino Android ***
        Examples: ./run.sh functional_tests/auto_connect_after_device_reboot.py --uut_ip 10.136.137.159\
        """)

    test = AutoConnectAfterDeviceReboot(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
