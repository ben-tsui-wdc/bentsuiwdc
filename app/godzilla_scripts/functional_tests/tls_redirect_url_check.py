# -*- coding: utf-8 -*-
""" Test case to check the device name
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.reboot import Reboot
from godzilla_scripts.bat_scripts.firmware_update import FirmwareUpdate
from godzilla_scripts.bat_scripts.factory_reset import FactoryReset


class TLSRedirectURLCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'TLS Redirect URL Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-8112,GZA-8113'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):

        env_dict = self.env.dump_to_dict()
        if self.pre_step == "reboot":
            self.TEST_JIRA_ID = 'GZA-8112'
            env_dict['Settings'] = ['uut_owner=False']
            reboot = Reboot(env_dict)
            reboot.no_rest_api = True
            reboot.test()
        elif self.pre_step == "fw_update":
            self.TEST_JIRA_ID = 'GZA-8113'
            firmware_update = FirmwareUpdate(env_dict)
            firmware_update.fw_version = self.env.firmware_version
            firmware_update.force_update = True
            firmware_update.before_test()
            firmware_update.test()
            firmware_update.after_test()
        elif self.pre_step == "factory_reset":
            # Blocked by GZA-8066: 429 too many requests
            self.TEST_JIRA_ID = 'GZA-8114'
            factory_reset = FactoryReset(env_dict)
            factory_reset.test()

        tls_info = self.ssh_client.get_tls_info()
        redirect_url = tls_info.get('redirect_url')
        if not redirect_url:
            raise self.err.TestFailure("Cannot find redirect URL from the TLS info!")

        self.log.info("Checking if the TLS redirect URL is accessible")
        response = self.ssh_client.execute_cmd("curl -I {}".format(redirect_url))[0]
        if "200 OK" not in response:
            raise RuntimeError("Failed to access the TLS URL!")
        else:
            self.log.info("Check the TLS redirect URL PASS!")


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Device Name Check test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/tls_redirect_url_check.py -ip 10.136.137.159 -model PR2100\
        """)

    parser.add_argument('-pre_step', '--pre_step', help='Run test steps before checking tls redirect url',
                        choices=['skip', 'reboot', 'fw_update', 'factory_reset'], default="skip")
    test = TLSRedirectURLCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
