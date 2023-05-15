# -*- coding: utf-8 -*-
""" Test case to check partition and size for RND project
    https://jira.wdmv.wdc.com/browse/KDP-4041
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import os
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class PartitionAndSizeVerify(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-4041 - Verify partition and size'
    TEST_JIRA_ID = 'KDP-4041'

    SETTINGS = {
        'uut_owner': False
    }

    def before_test(self):
        if not self.ssh_client.check_is_rnd_device():
            raise self.err.TestSkipped('Device is not Rocket or Drax, skipped the test')

    def test(self):
        self.log.info('Verify SYS_CONFIGS partition ...')
        cur_cfg = self.ssh_client.execute_cmd('cat /proc/device-tree/factory/cur_cfg')[0]
        if 'P' in cur_cfg:
            self.check_partition_mount_and_size(mountpoint='/sys_configs', label='SYS_CONFIGS', size=32)
        else:
            self.check_partition_mount_and_size(mountpoint='/sys_configs', label='SYS_CONFIGS_BKUP', size=32)
        self.log.info('Verify KDP_FW partition ...')
        cur_fw = self.ssh_client.execute_cmd('cat /proc/device-tree/factory/cur_fw')[0]
        if 'A' in cur_fw:
            self.check_partition_mount_and_size(mountpoint='/usr/local/tmp', label='KDP_FW_A', size=1024)
        else:
            self.check_partition_mount_and_size(mountpoint='/usr/local/tmp', label='KDP_FW_B', size=1024)
        self.log.info('Verify PLATFORM_CONFIGS partition ...')
        self.check_partition_mount_and_size(mountpoint='/platform_configs', label='PLATFORM_CONFIGS', size=64)
        self.log.info('Verify KDP_LOGS partition ...')
        self.check_partition_mount_and_size(mountpoint='/kdp_logs', label='KDP_LOGS', size=512)
        self.log.info('Verify OTA_DOWNLOAD partition ...')
        self.check_partition_mount_and_size(mountpoint='/ota_download', label='OTA_DOWNLOAD', size=2048)
        self.log.info('Verify NAS_ADMIN partition ...')
        self.check_partition_mount_and_size(mountpoint='/nas_admin', label='NAS_ADMIN', size=1024)
        self.log.info('Verify apps log partition ...')
        self.check_partition_mount_and_size(mountpoint='/app_logs', label='APP_LOGS', size=256)
        self.log.info('Verify NAS_ADMIN_HDD partition size ...')
        self.check_partition_mount_and_size(mountpoint='/nas_admin_hdd', label='NAS_ADMIN_HDD', size=1024, check_size_only=True)

    def check_partition_mount_and_size(self, mountpoint, label, size, check_size_only=False):
        df = self.ssh_client.execute_cmd('df -T -BM | grep "{}"'.format(mountpoint))[0]
        mounted_path = df.split()[0]
        mounted_size = df.split()[2]
        if not check_size_only:
            blkid = self.ssh_client.execute_cmd('blkid -L {}'.format(label))[0]
            if mounted_path != blkid:
                raise self.err.TestFailure('Partition path is not match, label:{0}, mount path:{1}, Test failed !!!'
                                            .format(label, mounted_path))
        if not int(size)*0.8 < int(mounted_size) < int(size)*1.2:
            raise self.err.TestFailure('Partition size({0}MB) is not match with define({1}MB), Test Failed !!!'
                                        .format(mounted_size, size))

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Partition and Size Verify Test Script ***
        Examples: ./run.sh kdp_scripts/app_manager_scripts/platform_partition_verify_rnd.py --uut_ip 10.92.224.68\
        """)

    test = PartitionAndSizeVerify(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
