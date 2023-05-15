# -*- coding: utf-8 -*-
""" For OTA Proxy error check
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.cloud_api import CloudAPI


class OTAProxyCheck(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-205 - OTA Proxy error check'
    TEST_JIRA_ID = 'KDP-205'

    SETTINGS = {
        'uut_owner': True,
        'enable_auto_ota': True
    }

    def init(self):
        self.cloud = CloudAPI(env=self.env.cloud_env)

    def test(self):
        device_fw_version = self.ssh_client.get_firmware_version()
        device_id = self.uut_owner.get_local_code_and_security_code()[0]
        result = self.cloud.get_ota_status(device_id)
        self.log.info("OTA result:\n{}".format(pformat(result)))
        ota_data = result.get('data')
        ota_errors = result.get('error')
        current_version = ota_data.get('currVersion')
        update_failed = ota_data.get('deviceUpdateStatusFailed')

        if ota_errors is not None:
            raise self.err.TestFailure('The OTA was failed and the error was: {}!'.format(ota_errors))
        if update_failed != "false":
            raise self.err.TestFailure("Device Update Status Failed!")
        if device_fw_version != current_version:
            raise self.err.TestFailure('Current version in OTA status is not match the device firmware version!\
                                        OTA: {0}, Device: {1}'.format(current_version, device_fw_version))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** OTA proxy error check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/ota_proxy_check.py --uut_ip 10.92.224.68\
        """)

    test = OTAProxyCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
