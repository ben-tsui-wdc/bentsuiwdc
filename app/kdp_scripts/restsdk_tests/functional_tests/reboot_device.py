# -*- coding: utf-8 -*-
""" Test for API: PUT /v1/device (KAM-16644).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class RebootDeviceTest(KDPTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Reboot Device'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-907'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }

    def test(self):
        self.uut_owner.reboot_device()
        self.verify_result()

    def verify_result(self):
        timeout = 60*5
        self.log.info('Expect device do reboot in {}s.'.format(timeout))
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=timeout):
            self.log.error('Reboot device: FAILED.')
            raise self.err.TestFailure('Reboot device failed')
        self.log.info('Reboot device: PASSED.')

    def after_test(self):
        timeout = 60*5
        try:
            if self.wait_device:
                self.log.info('Wait for device boot completede...')
                if not self.ssh_client.wait_for_device_boot_completed(timeout=timeout):
                    self.log.error('Device seems down.')
        except:
            self.log.exception('Exception occurred during waiting.')
    

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Reboot_Device test on Kamino Android ***
        Examples: ./run.sh kdp_scripts/restsdk_tests/functional_tests/reboot_device.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-wait', '--wait_device', help='Wait for device boot completede', action='store_true')

    test = RebootDeviceTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
