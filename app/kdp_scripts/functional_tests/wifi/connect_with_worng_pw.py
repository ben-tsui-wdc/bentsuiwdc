# -*- coding: utf-8 -*-
""" Test cases to connect Wi-Fi AP with incorrect password [KDP-303]
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"


# std modules
import sys

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class ConnectWithIncorrectPW(KDPTestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'KDP-303: Connect Wi-Fi AP with incorrect password'
    # Popcorn
    TEST_JIRA_ID = 'KDP-303'
    REPORT_NAME = 'Functional'

    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True,
        'serial_client': True
    }
    
    def declare(self):
        self.timeout = 300

    def init(self):
        self.reset_network = False

    def test(self):
        self.log.info("Recording current IP for comparing")
        old_ip = self.serial_client.get_ip()
        self.log.info("Connecting 5G Wi-Fi with incorrect password")
        self.serial_client.configure_ssid_kdp(ssid=self.wifi_ssid_5g, password='WrongPassword')
        self.log.info("Waiting for INACTIVE status")
        output = self.serial_client.wait_for_wpa_state(status='INACTIVE', timeout=60, raise_error=False)
        assert output, 'wpa_state is not as expected'
        self.log.info("Waiting for reconnecting with old WiFi setting")
        self.serial_client.wait_for_ip_kdp(timeout=60*5)
        current_ip = self.serial_client.get_ip()
        # Expect it reconnect to original AP and have a IP is in the same subnet.
        if (current_ip.startswith('192.168.43.1') or old_ip.rsplit('.', 2)[0] not in current_ip):
            self.reset_network = True
            raise self.err.TestFailure('Current IP: {} which is not as expected'.format(self.current_ip))

    def after_test(self):
        if self.reset_network:
            self.serial_client.retry_for_connect_WiFi_kdp(ssid=self.wifi_ssid_5g, password=self.wifi_password_5g)
        self.env.check_ip_change_by_console()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Connect Wi-Fi AP with incorrect password ***
        """)
    parser.add_argument('--wifi_ssid_5g', help="", default='R7000_50')
    parser.add_argument('--wifi_password_5g', help="", default='fituser99')

    test = ConnectWithIncorrectPW(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
