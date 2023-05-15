# -*- coding: utf-8 -*-
""" For OTA Proxy error check (https://jira.wdmv.wdc.com/browse/IBIX-801)
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.reboot import Reboot
from platform_libraries.cloud_api import CloudAPI
from platform_libraries.nasadmin_api import NasAdminAPI


class OTAProxyCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'OTA Proxy Error Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1007'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': True,
        'enable_auto_ota': True
    }

    def init(self):
        self.cloud = CloudAPI(env=self.env.cloud_env)
        self.nasAdmin = NasAdminAPI(uut_ip=self.env.ssh_ip)

    def test(self):
        """
        try:
            reboot = Reboot(self)
            reboot.main()
        except Exception as e:
            raise self.err.TestSkipped('Reboot failed! Skipped the OTA proxy error check test! Error message: {}'.
                                       format(repr(e)))
        """
        # Skip this step since it's no loger needed (otaclient-2.0.0-189)
        # self.nasAdmin.ota_check_for_firmware_update_now()  # This step is necessary to get the ota status from cloud
        device_fw_version = self.ssh_client.get_firmware_version()
        device_id = self.uut_owner.get_local_code_and_security_code()[0]
        result = self.cloud.get_ota_status(device_id)
        self.log.info("OTA result:\n{}".format(pformat(result)))
        ota_data = result.get('data')
        ota_errors = result.get('error')
        current_version = ota_data.get('currVersion')
        # if the auto update is disabled, there will be no 'deviceUpdateStatusFailed' info,
        # check the 'statusUpd' instead.
        update_failed = ota_data.get('deviceUpdateStatusFailed')
        enable_auto_update = ota_data.get('statusUpd')

        if ota_errors is not None:
            raise self.err.TestFailure('The OTA was failed and the error was: {}!'.format(ota_errors))
        if update_failed != "false":
            if enable_auto_update == "DISABLE":
                self.log.info('The auto update is disabled so there is no update status in the cloud')
            else:
                raise self.err.TestFailure("Device Update Status Failed!")
        if device_fw_version != current_version:
            raise self.err.TestFailure('Current version in OTA status is not match the device firmware version!\
                                        OTA: {0}, Device: {1}'.format(current_version, device_fw_version))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Device Name Check test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/ota_proxy_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = OTAProxyCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
