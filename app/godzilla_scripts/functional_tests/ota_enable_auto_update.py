# -*- coding: utf-8 -*-
""" JIRA Ticket of test steps: TBD
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
import pprint
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class OTA_ENABLE_AUTO_UPDATE(GodzillaTestCase):

    TEST_SUITE = 'Platform Functional Tests'
    TEST_NAME = 'OTA API Test'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-6936'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'OTA API'

    SETTINGS = {
        'enable_auto_ota': True
    }

    def test(self):
        self.ssh_client.ota_change_auto_update(mode='enabled')
        result = self.ssh_client.get_ota_update_status()
        self.log.info(result)
        if result.get('updatePolicy').get('mode') != 'enabled':
            raise self.err.TestFailure('Enable the OTA auto update failed!')

if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Get_Device_info test on Kamino Android ***
        Examples: ./run.sh godzilla_scripts/functional_tests/ota_disable_auto_update.py \
        --uut_ip 10.136.137.159 -env dev1 
        """)

    test = OTA_ENABLE_AUTO_UPDATE(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
