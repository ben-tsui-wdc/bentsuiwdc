# -*- coding: utf-8 -*-
""" Test cases to check BLE(bluetooth Low Energy) service is launch.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from bat_scripts_new.reboot import Reboot


class BLEServiceCheck(Reboot):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'BLE service check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-24576'

    def test(self):
        model = self.uut.get('model')
        if model == 'monarch' or model == 'pelican':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(model))
        try:
            super(BLEServiceCheck, self).test()
        except Exception as ex:
            raise self.err.TestSkipped('Reboot failed ! Skipped the BLE check test ! Error message: {}'.format(repr(ex)))
        ble_service = self.adb.executeShellCommand('logcat -d | grep startAdvertising && logcat -d | grep LeAdvStarted')[0]
        check_list1 = ['startAdvertising', 'success']
        if not all(word in ble_service for word in check_list1):
            raise self.err.TestFailure('BLE Service Check Failed, bluetooth service is not is not launch in yoda device !!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** BLE Service Check Script ***
        Examples: ./run.sh bat_scripts_new/ble_service_check.py --uut_ip 10.92.224.68\
        """)

    test = BLEServiceCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
