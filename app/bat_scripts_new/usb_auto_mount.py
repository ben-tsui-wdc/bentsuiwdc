# -*- coding: utf-8 -*-
""" Test cases to check USB device is mount on device.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class UsbAutoMount(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'USB Auto Mount Test'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13983'
    COMPONENT = 'PLATFORM'

    def init(self):
        self.mount_path = '/mnt/media_rw/'

    def test(self):
        model = self.uut.get('model')
        if model == 'yoda':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(model))
        self.usb_mount = self.adb.executeShellCommand('ls {}'.format(self.mount_path))[0].strip()
        if self.usb_mount:
            usb_info = self.uut_owner.get_usb_info()
            self.usb_id = usb_info.get('id')
            self.usb_name = usb_info.get('name')
            self.log.info('USB Name is: {}'.format(self.usb_name))
            self.log.info('USB folder id is: {}'.format(self.usb_id))
        else:
            raise self.err.TestFailure('USB is not mounted!!!!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Check USB Auto Mounted Script ***
        Examples: ./run.sh bat_scripts_new/usb_auto_mount.py --uut_ip 10.92.224.68\
        """)

    test = UsbAutoMount(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
