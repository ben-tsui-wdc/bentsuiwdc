# -*- coding: utf-8 -*-
""" Case to confirm the app log path /var/log/apps will reserve 10 MB space
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import urllib2
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.bat_scripts.reboot import Reboot


class CheckAppLogReserveSpace(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-3867 - [ANALYTICS] APP log path should reserve specific space as expected'
    TEST_JIRA_ID = 'KDP-3867'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.app_log_path = '/var/log/apps'
        self.log_path = '/var/log'

    def test(self):
        self.log.info("*** Step 1: Create a 5 MB data in the app logs path and get the checksum")
        self.ssh_client.execute_cmd("dd if=/dev/zero of={}/dummyfile bs=1M count=5".format(self.app_log_path))
        md5_before = self.ssh_client.get_file_md5_checksum(file_path='{}/dummyfile'.format(self.app_log_path))

        self.log.info("*** Step 2: Fill up all the space in /var/log")
        self.ssh_client.execute_cmd('busybox fallocate -l 1000M {}/1000M.bin'.format(self.log_path))

        self.log.info("*** Step 3: Reboot the device")
        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=False']
        reboot = Reboot(env_dict)
        reboot.no_rest_api = True
        reboot.main()

        self.log.info("*** Step 4: Verify the dymmyfile checksum and try to write a new file")
        md5_after = self.ssh_client.get_file_md5_checksum(file_path='{}/dummyfile'.format(self.app_log_path))
        if md5_before != md5_after:
            raise self.err.TestFailure('The dummyfile checksum was not matched! Before: {}, After: {}'.
                                       format(md5_before, md5_after))

        exit_status, output = self.ssh_client.execute("dd if=/dev/zero of={}/dummyfile2 bs=1M count=1".
                                                      format(self.app_log_path))
        if exit_status != 0:
            raise self.err.TestFailure('Failed to generate a new dummy file in /var/log/apps reserved space!')

    def after_test(self):
        self.log.info("Start cleaning the dummyfiles in the device")
        self._delete_file("{}/dummyfile".format(self.app_log_path))
        self._delete_file("{}/dummyfile2".format(self.app_log_path))
        self._delete_file("{}/1000M.bin".format(self.log_path))

    def _delete_file(self, file_path):
        if self.ssh_client.check_file_in_device(file_path):
            exit_status, output = self.ssh_client.execute("rm {}".format(file_path))
            if exit_status != 0:
                raise self.err.TestFailure('Failed to clean up test file: {} in the device!'.format(file_path))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_app_log_reserve_space.py --uut_ip 10.92.224.68\
        """)

    test = CheckAppLogReserveSpace(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
