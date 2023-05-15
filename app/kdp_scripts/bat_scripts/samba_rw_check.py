# -*- coding: utf-8 -*-
""" Test cases to check Samba Read/Write test.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import os
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.common_utils import execute_local_cmd
from platform_libraries.common_utils import delete_local_file
from platform_libraries.constants import KDP


class SambaRW(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = '   KDP-202 - Samba IO Test'
    TEST_JIRA_ID = 'KDP-202'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.samba_user = None
        self.samba_password = None
        self.samba_version = "3.0"
        self.keep_test_data = False

    def before_test(self):
        self.model = self.uut.get('model')
        self.time_out = 60*5
        self.sharelocation = '//{0}/Public'.format(self.env.ssh_ip)
        self.mountpoint = '/mnt/cifs_Public'
        self._ismounted = False
        self.count = 50
        self.filename = 'test{}MB'.format(self.count)

    def test(self):
        if not os.path.isdir(self.mountpoint):
            os.mkdir(self.mountpoint)
        self.log.info("Step 1: Mount test folder via Samba protocol")
        self.mount_samba()

        self.log.info("Step 2: Create a dummy test file: {}".format(self.filename))
        execute_local_cmd('dd if=/dev/urandom of={0} bs=1M count={1}'.format(self.filename, self.count))

        self.log.info("Step 3: Start the Write test")
        execute_local_cmd('cp -f {0} {1}'.format(self.filename, self.mountpoint), timeout=self.time_out)
        if not self.ssh_client.check_file_in_device('{0}/samba/share/{1}'.format(KDP.DATA_VOLUME_PATH.get(self.model), self.filename)):
            raise self.err.TestFailure('Upload file failed!')

        self.log.info("Step 4: Compare the md5 checksum")
        local_md5 = execute_local_cmd('md5sum {0}'.format(self.filename))[0]
        device_md5 = self.ssh_client.execute_cmd('busybox md5sum {0}/samba/share/{1}'.format(KDP.DATA_VOLUME_PATH.get(self.model), self.filename))[0]
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

    def after_test(self):
        if not self.keep_test_data:
            self.log.info("Clean the test data after testing")
            # self.remove_all_files(self.mountpoint)  # Todo: Check the /mnt/cifs/.smbm.xml delete error
            execute_local_cmd('rm {}/{}'.format(self.mountpoint, self.filename))
        self.umount_share()
        delete_local_file(self.filename)
        delete_local_file("{}_clone".format(self.filename))

    def mount_samba(self):
        user = self.samba_user
        password = self.samba_password
        mountpoint = self.mountpoint
        sharelocation = self.sharelocation

        if user is None:
            authentication = 'guest'
        else:
            if password is None:
                password = ''

            authentication = 'username=' + user + ',password=' + password

        mount_cmd = 'mount.cifs'
        mount_args = (sharelocation +
                      ' ' +
                      mountpoint +
                      ' -o ' +
                      authentication +
                      ',' +
                      'rw,nounix,file_mode=0777,dir_mode=0777,vers={}'.format(self.samba_version))

        # Run the mount command
        self.log.info('Mounting {} '.format(sharelocation))
        execute_local_cmd(mount_cmd + ' ' + mount_args)
        mounted = execute_local_cmd('df')[0]
        if self.mountpoint in mounted:
            self._ismounted = True
        else:
            raise self.err.TestFailure('Mount samba folder failed!')

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


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Samba Read/Write Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/samba_rw_check.py --uut_ip 10.200.141.68\
        """)

    # Test Arguments
    parser.add_argument('--samba_user', help='Samba login user name', default=None)
    parser.add_argument('--samba_password', help='Samba login password', default=None)
    parser.add_argument('--samba_version', help='Samba version, 1.0/2.1/3.0', default="3.0")
    parser.add_argument('--keep_test_data', help='Test data will not be deleted after testing',
                        action='store_true', default=False)

    test = SambaRW(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
