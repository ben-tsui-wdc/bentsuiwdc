# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: GET /v2/device - 200 - owner attached
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import subprocess
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class GetDeviceInfo(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Fetch general device information'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3799'

    def test(self):
        resp = self.nasadmin.get_device()
        self.verify_device_info(resp)
        if resp['redirectURL']:
            self.tls_access_check(url=resp['redirectURL'])
        else:
            self.log.info('redirectURL is empty, skip the link verify"')

    def verify_device_info(self, call_resp, owner_attached=True):
        assert call_resp['deviceType'] == self.uut['model'],\
            'deviceType: {} != {}'.format(call_resp['deviceType'], self.uut['model'])
        assert call_resp['ready'], 'Device is not ready'
        if owner_attached:
            assert call_resp['ownerAttached'], 'Owner is not attached'
        else:
            assert not call_resp['ownerAttached'], 'Owner is still attached'
        assert call_resp['maxSpaces'] == 100, 'Max space: {} != 100'.format(call_resp['maxSpaces'])
        assert call_resp['maxUsers'] == 300, 'Max users: {} != 300'.format(call_resp['maxUsers'])

    def tls_access_check(self, url, not_raise_error=True):
        self.log.info("Accessing the call with TLS")
        self.log.info("Make sure the test network can work with TLS")
        stdout = subprocess.Popen('curl -s {}/nas/v2/device'.format(url), shell=True, stdout=subprocess.PIPE).communicate()[0]
        self.log.info('Content: {}'.format(stdout))
        # Not work on VPN network
        try:
            assert '"maxSpaces":100' in stdout, 'Max space is not 100'
            assert '"maxUsers":300' in stdout, 'Max users is not 300'
            assert '"redirectURL":"https://device-local-' in stdout, 'MredirectURL is incorrect'
        except Exception as e:
            if not not_raise_error:
                raise e
            self.log.warning('Seem TLS is not working in this network\nGot an error: {}'.format(e))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get device information test ***
        """)

    test = GetDeviceInfo(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
