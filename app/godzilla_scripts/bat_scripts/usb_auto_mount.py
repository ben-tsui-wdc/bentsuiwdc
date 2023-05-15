# -*- coding: utf-8 -*-
""" Test case to check USB device is mount on device
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.samba_rw_check import SambaRW


class USBAutoMount(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'USB Auto Mount Test'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1314,GZA-7194,GZA-7195,GZA-7196'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.usb_file_system = 'fat32'

    def test(self):
        usb_dict = self.ssh_client.get_usb_format()
        self.log.info(usb_dict)
        if self.usb_file_system.lower() not in usb_dict.values():
            raise self.err.TestFailure('Cannot find the USB with {} file system!'.format(self.usb_file_system))

        for usb_path, usb_fs in usb_dict.iteritems():
            self.log.info("usb_path: {}".format(usb_path))
            self.log.info("usb_fs: {}".format(usb_fs))
            if usb_fs == self.usb_file_system.lower():
                usb_share_info = self.ssh_client.execute_cmd('ls -al /shares/ | grep "{}"'.format(usb_path))[0]
                usb_share_path = usb_share_info.split()[-3]
                self.log.info("Run the SAMBA read write test on USB share path: {}".format(usb_share_path))
                smbrw = SambaRW(self)
                smbrw.share_folder = usb_share_path
                smbrw.keep_test_data = False
                smbrw.before_test()
                smbrw.test()
                smbrw.after_test()


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Device Name Check test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/usb_auto_mount.py --uut_ip 10.136.137.159 -model PR2100\
        """)
    parser.add_argument('-ufs', '--usb_file_system', help='The USB file system for testing', default="fat32")
    test = USBAutoMount(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
