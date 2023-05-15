# -*- coding: utf-8 -*-
""" Test cases to check transcoding function is disabled on device.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class TranscodingFlagCheck(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-402 - Transcoding Flag Check'
    TEST_JIRA_ID = 'KDP-402'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        if not self.ssh_client.get_device_info(fields='hwTranscoding').get('features').get('hwTranscoding'):
            raise self.err.TestFailure('Transcoding Flag is False, test failed!!!')

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Transcoding Flag Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/transcoding_flag_check.py --uut_ip 10.92.224.68\
        """)

    test = TranscodingFlagCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
