# -*- coding: utf-8 -*-
""" System Management Test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import time
import numbers
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.assert_utls import assert_dict, assert_dict_with_value_type
from platform_libraries.constants import RnD


class NasAdminSystemTest(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-5517 - nasAdmin - System Management Test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5517'
    ISSUE_JIRA_ID = None

    def test(self):
        system_process = self.nasadmin.get_system_process()
        pids = []
        for p in system_process:
            assert_dict_with_value_type(p, {
                'name': unicode,
                'pid': numbers.Integral,
                'cpuUsagePct': numbers.Number,
                'memoryUsageKB': numbers.Integral
            })
            assert p['pid'] not in pids, 'pid: {} is already exist'.format(p['pid'])
            pids.append(p['pid'])

        system_status = self.nasadmin.get_system_status()
        assert_dict_with_value_type(system_status, {
            'cpuUsagePct': numbers.Integral,
            'memoryUsagePct': numbers.Integral,
            'fanspeedRPM': numbers.Integral,
            'drives': list
        })
        slot_count = RnD.DriveSlots.get(self.uut['model'])
        assert len(system_status['drives']) == int(slot_count), 'drive slots is not {}'.format(slot_count)
        for drive in system_status['drives']:
            assert_dict_with_value_type(drive, {
                'slot': numbers.Integral,
                'tempCelsius': numbers.Integral
            })

        self.nasadmin.init_system_test()

        count = 0
        while True:
            if count > 60*5:
                raise AssertionError('System test take over 5 mins')
            system_test = self.nasadmin.get_system_test()
            if 'completed' not in system_test:
                raise AssertionError('Unexpected response')
            if not system_test['completed']:
                count = +1
                time.sleep(1)
                continue
            else:
                assert_dict(system_test, {
                    'clock': 'Pass',
                    'systemp': 'Pass',
                    'fan': 'Pass' if self.uut['model'] == 'drax' else 'NotSupported',
                    'completed': True
                })
                usb_slots = RnD.UsbSlots.get(self.uut['model'])
                assert len(system_test['usb']) == int(usb_slots), 'USB slots is not {}'.format(usb_slots)
                for ul in system_test['usb']:
                    assert ul == 'Pass', 'USB test is not passed'
                break


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** nasAdmin - System Management Test ***
        """)

    test = NasAdminSystemTest(parser)
    resp = test.main()
    print 'test result: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
