# -*- coding: utf-8 -*-
""" Test cases to check Bluetooth service is launch.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class BluetoothServiceCheck(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-680 - Bluetooth service check'
    TEST_JIRA_ID = 'KDP-680'

    SETTINGS = {
        'uut_owner': False
    }

    def before_test(self):
        model = self.uut.get('model')
        if model == 'monarch2' or model == 'pelican2':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(model))

    def test(self):
        exitcode, _ = self.ssh_client.execute('pidof bluetoothd')
        if exitcode != 0:
            raise self.err.TestFailure("Bluetooth process not found")


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Bluetooth Service Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/bluetooth_service_check.py --uut_ip 10.92.224.68\
        """)

    test = BluetoothServiceCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
