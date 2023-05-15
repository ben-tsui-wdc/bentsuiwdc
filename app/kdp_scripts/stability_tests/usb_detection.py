# -*- coding: utf-8 -*-
""" Test for USB detection
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from platform_libraries.mcci_client import MCCIAPI
from platform_libraries.pyutils import retry
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class USBDetection(KDPTestCase):

    TEST_SUITE = 'Stability Tests'
    TEST_NAME = 'USB Detection Test'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-3236'
    PRIORITY = 'critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.mcci_url = None
        self.mcci_serno = None
        self.mcci_device = None
        self.usb_name = None

    def init(self):
        self.mcci = MCCIAPI(self.mcci_url)

    def before_test(self): # try to fix MCCI is not working sometimes
        if self.env.iteration%50 != 0:
            return
        try:
            self.log.info('checking MCCI')
            self.mcci.reattach_usb2(serno=self.mcci_serno, device=self.mcci_device)
            self.mcci.reattach_usb3(serno=self.mcci_serno, device=self.mcci_device)
        except Exception as e:
            self.log.warning(e, exc_info=True)

    def test(self):
        self.mcci.detach(serno=self.mcci_serno, device=self.mcci_device)
        retry(
            func=self.uut_owner.search_file_by_parent, parent_id=None, fields='id,name,storageType',
            retry_lambda=self.detach_usb_check, delay=5, max_retry=12, log=self.log.warning
        )
        self.mcci.attach_usb3(serno=self.mcci_serno, device=self.mcci_device)
        retry(
            func=self.uut_owner.search_file_by_parent, parent_id=None, fields='id,name,storageType',
            retry_lambda=self.attach_usb_check, delay=5, max_retry=12, log=self.log.warning
        )

    def detach_usb_check(self, resp):
        data_list, page_token = resp
        self.check_usb(data_list, usb_attached=False)

    def attach_usb_check(self, resp):
        data_list, page_token = resp
        self.check_usb(data_list, usb_attached=True)

    def check_usb(self, data_list, usb_attached):
        usbs = [item for item in data_list if item['storageType'] == 'usb']
        if usb_attached:
            if not usbs:
                raise self.err.TestFailure('No USB found from ReskSDK call, but expect USB found')
            self.log.info('USB found as expected')
            if self.usb_name:
                found = False
                for usb in usbs:
                    if usb['name'] == self.usb_name:
                        found = True
                if not found:
                    raise self.err.TestFailure('No USB name with "{}" found from ReskSDK call'.format(self.usb_name))
        else:
            if usbs:
                raise self.err.TestFailure('USB found from ReskSDK call, but expect no USB found')
            self.log.info('USB not found as expected')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** USB Detection for KDP ***
        """)

    parser.add_argument('-mu', '--mcci_url', help='MCCI server URL', metavar='PATH')
    parser.add_argument('-ms', '--mcci_serno', help='Serail number of MCCI device', metavar='serno', default=None)
    parser.add_argument('-md', '--mcci_device', help='Device number of MCCI device', metavar='device', default=None)
    parser.add_argument('-un', '--usb_name', help='Check USB stick name', metavar='name', default=None)

    test = USBDetection(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
