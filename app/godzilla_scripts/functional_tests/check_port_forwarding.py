# -*- coding: utf-8 -*-
""" Test for API: GET /device/v1/device/{device_id}
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class CheckPortForwarding(GodzillaTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Check Port Forwarding Connection'
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
        if int(stdout) > 2:
            raise self.err.TestFailure('Wipe user root failed')
        self.log.info('Wipe user root completed.')

    def test(self):
        self.ssh_client.reset_restsdk()
        self.check_root_path()
        self.uut_owner.attach_user_to_device()
        result = self.uut_owner.get_device_info()
        pf_port = result.get('network').get('portForwardPort')
        self.log.info('port_forwarding_port:{}'.format(pf_port))
        assert pf_port > 0
        pf_status = result.get('network').get('portForwardInfoUpdateStatus')
        self.log.info('port_forwarding_status:{}'.format(pf_status))
        assert pf_status == "PORT_TEST_OK"


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Get_Device_info test on Kamino Android ***
        Examples: ./run.sh godzilla_scripts/functional_tests/get_device_info.py --uut_ip 10.136.137.159\
        """)

    test = CheckPortForwarding(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
