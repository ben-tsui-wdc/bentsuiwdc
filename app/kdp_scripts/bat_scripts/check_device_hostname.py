# -*- coding: utf-8 -*-
""" KDP device host name: MyCloud-xxxxxx(serial number last 6 digits) check
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckDeviceHostname(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-5120 - Device hostname check'
    TEST_JIRA_ID = 'KDP-5120'

    SETTINGS = {
        'uut_owner': False
    }

    def before_test(self):
        check_is_kdp_device = self.ssh_client.check_is_kdp_device()
        if not check_is_kdp_device:
            self.err.TestSkipped('Device is not ibi2/MCH2, skipped the test!')

    def test(self):
        serial_number = self.ssh_client.get_device_serial_number()
        hostname = self.ssh_client.get_device_hostname()
        if serial_number[6:] != hostname.split("-")[1]:
            self.err.TestFailure('Device hostname last 6 digits is not match serial number, test Failed !!!')
        

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Check Device Hostname Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/check_device_hostname.py --uut_ip 10.92.224.68\
        """)

    test = CheckDeviceHostname(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
