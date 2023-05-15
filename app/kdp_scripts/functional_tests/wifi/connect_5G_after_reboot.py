# -*- coding: utf-8 -*-
""" Test cases to connect 5G after reboot [KDP-285]
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"


# std modules
import sys

# platform modules
from middleware.arguments import KDPInputArgumentParser
# test case
from connect_2G_after_reboot import Connect2GAfterReboot


class Connect5GAfterReboot(Connect2GAfterReboot):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'KDP-285: Connect 5G after reboot'
    # Popcorn
    TEST_JIRA_ID = 'KDP-285'
    REPORT_NAME = 'Functional'

    def test(self):
        self.log.info("Connect 5G Wi-Fi")
        self.serial_client.retry_for_connect_WiFi_kdp(ssid=self.wifi_ssid_5g, password=self.wifi_password_5g)
        self.env.check_ip_change_by_console()

        self.log.info('Create a dummy file and upload to test device')
        self._verify_upload_files()

        self.log.info('Reboot test device')
        self.serial_client.serial_write("busybox nohup do_reboot")
        self.serial_client.serial_wait_for_string('The system is going down NOW!',
                                                  timeout=self.timeout, raise_error=True)
        self.serial_client.wait_for_boot_complete_kdp(timeout=self.timeout)

        if not self.serial_client.verify_ssid_is_match(self.wifi_ssid_5g):
            raise self.err.TestFailure('Connect to {} AP failed after device reboot!'.format(self.wifi_ssid_5g))

        self.log.info('Try to upload a file after device boot up')
        self._verify_upload_files()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** change wifi and verify ***
        Examples: ./run.sh functional_tests/connect_5G_after_reboot.py --uut_ip 10.92.224.68 \
        """)
    parser.add_argument('--wifi_ssid_5g', help="", default='R7000_24')
    parser.add_argument('--wifi_password_5g', help="", default='fituser99')
    test = Connect5GAfterReboot(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
