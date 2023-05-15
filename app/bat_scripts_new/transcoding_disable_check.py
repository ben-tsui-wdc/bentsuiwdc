# -*- coding: utf-8 -*-
""" Test cases to check transcoding function is disabled on device.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class TranscodingDisableCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Transcoding Disabled Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-24453'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        model = self.adb.getModel()
        if model == 'monarch' or model == 'pelican':
            self.log.info('device.feature.hwtranscoding only display on yoda series, model is {}'.format(model))
        else:
            hwtranscoding = self.adb.executeShellCommand('getprop device.feature.hwtranscoding')[0].strip()
            if model == 'yoda':
                if hwtranscoding != 'false':
                    raise self.err.TestFailure('Transcoding Disabled Flag Check Failed, value is {} !!'.format(hwtranscoding))
            elif model == 'yodaplus':
                if hwtranscoding != 'true':
                    raise self.err.TestFailure('Transcoding Disabled Flag Check Failed, value is {} !!'.format(hwtranscoding))

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Transcoding Disable Check Script ***
        Examples: ./run.sh bat_scripts_new/transcoding_disable_check.py --uut_ip 10.92.224.68\
        """)

    test = TranscodingDisableCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
