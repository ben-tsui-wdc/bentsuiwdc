# -*- coding: utf-8 -*-
""" Test cases to check memory size that uboot supported. For Yoda plus only
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class UbootMemoryCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Uboot Memory Support Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-23759'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        model = self.uut.get('model')
        if model == 'monarch' or model == 'pelican':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(model))
        memtotal = self.adb.executeShellCommand('cat /proc/meminfo | grep MemTotal')[0].split()[1]
        memunit = self.adb.executeShellCommand('cat /proc/meminfo | grep MemTotal', consoleOutput=False)[0].split()[2]
        if memunit == 'kB':
            if model == 'yodaplus' and (1024-256)*1024*0.9 < int(memtotal) < 1024*1024*1.1:
                self.log.info('Uboot Memory Support for YodaPlus Check PASSED !!')
            elif model == 'yoda' and int(memtotal) < 512*1024*1.1:
                self.log.info('Uboot Memory Support for Yoda Check PASSED !!')
            else:
                raise self.err.TestFailure('Uboot Memory Support check failed !! ')
        elif memunit == 'MB':
            if model == 'yodaplus' and (1024-256)*0.9 < int(memtotal) < 1024*1.1:
                self.log.info('Uboot Memory Support for YodaPlus Check PASSED !!')
            elif model == 'yoda' and int(memtotal) < 512*1.1:
                self.log.info('Uboot Memory Support for Yoda Check PASSED !!')
            else:
                raise self.err.TestFailure('Uboot Memory Support check failed !! ')
        else:
            raise self.err.TestSkipped('Memory unit is not kB or MB, skip the test !! ')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Uboot Memory Support Check Script ***
        Examples: ./run.sh bat_scripts_new/uboot_memory_check.py --uut_ip 10.92.224.68\
        """)

    test = UbootMemoryCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
