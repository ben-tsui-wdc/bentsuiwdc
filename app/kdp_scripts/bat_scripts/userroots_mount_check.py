# -*- coding: utf-8 -*-
""" Test case to check the userRoots mount point is mounted on the test device
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP
from platform_libraries.constants import RnD


class UserRootsMountOnDevice(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = '   KDP-210 - UserRoots Check'
    TEST_JIRA_ID = 'KDP-210'
    ISSUE_JIRA_ID = None

    def init(self):
        self.model = self.uut.get('model')

    def test(self):
        wd_disk_mounted = self.ssh_client.execute('getprop sys.wd.disk.mounted')[1]
        if wd_disk_mounted != '1':
            raise self.err.TestFailure("Disk does not mounted!")

        exitcode, _ = self.ssh_client.execute('mount | grep {}'.format(KDP.DATA_VOLUME_PATH.get(self.model)))
        if exitcode != 0:
            raise self.err.TestFailure("diskVolume0 is not in the mount list")

        self.log.info("Checking userRoots path")
        if self.ssh_client.check_is_kdp_device():
            user_roots_path = KDP.USER_ROOT_PATH
        else:
            user_roots_path = RnD.USER_ROOT_PATH
        if not self.ssh_client.check_folder_in_device(user_roots_path):
            raise self.err.TestFailure('The userRoots folder does not exist, test Failed!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Check userRoots Mount on Device test ***
        Examples: ./run.sh kdp_scripts/bat_scripts/userroots_mount_check.py --uut_ip 10.136.137.159 -env qa1\
        """)

    test = UserRootsMountOnDevice(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)