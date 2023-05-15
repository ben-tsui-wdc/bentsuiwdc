# -*- coding: utf-8 -*-
""" Share access full device test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import os
import sys
# platform modules
import time

from kdp_scripts.bat_scripts.nasadmin_samba_read_write import NasAdminSambaRW
from middleware.arguments import KDPInputArgumentParser
from platform_libraries.constants import KDP
from platform_libraries.common_utils import execute_local_cmd, delete_local_file


class ShareAccessFullDeviceTest(NasAdminSambaRW):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-5849 - Share access full device test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5849'

    def init(self):
        self.data_vol_path = KDP.DATA_VOLUME_PATH[self.uut['model']]
        self.full_file = '{}/full'.format(self.data_vol_path)
        self.lite_mode = True

    def before_test(self):
        super(ShareAccessFullDeviceTest, self).before_test()
        self.filename = 'test_file'
        self.file_path_in_device = '{}{}/{}'.format(KDP.SHARES_PATH, self.remote_space_name, self.filename)
        self.clear_test_data()

    def test(self):
        token = self.nasadmin.login_owner()
        self.nasadmin.update_user(
            token['userID'], localAccess=True, username=self.samba_user, password=self.samba_password)

        self.log.info('Checking disk capacity...')
        exit_status, output = self.ssh_client.execute(
            "df -h | grep " + self.data_vol_path + " | head -1 | awk '{ print $2 }'")
        if not output:
            raise self.err.StopTest('Cannot found data path')
        size_in_g = (int(float(output.strip()[:-1])) + 1) * 1000  # a number greater than disk capacity.
        self.log.info('Generating a file which size is {}G to fill up disk...'.format(size_in_g))
        exit_status, output = self.ssh_client.execute("busybox fallocate -l {}G {}".format(size_in_g, self.full_file))
        assert exit_status != 0, 'Success to create the file, seems file is too small, not fill up the disk'

        self.ssh_client.execute("df -h")
        self.reboot()
        self.ssh_client.execute("df -h")

        self.log.info("Mount test folder via Samba protocol")
        for idx in xrange(5):
            try:
                self.log.info("Creating {}".format(self.mountpoint))
                os.mkdir(self.mountpoint)

                stdout, _ = execute_local_cmd('mount', timeout=self.time_out)
                if self.mountpoint in stdout:
                    break

                self.log.info("Idle for 60 secs for SMB ready")
                time.sleep(60)

                self.mount_samba()
                break
            except:
                if idx == 4:
                    raise
                self.log.info("Clearing {} and try again...".format(self.mountpoint))
                try:
                    self.umount_share()
                except:
                    pass
                if os.path.exists(self.mountpoint):
                    execute_local_cmd('rm -r {}'.format(self.mountpoint), timeout=self.time_out)

        self.log.info("Writing test file...")
        execute_local_cmd('touch {}/{}'.format(self.mountpoint, self.filename), timeout=self.time_out)
        if not self.ssh_client.check_file_in_device(self.file_path_in_device):
            raise self.err.TestFailure('Write file failed!')

        self.log.info("Deleting test file...")
        delete_local_file('{}/{}'.format(self.mountpoint, self.filename))
        if self.ssh_client.check_file_in_device(self.file_path_in_device):
            raise self.err.TestFailure('Delete file failed!')

    def after_test(self):
        self.clear_test_data()
        self.log.info("Recovering test environment")
        token = self.nasadmin.login_owner()
        self.nasadmin.update_user(token['userID'], localAccess=False, username='', password='')
        self.reboot()

    def clear_test_data(self):
        self.log.info("Clearing test data...")
        mountpoint = self.mountpoint
        try:
            self.umount_share()
        except:
            pass
        if os.path.exists(mountpoint):
            execute_local_cmd('rm -r {}'.format(mountpoint), timeout=self.time_out)
        self.ssh_client.execute("test -e {0} && rm {0}".format(self.full_file))
        self.ssh_client.execute("test -e {0} && rm {0}".format(self.file_path_in_device))

    def reboot(self):
        self.ssh_client.reboot_device()
        self.ssh_client.wait_for_device_to_shutdown()
        self.ssh_client.wait_for_device_boot_completed()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Share access full device test ***
        """)

    test = ShareAccessFullDeviceTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
