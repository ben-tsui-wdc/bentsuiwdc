# -*- coding: utf-8 -*-
""" Test cases to check USB device is mount on device.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP


class UsbAutoMount(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-196 - USB Auto mount on Device'
    TEST_JIRA_ID = 'KDP-196'

    def test(self):
        status, output = self.ssh_client.execute('ls {}'.format(KDP.MOUNT_PATH))
        self.usb_mount = output.strip()
        if self.usb_mount:
            usb_info = self.uut_owner.get_usb_info()
            self.usb_id = usb_info.get('id')
            self.usb_name = usb_info.get('name')
            self.log.info('USB Name is: {}'.format(self.usb_name))
            self.log.info('USB folder id is: {}'.format(self.usb_id))
        else:
            raise self.err.TestFailure('USB is not mounted!!!!')

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Check USB Auto Mounted Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/usb_auto_mount.py --uut_ip 10.92.224.68\
        """)

    test = UsbAutoMount(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
