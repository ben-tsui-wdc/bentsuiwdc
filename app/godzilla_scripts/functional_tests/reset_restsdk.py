# -*- coding: utf-8 -*-
""" Test for API: GET /v1/device (KAM-16642).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.factory_reset import FactoryReset


class ResetRestSDK(GodzillaTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Reset RestSDK'
    # Popcorn
    PROJECT = 'godzilla'
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = ''
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = "GZA-170"

    USER_ROOT_PATH = "/mnt/HD/HD_a2/restsdk-data/userRoots/"

    def check_root_path(self):
        stdout, stderr = self.ssh_client.execute_cmd('ls -al {} | wc -l'.format(self.USER_ROOT_PATH))
        stdout = stdout.strip()
        if not stdout.isdigit():
            raise self.err.TestFailure('Unknown failure when check user root.')
        print("stdoud:{}".format(stdout))
        if int(stdout) < 3:
            raise self.err.TestFailure('Wipe user root failed')
        self.log.info('Wipe user root completed.')

    def test(self):
        factory_reset = FactoryReset(self)
        factory_reset.init()
        factory_reset.test()
        self.check_root_path()


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Get_Device_info test on Godzilla Platform ***
        Examples: ./run.sh godzilla_scripts/functional_tests/get_device_info.py --uut_ip 10.136.137.159\
        """)

    test = ResetRestSDK(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
