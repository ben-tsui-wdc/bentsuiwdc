# -*- coding: utf-8 -*-

__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"
__compatible__ = 'KDP'

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class WiFiChannelPlan(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-290 - WiFi channel plan test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-290'
    SETTINGS = {
        'uut_owner': False # Disbale restAPI.
    }

    def test(self):
        code, output = self.ssh_client.execute('cat /proc/net/rtl88x2be/wlan0/chan_plan')
        assert 'chplan:0x67' in output, 'chan_plan is not as expected: {}'.format(output)

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** WiFi channel plan test ***
        """)
    test = WiFiChannelPlan(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)