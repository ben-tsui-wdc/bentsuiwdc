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


class CHECK_BRIDGE_FIRMWARE(GodzillaIntegrationTest):

    TEST_SUITE = 'GODZILLA INTEGRATION TESTS'
    TEST_NAME = 'GODZILLA CHECK BRIDGE FIRMWARE TEST'
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
        self.integration.add_testcases(testcases=[
            (FirmwareUpdate, {'force_update': True, 'local_image': self.local_image, 'overwrite': False,
                              'fw_version': self.godzilla_firmware, 'io_before_test': self.io_before_test,
                              'disable_ota': True, 'keep_fw_img': True}),
            # Backdoor to downgrade GZA to Bridge FW
            (FirmwareUpdate, {'force_update': False, 'local_image': self.local_image, 'overwrite': True,
                              'fw_version': self.bridge_firmware, 'io_before_test': self.io_before_test,
                              'disable_ota': True, 'keep_fw_img': True})
        ])

        if self.last_bridge_firmware:
            self.integration.add_testcases(testcases=[
                # New bridge firmware downgrade to previous bridge firmware
                (FirmwareUpdate, {'force_update': False, 'local_image': self.local_image, 'overwrite': False,
                                  'fw_version': self.last_bridge_firmware, 'io_before_test': self.io_before_test,
                                  'disable_ota': True, 'keep_fw_img': True}),
                # Previous bridge firmware upgrade to new bridge firmware
                (FirmwareUpdate, {'force_update': False, 'local_image': self.local_image, 'overwrite': False,
                                  'fw_version': self.bridge_firmware, 'io_before_test': self.io_before_test,
                                  'disable_ota': True, 'keep_fw_img': True, 'data_integrity': self.data_integrity,
                                  'check_protocol': self.check_protocol, 'TEST_JIRA_ID': 'GZA-9457',
                                  'TEST_NAME': 'Manually update old Bridge FW to new Bridge FW'})
                ])

        self.integration.add_testcases(testcases=[
            (FirmwareUpdate, {'force_update': False, 'local_image': self.local_image, 'overwrite': False,
                              'fw_version': self.godzilla_firmware, 'io_before_test': self.io_before_test,
                              'disable_ota': True, 'keep_fw_img': True, 'data_integrity': self.data_integrity,
                              'check_protocol': self.check_protocol, 'TEST_JIRA_ID': 'GZA-3297',
                              'TEST_NAME': 'Bridge FW upgrade to GZA FW manually'}),
            # Negative test, GZA -> Bridge should failed
            (FirmwareUpdate, {'force_update': False, 'local_image': self.local_image, 'overwrite': False,
                              'fw_version': self.bridge_firmware, 'io_before_test': self.io_before_test,
                              'disable_ota': True, 'keep_fw_img': True, 'data_integrity': self.data_integrity,
                              'check_protocol': self.check_protocol, 'negative': True, 'TEST_JIRA_ID': 'GZA-3300',
                              'TEST_NAME': 'Negative: GZA FW downgrade to Bridge FW should failed'})
        ])

        """ 
            OS5 -> Bridge -> Removed this part (OS3 -> Bridge, including negative tests) -> OS5
            
            # Use Overwrite = True as a backdoor to downgrade firmware to OS3 versions at the beginning
            # Bridge -> OS3
            (FirmwareUpdate, {'force_update': False, 'local_image': self.local_image, 'overwrite': False,
                              'fw_version': self.os3_firmware, 'io_before_test': self.io_before_test,
                              'disable_ota': True, 'keep_fw_img': True, 'data_integrity': self.data_integrity,
                              'check_protocol': self.check_protocol, 'TEST_JIRA_ID': 'GZA-3296',
                              'TEST_NAME': 'Bridge FW downgrade to OS3 FW manually'}),
            # Negative test, OS3 -> GZA should failed
            (FirmwareUpdate, {'force_update': False, 'local_image': self.local_image, 'overwrite': False,
                              'fw_version': self.godzilla_firmware, 'io_before_test': self.io_before_test,
                              'disable_ota': True, 'keep_fw_img': True, 'data_integrity': self.data_integrity,
                              'check_protocol': self.check_protocol, 'negative': True, 'TEST_JIRA_ID': 'GZA-3299',
                              'TEST_NAME': 'Negative: OS3 FW upgrade to GZA FW should failed'}),
            (FirmwareUpdate, {'force_update': True, 'local_image': self.local_image, 'overwrite': False,
                              'fw_version': self.bridge_firmware, 'io_before_test': self.io_before_test,
                              'disable_ota': True, 'keep_fw_img': True, 'data_integrity': self.data_integrity,
                              'check_protocol': self.check_protocol, 'TEST_JIRA_ID': 'GZA-2869',
                              'TEST_NAME': 'OS3 FW upgrade to Bridge FW manually'})
            ===
            # Negative test, GZA -> OS3 should failed
            (FirmwareUpdate, {'force_update': False, 'local_image': self.local_image, 'overwrite': False,
                              'fw_version': self.os3_firmware, 'io_before_test': self.io_before_test,
                              'disable_ota': True, 'keep_fw_img': True, 'data_integrity': self.data_integrity,
                              'check_protocol': self.check_protocol, 'negative': True, 'TEST_JIRA_ID': 'GZA-3301',
                              'TEST_NAME': 'Negative: GZA FW downgrade to OS3 FW should failed'})             
        """
    def after_loop(self):
        self.log.info("Clean all the firmware images after testing")
        self.ssh_client.execute('rm /shares/Public/*.bin')


if __name__ == '__main__':
    parser = GodzillaIntegrationTestArgument("""\
        *** RESTSDK_BAT on Kamino Android ***
        Examples: ./run.sh godzilla_scripts/integration_tests/check_bridge_firmware.py --uut_ip 10.136.137.159:8001\
        """)
    # Test Arguments
    parser.add_argument('-ibf', '--io_before_test', help='Use samba to run IO before testing', action='store_true')
    parser.add_argument('-ofw', '--os3_firmware', help='OS3 Firmware Version', default='2.31.204')
    parser.add_argument('-bfw', '--bridge_firmware', help='Bridge Firmware Version', default='2.42.107')
    parser.add_argument('-lbfw', '--last_bridge_firmware', help='Last Bridge Firmware Version', default=None)
    parser.add_argument('-gfw', '--godzilla_firmware', help='Godzilla Firmware Version', default='5.16.105')
    parser.add_argument('-di', '--data_integrity', help='check data integrity before firmware update',
                        action='store_true')
    parser.add_argument('-cp', '--check_protocol',
                        help='check I/O works with different protocols after firmware update', action='store_true')
    parser.add_argument('--local_image', help='Download firmware image from local file server', action="store_true")

    test = CHECK_BRIDGE_FIRMWARE(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
