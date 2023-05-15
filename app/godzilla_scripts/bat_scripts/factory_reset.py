# -*- coding: utf-8 -*-
""" Test case for Device Factory Reset
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.reboot import Reboot


class FactoryReset(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Factory Reset Test'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1149'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        if self.VERSION == "3.00":
            self.restsdk_stop_cmd = "/mnt/HD/HD_a2/Nas_Prog/RestSDK-dev1/stop.sh"
            self.restsdk_start_cmd = "/mnt/HD/HD_a2/Nas_Prog/RestSDK-dev1/start.sh"
        else:
            # 3.10 and later
            self.restsdk_stop_cmd = "restsdk.sh stop"
            self.restsdk_start_cmd = "sudo -u restsdk restsdk.sh start"

    def test(self):
        self.log.warning("Reset the RestSDK service as a replacement of factory reset")

        self.log.info("Step 1: Notify the cloud to delete device ID info")
        cmd = 'curl -i -X DELETE -H "Host: service.device.url" -H "Content-Type: application/json" ' \
              'http://localhost:8003/sdk/v1/cloudProxy/device/v1/device/device_identifier?sendNotification=false'
        result = self.ssh_client.execute_cmd(cmd)[0]
        if "200 OK" not in result:
            self.log.warning("Failed to notify cloud to delete the device ID info! Skip this step")

        self.log.info("Step 2: Stop RestSDK service")
        self.ssh_client.execute_cmd(self.restsdk_stop_cmd, timeout=60)
        response = self.ssh_client.get_restsdk_service()
        if response:
            raise self.err.TestFailure("Stop RestSDK service failed!")

        self.log.info("Step 3: Clean RestSDK data")
        stdout, stderr = self.ssh_client.execute_cmd("rm -rf /mnt/HD/HD_a2/restsdk-data")
        if stderr:
            raise self.err.TestFailure("Clean RestSDK data failed!")

        self.log.info("Step 4: Clean RestSDK info")
        stdout, stderr = self.ssh_client.execute_cmd("rm -rf /mnt/HD/HD_a2/restsdk-info")
        if stderr:
            raise self.err.TestFailure("Clean RestSDK info failed!")

        self.log.info("Step 5: Rebooting the device...")
        self.ssh_client.reboot_device()
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=60*20):
            raise self.err.TestFailure('Device was not shut down successfully!')

        if not self.ssh_client.wait_for_device_boot_completed(timeout=60*20):
            raise self.err.TestFailure('Device was not boot up successfully!')

        self.log.info("Restart RestSDK service if it's in minimal mode")
        self.ssh_client.disable_restsdk_minimal_mode()


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Reboot test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/factory_reset.py --uut_ip 10.136.137.159 \
        """)

    test = FactoryReset(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
