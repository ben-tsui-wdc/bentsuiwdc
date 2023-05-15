# -*- coding: utf-8 -*-
""" Test for API: PUT /v1/device (KAM-16644).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.reboot import Reboot


class RebootDeviceTest(GodzillaTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Reboot Device'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1745'
    PRIORITY = 'Blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def test(self):
        reboot = Reboot(self)
        reboot.init()
        reboot.test()
        reboot.after_test()

if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Reboot_Device test on Godzilla platform ***
        Examples: ./run.sh restsdk_tests/functional_tests/reboot_device.py --uut_ip 10.136.137.159\
        """)
    test = RebootDeviceTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
