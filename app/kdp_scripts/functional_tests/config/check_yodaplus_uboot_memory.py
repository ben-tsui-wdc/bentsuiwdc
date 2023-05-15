# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckYodaplusUbootMemory(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-403 - Check_Yodaplus_Uboot_Memory'

    SETTINGS = {
        'uut_owner': False
    }
    # Popcorn
    TEST_JIRA_ID = 'KDP-403'

    def test(self):
        if 'yodaplus' not in self.uut.get('model'):
            raise self.err.TestSkipped('Model is {}, skipped the test!'.format(self.uut.get('model')))

        out, err = self.ssh_client.execute_cmd('cat /proc/meminfo | grep MemTotal')
        if '751632 kB' not in out:
            raise self.err.TestFailure("The uboot memory total should be 751632 kB but it's {}!".format(out))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** check Yodaplus uboot memory ***
        Examples: ./run.sh kdp_scripts/functional_tests/config/check_yodaplus_uboot_memory.py --uut_ip 10.92.224.61 
        --cloud_env qa1 --dry_run --debug_middleware --disable_clean_logcat_log """)

    test = CheckYodaplusUbootMemory(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
