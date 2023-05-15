# -*- coding: utf-8 -*-
""" Test cases to check share_user_access
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"
# std modules
import sys
import os
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.common_utils import execute_local_cmd


class CheckShareUserAccess(GodzillaTestCase):
    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Check Share User Access'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1041'
    PRIORITY = 'Blocker'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.samba_user = "admin"
        self.samba_password = "adminadmin"
        self.share_folder = "test_share_permission"
        self.user_permission = 1  # 1: Read only, 2: Rear Write, 3: Deny

    def before_test(self):
        self.permission = {"1": "Read Only", "2": "Read Write", "3": "Deny"}.get(self.user_permission)
        self.time_out = 60*5
        self.sharelocation = '//{0}/{1}'.format(self.env.ssh_ip, self.share_folder)
        self.mountpoint = '/mnt/cifs'
        self._ismounted = False
        self.count = 50
        self.filename = 'test{}MB'.format(self.count)

        share_folders = self.ssh_client.get_share_permission()  # Used for check if share folder already exist
        if self.share_folder not in share_folders.keys():
            if not self.ssh_client.create_share(share_name=self.share_folder):
                raise self.err.TestFailure('Create share folder: "{}" failed!'.format(self.share_folder))

        if self.permission != "Deny":
            # Deny permission will not be able to login and no need to create test files
            self.log.info("Create a dummy test file locally: {}".format(self.filename))
            execute_local_cmd('dd if=/dev/urandom of={0} bs=1M count={1}'.format(self.filename, self.count))

        if self.permission == "Read Only":
            self.log.info("Before testing Rest Only permission, we need to upload a file to the share folder")
            if not self.ssh_client.change_share_public_status(share_name=self.share_folder, public=True):
                raise self.err.TestFailure('Change share public status failed!')
            self.mount_samba()
            execute_local_cmd('cp -f {0} {1}'.format(self.filename, self.mountpoint), timeout=self.time_out)
            if not self.ssh_client.check_file_in_device('/shares/{0}/{1}'.format(self.share_folder, self.filename)):
                raise self.err.TestFailure('Failed to upload file before testing!')

            self.log.info("Compare the md5 checksum")
            local_md5 = execute_local_cmd('md5sum {0}'.format(self.filename))[0]
            device_md5 = self.ssh_client.execute_cmd('md5sum /shares/{0}/{1}'.format(self.share_folder, self.filename))[0]
            if not local_md5.split()[0] == device_md5.split()[0]:
                raise self.err.TestFailure('The md5 checksum were not match!')
            self.umount_share()

    def test(self):
        self.log.info("Setup the user permission: {} on test share folder".format(self.permission))
        if not self.ssh_client.change_share_public_status(share_name=self.share_folder, public=False):
            raise self.err.TestFailure('Change share public status failed!')

        if not self.ssh_client.change_share_user_permission(share_name=self.share_folder,
                                                            user=self.samba_user, permission=int(self.user_permission)):
            raise self.err.TestFailure('Change share user permission failed!')

        if self.permission == "Deny":
            try:
                self.mount_samba()
                raise self.err.TestFailure('Mount Samba successfully but user should have been denied!')
            except Exception as e:
                self.log.info("User has been denied to access the share folder as expected")
        else:
            self.mount_samba()
            if self.permission == "Read Write":  # test write before read
                self.log.info("Start the Write test")
                execute_local_cmd('cp -f {0} {1}'.format(self.filename, self.mountpoint), timeout=self.time_out)
                if not self.ssh_client.check_file_in_device('/shares/{0}/{1}'.format(self.share_folder, self.filename)):
                    raise self.err.TestFailure('Upload file failed!')

                self.log.info("Compare the md5 checksum")
                local_md5 = execute_local_cmd('md5sum {0}'.format(self.filename))[0]
                device_md5 = self.ssh_client.execute_cmd('md5sum /shares/{0}/{1}'.format(self.share_folder, self.filename))[0]
                if not local_md5.split()[0] == device_md5.split()[0]:
                    raise self.err.TestFailure('Basic Samba Write Test Failed! Error: md5 checksum not match!!')

            self.log.info("Start the Read test")
            execute_local_cmd('cp -f {0}/{1} {2}_clone'.format(self.mountpoint, self.filename, self.filename),
                              timeout=self.time_out)
            if not os.path.isfile('./{}_clone'.format(self.filename)):
                raise self.err.TestFailure('Download file failed!')

            self.log.info("Compare the md5 checksum")
            local_md5 = execute_local_cmd('md5sum {0}'.format(self.filename))[0]
            local_clone_md5 = execute_local_cmd('md5sum {0}_clone'.format(self.filename))[0]
            if not local_md5.split()[0] == local_clone_md5.split()[0]:
                raise self.err.TestFailure('Basic Samba Read Test Failed! Error: md5 checksum not match!!')

            if self.permission == "Read Only":
                self.log.info("Try to upload files in by a Read Only user and test should be failed")
                try:
                    execute_local_cmd('touch {0}/ro.txt'.format(self.mountpoint), timeout=self.time_out)
                    raise self.err.TestFailure('Read Only users should not be able to write files!')
                except Exception as e:
                    self.log.info("Read Only users cannot write files as expected")

    def after_test(self):
        if self.permission != "Deny":
            self.umount_share()
            os.remove(self.filename)
        if not self.ssh_client.delete_share(share_name=self.share_folder):
            raise self.err.TestFailure('Delete share folder: "{}" failed! '.format(self.share_folder))

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

        if not os.path.exists(self.mountpoint):
            os.mkdir(self.mountpoint)

        mount_cmd = 'mount.cifs'
        mount_args = (sharelocation +
                      ' ' +
                      mountpoint +
                      ' -o ' +
                      authentication +
                      ',' +
                      'rw,nounix,file_mode=0777,dir_mode=0777')
        # Run the mount command
        self.log.info('Mounting {} '.format(sharelocation))
        execute_local_cmd(mount_cmd + ' ' + mount_args)
        mounted = execute_local_cmd('df')[0]
        if self.mountpoint in mounted:
            self._ismounted = True
        else:
            raise self.err.TestFailure('Mount samba folder failed!')

    def umount_share(self):
        umount_cmd = 'umount'
        umount_args = '-l -f ' + self.mountpoint
        # Run the umount command
        execute_local_cmd(umount_cmd + ' ' + umount_args)
        os.rmdir(self.mountpoint)
        # Clear the mountpoint
        self._ismounted = False


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Samba Read/Write Check Script ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/check_share_user_access.py --uut_ip 10.136.137.159 -model PR2100\
        """)
    # Test Arguments
    parser.add_argument('--samba_user', help='Samba login user name', default="admin")
    parser.add_argument('--samba_password', help='Samba login password', default="admin")
    parser.add_argument('--share_folder', help='Share folder name to test', default="test_share_permission")
    parser.add_argument('--user_permission', choices=["1", "2", "3"], default="1",
                        help='User permission to the test folder, 1: Read Only, 2: Rear Write, 3: Deny')
    test = CheckShareUserAccess(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)