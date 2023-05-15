# -*- coding: utf-8 -*-
""" Godzilla integration test for Platform BAT
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
from datetime import datetime, timedelta
# platform modules
from middleware.arguments import GodzillaIntegrationTestArgument
from middleware.godzilla_integration_test import GodzillaIntegrationTest
# Sub-tests

from godzilla_scripts.bat_scripts.firmware_update import FirmwareUpdate


class FIRMWARE_DOWNGRADE_UPGRADE(GodzillaIntegrationTest):

    TEST_SUITE = 'GODZILLA INTEGRATION TESTS'
    TEST_NAME = 'GODZILLA FIRMWARE DOWNGRADE UPGRADE TESTS'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'FUNCTIONAL'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            self.integration.add_testcases(testcases=[
                (FirmwareUpdate, {'force_update': True, 'local_image': self.local_image,
                                  'fw_version': self.downgrade_version, 'io_before_test': self.io_before_test,
                                  'disable_ota': True, 'keep_fw_img': True, 'overwrite': self.overwrite}),
                (FirmwareUpdate, {'force_update': True, 'local_image': self.local_image,
                                  'fw_version': self.env.firmware_version, 'io_before_test': self.io_before_test,
                                  'disable_ota': True, 'keep_fw_img': True}),
            ])

    def after_loop(self):
        self.log.info("Clean all the firmware images after testing")
        self.ssh_client.execute('rm /shares/Public/*.bin')


if __name__ == '__main__':
    parser = GodzillaIntegrationTestArgument("""\
        *** RESTSDK_BAT on Kamino Android ***
        Examples: ./run.sh godzilla_scripts/integration_tests/platform_bat.py --uut_ip 10.136.137.159\
        """)
    # Test Arguments
    parser.add_argument('--single_run', help='Run single case for RESTSDK BAT')
    parser.add_argument('--downgrade_version', help='Version of the downgrade firmware')
    parser.add_argument('--local_image', help='Download firmware image from local file server', action="store_true", default=False)
    parser.add_argument('-ibf', '--io_before_test', help='Use samba to run IO before testing', action='store_true')
    parser.add_argument('-o', '--overwrite', help='use to force downgrade to OS3 versions', action='store_true')

    test = FIRMWARE_DOWNGRADE_UPGRADE(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
