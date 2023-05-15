# -*- coding: utf-8 -*-
""" Test cases to check NFS Read/Write test.
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import os

# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.common_utils import execute_local_cmd
from platform_libraries.common_utils import delete_local_file


class NFSRW(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Basic NFS Read Write Test'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1529'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.skip_enable_folder_nfs = False
        self.skip_enable_service = False
        self.disable_share_nfs = False
        self.share_folder = 'Public'

    def init(self):
        self.time_out = 60*5
        self.sharelocation = '{}:/nfs/{}'.format(self.env.ssh_ip, self.share_folder)  # Todo: Replace with showmount result
        self.mountpoint = '/mnt/nfs'
        self._ismounted = False
        self.count = 50
        self.filename = 'test{}MB'.format(self.count)

    def before_test(self):
        if not self.skip_enable_service:
            self.ssh_client.enable_nfs_service()

        if not self.skip_enable_folder_nfs:
            if self.disable_share_nfs:
                self.ssh_client.disable_share_nfs(share_name=self.share_folder)
            else:
                self.ssh_client.enable_share_nfs(share_name=self.share_folder)

    def test(self):
        if not os.path.isdir(self.mountpoint):
            os.mkdir(self.mountpoint)
        self.log.info("Step 1: Mount test folder via Samba protocol")
        self.mount_nfs()
        self.log.info("Step 2: Create a dummy test file: {}".format(self.filename))
        execute_local_cmd('dd if=/dev/urandom of={0} bs=1M count={1}'.format(self.filename, self.count))

        self.log.info("Step 3: Start the Write test")
        execute_local_cmd('cp -f {0} {1}'.format(self.filename, self.mountpoint), timeout=self.time_out)
        if not self.ssh_client.check_file_in_device('/shares/Public/{}'.format(self.filename)):
            raise self.err.TestFailure('Upload file failed!')

        self.log.info("Step 4: Compare the md5 checksum")
        local_md5 = execute_local_cmd('md5sum {0}'.format(self.filename))[0]
        device_md5 = self.ssh_client.execute_cmd('busybox md5sum {0}/{1}'.format('/shares/Public', self.filename))[0]
        if not local_md5.split()[0] == device_md5.split()[0]:
            raise self.err.TestFailure('Basic Samba Write Test Failed! Error: md5 checksum not match!!')

        self.log.info("Step 5: Start the Read test")
        execute_local_cmd('cp -f {0}/{1} {2}_clone'.format(self.mountpoint, self.filename, self.filename),
                          timeout=self.time_out)
        if not os.path.isfile('./{}_clone'.format(self.filename)):
            raise self.err.TestFailure('Download file failed!')

        self.log.info("Step 6: Compare the md5 checksum")
        local_clone_md5 = execute_local_cmd('md5sum {0}_clone'.format(self.filename))[0]
        if not local_md5.split()[0] == local_clone_md5.split()[0]:
            raise self.err.TestFailure('Basic Samba Read Test Failed! Error: md5 checksum not match!!')

    def mount_nfs(self):
        mountpoint = self.mountpoint
        sharelocation = self.sharelocation

        mount_cmd = 'mount.nfs -o nolock {0} {1}'.format(sharelocation, mountpoint)
        # Run the mount command
        self.log.info('Mounting {} '.format(sharelocation))
        execute_local_cmd(mount_cmd)
        mounted = execute_local_cmd('df')[0]
        if self.mountpoint in mounted:
            self._ismounted = True
        else:
            raise self.err.TestFailure('Mount NFS folder failed!')

    def remove_all_files(self, path):
        import shutil
        for root, dirs, files in os.walk(path):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))

    def umount_share(self):
        umount_cmd = 'umount'
        umount_args = '-l -f ' + self.mountpoint

        # Run the umount command
        execute_local_cmd(umount_cmd + ' ' + umount_args)
        os.rmdir(self.mountpoint)

        # Clear the mountpoint
        self.mountpoint = None
        self._ismounted = False

    def after_test(self):
        self.remove_all_files(self.mountpoint)
        self.umount_share()
        delete_local_file(self.filename)


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** NFS Read/Write Check Script ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/nfs_rw_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    # Test Arguments
    parser.add_argument('--skip_enable_service', help='do not enable the service before testing', action='store_true')
    parser.add_argument('--skip_enable_folder_nfs', help='do not enable the share folder nfs access before testing', action='store_true')
    parser.add_argument('--disable_share_nfs', help='disable the nfs function in share folder for negative tests', action='store_true')
    parser.add_argument('--share_folder', help='The test share folder name', default="Public")

    test = NFSRW(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
