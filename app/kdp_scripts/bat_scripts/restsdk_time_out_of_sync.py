# -*- coding: utf-8 -*-
""" Test cases to verify restsdk proxy connect when platform time out of sync.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
import urllib2
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class RestsdkProxyConnectTimeOutOfSync(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-4222 - Restsdk proxy connect verify when platform time out of sync'
    TEST_JIRA_ID = 'KDP-4222'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.set_time_to_past = 'busybox date -s "@1523824222"'
        self.get_proxy_connect_log = 'cat /var/log/wdpublic.log | grep connectivity'

    def test(self):
        self.log.info('Set time to past ...')
        self.ssh_client.execute(self.set_time_to_past)
        self.ssh_client.stop_restsdk_service()
        self.ssh_client.start_restsdk_service()
        proxy_connected = self.ssh_client.get_device_proxy_connect_status()
        if not proxy_connected:
            raise self.err.TestFailure('proxyConnected is false, test failed !!!')
        time.sleep(10)
        proxy_connect_log = self.ssh_client.execute_cmd(self.get_proxy_connect_log)[0]
        # tmp remove this check step due to KDP-4682, IBIX-6306
        #if 'x509' in proxy_connect_log or 'certificate has expired' in proxy_connect_log:
        #    raise self.err.TestFailure('x509: certificate has expired happened, test failed !!!')

    def after_test(self):
        self.log.info('Set time back to normal')
        self.ssh_client.execute('sntp_setup.sh')
        self.ssh_client.execute('date')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Restsdk proxy connect verify when platform time out of sync test script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/restsdk_time_out_of_sync.py --uut_ip 10.92.224.68\
        """)

    test = RestsdkProxyConnectTimeOutOfSync(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
