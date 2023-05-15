# -*- coding: utf-8 -*-
""" Samba R/W Test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import os
import sys
import time
import numbers
# platform modules
from samba_rw_check import SambaRW
from middleware.arguments import KDPInputArgumentParser
from platform_libraries.assert_utls import assert_dict, assert_dict_with_value_type
from platform_libraries.common_utils import execute_local_cmd, delete_local_file
from platform_libraries.constants import RnD


class NasAdminSambaRW(SambaRW):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-5519 - nasAdmin - Samba R/W Test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5519'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': True
    }

    def declare(self):
        super(NasAdminSambaRW, self).declare()
        self.samba_user = 'owner'
        self.samba_password = 'password'
        self.remote_space_name = 'SambaSpace'
        self.lite_mode = False

    def before_test(self):
        super(NasAdminSambaRW, self).before_test()
        if self.lite_mode:
            owner_cloud_user = self.uut_owner.get_cloud_user()
            self.remote_space_name = owner_cloud_user['user_metadata']['first_name']
        self.sharelocation = '//{}/{}'.format(self.env.ssh_ip, self.remote_space_name)
        self.file_path_in_device = '{}{}/{}'.format(RnD.SHARE_PATH, self.remote_space_name, self.filename)

    def test(self):
        if self.lite_mode:
            token = self.nasadmin.login_owner()
            owner = self.nasadmin.get_user(token['userID'])
        else:
            owner = self.nasadmin.get_owner()

        updated_owner = self.nasadmin.update_user(
            owner['id'], localAccess=True, username=self.samba_user, password=self.samba_password
        )
        assert updated_owner['localAccess'], "localAccess is not true"
        assert updated_owner['username'] == self.samba_user, \
            "username: {} != {}".format(updated_owner['username'], self.samba_user)

        space = None
        try:
            if not self.lite_mode:
                space = self.nasadmin.create_space(self.remote_space_name, allUsers=True)
                expected_space = {
                    'userID': '',
                    'name': self.remote_space_name,
                    'systemName': '',
                    'allUsers': True,
                    'localPublic': False,
                    'usageBytes': 0,
                    'timeMachine': False
                }
                assert_dict(space, expected_space)

            self.log.info("Create a dummy test file: {}".format(self.filename))
            execute_local_cmd('dd if=/dev/urandom of={} bs=1M count={}'.format(self.filename, self.count))
            local_md5, _ = execute_local_cmd('md5sum {}'.format(self.filename))

            self.log.info("Mount test folder via Samba protocol")
            if not os.path.isdir(self.mountpoint):
                os.mkdir(self.mountpoint)
            self.mount_samba()

            self.log.info("Start the Write test")
            execute_local_cmd('cp -f {} {}/'.format(self.filename, self.mountpoint), timeout=self.time_out)
            if not self.ssh_client.check_file_in_device(self.file_path_in_device):
                raise self.err.TestFailure('Upload file failed!')

            device_md5, _ = self.ssh_client.execute_cmd('md5sum {}'.format(self.file_path_in_device))
            if not local_md5.split()[0] == device_md5.split()[0]:
                raise self.err.TestFailure('Basic Samba Write Test Failed! Error: md5 checksum not match!!')

            self.log.info("Start the Read test")
            execute_local_cmd('cp -f {}/{} {}_copy'.format(self.mountpoint, self.filename, self.filename),
                              timeout=self.time_out)
            if not os.path.isfile('{}_copy'.format(self.filename)):
                raise self.err.TestFailure('Download file failed!')

            self.log.info("Compare the md5 checksum")
            local_copy_md5, _ = execute_local_cmd('md5sum {0}_copy'.format(self.filename))
            if not local_md5.split()[0] == local_copy_md5.split()[0]:
                raise self.err.TestFailure('Basic Samba Read Test Failed! Error: md5 checksum not match!!')
        finally:
            self.nasadmin.update_user(
                owner['id'], localAccess=False, username='', password=''
            )
            if not self.lite_mode and space:
                self.log.info('Remove existing local space')
                self.nasadmin.delete_spaces(space['id'])

    def after_test(self):
        output, _ = execute_local_cmd('mount')
        if self.remote_space_name in output:
            self.umount_share()
        delete_local_file(self.filename)
        delete_local_file("{}_copy".format(self.filename))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** nasAdmin - Samba R/W Test ***
        """)
    parser.add_argument('-lite', '--lite_mode', help='Execute for lite mode', action='store_true')

    test = NasAdminSambaRW(parser)
    resp = test.main()
    print 'test result: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
