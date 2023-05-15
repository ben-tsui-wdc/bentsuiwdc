# -*- coding: utf-8 -*-

__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"
__compatible__ = 'KDP'

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class JavaExceptionCheck(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-914 - No Java exception on boot message'
    # Popcorn
    TEST_JIRA_ID = 'KDP-914'

    def declare(self):
        self.boot_complete_msg = 'System Ready'

    def test(self):
        self.serial_client.reboot_device_kdp()
        output = self.serial_client.serial_wait_for_string_and_return_string(
            string=self.boot_complete_msg, timeout=6*50)
        self.log.info('Boot up completed, checking message so far')
        assert 'java.lang.RuntimeException' not in output, 'Found Java Exception'
        self.log.info('Wait for another 30 secs to see any message on console')
        output = self.serial_client.serial_read_all(time_for_read=30)
        self.log.info('Checking message so far')
        assert 'java.lang.RuntimeException' not in output, 'Found Java Exception'
        self.log.info('Checking boot up status and update IP')
        self.serial_client.wait_for_docker_up()
        self.env.check_ip_change_by_console()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** No Java exception on boot message test ***
        """)

    test = JavaExceptionCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)