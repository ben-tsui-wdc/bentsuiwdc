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

from godzilla_scripts.bat_scripts.ota_proxy_check import OTAProxyCheck
from godzilla_scripts.functional_tests.ota_disable_auto_update import OTA_DISABLE_AUTO_UPDATE
from godzilla_scripts.functional_tests.ota_enable_auto_update import OTA_ENABLE_AUTO_UPDATE
from godzilla_scripts.functional_tests.ota_update_now import OTAUpdateNow
from platform_libraries.constants import Godzilla as GZA



class OTA_TEST_SUITE(GodzillaIntegrationTest):

    TEST_SUITE = 'GODZILLA PLATFORM Sanity'
    TEST_NAME = 'GODZILLA PLATFORM Sanity'
    # Popcorn
    PROJECT = 'godzilla'
    TEST_TYPE = 'functional'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'SANITY'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            if self.test_method == 'n_plus_one':
                """ Change to use fake fw version since 5.17.105, skip adding device to special buckets """
                # device_info = GZA.DEVICE_INFO.get(self.ssh_client.get_model_name())
                # ota_bucket_id = device_info.get('ota_special_bucket_{}'.format(self.env.cloud_env))
                self.integration.add_testcases(testcases=[
                    (OTAUpdateNow, {'start_fw': self.ota_start_fw, 'keep_fw_img': True,
                                    'local_image': self.local_image,  'update_mode': 'n_plus_one',
                                    'file_server_ip': self.file_server_ip,
                                    'ota_bucket_id': self.ota_bucket_id,
                                    'skip_data_integrity': self.skip_data_integrity,
                                    'TEST_NAME': 'OTA N+1 upgrade test', 'TEST_JIRA_ID': 'GZA-6953'})
                ])
            elif self.test_method == 'schedule':
                self.integration.add_testcases(testcases=[
                    (OTAUpdateNow, {'start_fw': self.ota_start_fw, 'keep_fw_img': True,
                                      'local_image': self.local_image, 'update_mode': 'daily',
                                      'ota_timeout': 7200, 'ota_retry_delay': 300,
                                      'file_server_ip': self.file_server_ip,
                                      'ota_bucket_id': self.ota_bucket_id,
                                      'skip_data_integrity': self.skip_data_integrity,
                                      'TEST_NAME': 'OTA schedule update - daily', 'TEST_JIRA_ID': 'GZA-6941,GZA-1567'}),
                    (OTAUpdateNow, {'start_fw': self.ota_start_fw, 'keep_fw_img': True,
                                    'local_image': self.local_image, 'update_mode': 'weekly',
                                    'ota_timeout': 7200, 'ota_retry_delay': 300,
                                    'file_server_ip': self.file_server_ip,
                                    'ota_bucket_id': self.ota_bucket_id,
                                    'skip_data_integrity': self.skip_data_integrity,
                                    'TEST_NAME': 'OTA schedule update - weekly', 'TEST_JIRA_ID': 'GZA-6942'})
                ])
            else:
                self.integration.add_testcases(testcases=[
                    OTAProxyCheck,
                    OTA_DISABLE_AUTO_UPDATE,
                    OTA_ENABLE_AUTO_UPDATE,
                    (OTAUpdateNow, {'start_fw': self.ota_start_fw, 'keep_fw_img': True,
                                    'local_image': self.local_image, 'update_mode': 'now',
                                    'file_server_ip': self.file_server_ip,
                                    'ota_bucket_id': self.ota_bucket_id,
                                    'skip_data_integrity': self.skip_data_integrity}),
                    (OTAUpdateNow, {'start_fw': self.ota_start_fw, 'keep_fw_img': True,
                                    'local_image': self.local_image, 'update_mode': 'random',
                                    'file_server_ip': self.file_server_ip,
                                    'ota_bucket_id': self.ota_bucket_id,
                                    'skip_data_integrity': self.skip_data_integrity,
                                    'TEST_NAME': 'OTA schedule update - random', 'TEST_JIRA_ID': 'GZA-6940'})
                ])


if __name__ == '__main__':
    parser = GodzillaIntegrationTestArgument("""\
        *** PLATFORM SANITY Test on Kamino Android ***
        Examples: ./run.sh godzilla_scripts/integration_tests/platform_sanity.py --uut_ip 10.136.137.159\
        """)

    # Test Arguments
    parser.add_argument('--single_run', help='Run single case for Platform Sanity Test')
    parser.add_argument('--ota_start_fw', help='The downgrade firmware version for OTA test', default='5.01.103')
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    parser.add_argument('--file_server_ip', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('-tm', '--test_method', choices=['default', 'n_plus_one', 'schedule'], default='default',
                        help='Select the test method to run')
    parser.add_argument('-oid', '--ota_bucket_id', help='Specified bucket id, can input "default" or "special" '
                                                        'to load the bucket id from constant file.', default="default")
    parser.add_argument('--skip_data_integrity', action='store_true', help='Skip upload files and compare checksum')

    test = OTA_TEST_SUITE(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
