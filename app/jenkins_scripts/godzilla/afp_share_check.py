# -*- coding: utf-8 -*-
""" Tool for AFP share check.
"""
# std modules
import logging
from argparse import ArgumentParser
from datetime import datetime

# platform modules
from platform_libraries.shell_cmds import ShellCommands
from platform_libraries.ssh_client import SSHClient


class AFPShareCheck(object):

    def __init__(self, parser):
        self.base_path = '/tmp/test_' + datetime.today().strftime('%Y%m%d-%H%M%S')
        self.mount_point = parser.mount_point
        self.share_location = parser.share_location
        self.share_target = None
        self.ip = parser.ip
        self.user = parser.user
        self.password = parser.password

        self.run_write_test = parser.write_test
        self.keep_data = parser.keep_data
        self.verify_mount_fail = parser.verify_mount_fail
        self.verify_write_fail = parser.verify_write_fail
        self.remove_file = parser.remove_file

        self.ssh_client = SSHClient(parser.ssh_ip, parser.ssh_user, parser.ssh_password, parser.ssh_port)
        self.ssh_client.connect()

    def main(self):
        try:
            self.set_up_workspace()
            self.create_mount_point()
            try:
                self.ssh_client.log.info('|- Mount share...')
                self.share_target = '{}/{}'.format(self.ip, self.share_location)
                mount_success = self.ssh_client.mount_afp_on_mac(
                    afp_user=self.user, afp_password=self.password, share_location=self.share_target, mount_point=self.mount_point)
                if self.verify_mount_fail:
                    if mount_success:
                        raise RuntimeError('Mount share successfully which does not perform as expected')
                    else:
                        self.ssh_client.log.info('Unable to mount share')
                        return
                if not mount_success:
                    raise RuntimeError("Fail to mount share")
                self.ssh_client.log.info('Mount share successfully')
                if self.run_write_test: self.write_test()
                if self.verify_write_fail: self.write_fail_test()
                if self.remove_file: self.clean_file(self.remove_file)
            finally:
                if not self.keep_data: self.clean_data()
                self.ssh_client.log.info('|- Umount share...')
                if not self.ssh_client.umount_afp_on_mac(mount_point=self.mount_point):
                    self.ssh_client.log.error('Fail to umoint share')
                self.ssh_client.log.info('Umount share successfully')
        finally:
            self.tear_down_workspace()
            self.ssh_client.close()

    def set_up_workspace(self):
        self.ssh_client.log.info('|- Preparing workspace...')
        exitcode, _ = self.ssh_client.execute(command='mkdir {0} && cd {0}'.format(self.base_path))
        if exitcode != 0: raise RuntimeError("Fail to create workspace")

    def tear_down_workspace(self):
        self.ssh_client.log.info('|- Clean up workspace...')
        exitcode, _ = self.ssh_client.execute(command='test -e {0} && rm -r {0}'.format(self.base_path))
        if exitcode != 0: raise RuntimeError("Fail to clean up workspace")

    def create_mount_point(self):
        self.ssh_client.log.info('|- Preparing moint point...')
        exitcode, _ = self.ssh_client.execute(command='test -e {0} || mkdir {0}'.format(self.mount_point))
        if exitcode != 0: raise RuntimeError("Fail to create local mount point")

    def write_test(self):
        self.ssh_client.log.info('|- Writing a small data to share...')
        exitcode, _ = self.ssh_client.execute(command='echo test > {}/testfile'.format(self.mount_point))
        if exitcode != 0: raise RuntimeError("Fail to write test data on share")
        self.ssh_client.log.info('Write a small data to share successfully')

    def write_fail_test(self):
        self.ssh_client.log.info('|- Trying to write share and expect it fail...')
        exitcode, _ = self.ssh_client.execute(command='echo test > {}/testfile'.format(self.mount_point))
        if exitcode == 0: raise RuntimeError("Successful to write share which does not perform as expected")
        self.ssh_client.log.info('Fail to write share as expected')

    def clean_data(self):
        self.ssh_client.log.info('|- Clean up test data...')
        if self.run_write_test:
            self.clean_file('testfile')

    def clean_file(self, filename):
        # File deleted or not found are both successful.
        exitcode, _ = self.ssh_client.execute(command='test -e {0}/{1} && rm {0}/{1} || echo no file found'.format(self.mount_point, filename))
        if exitcode != 0: raise RuntimeError("Fail to clean file: {}".format(filename))
        self.ssh_client.log.info('Clean up file: {} successfully'.format(filename))


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** AFP share check. ***
        """)

    parser.add_argument('-mp', '--mount-point', help='Mount point', metavar='MP', default='test')
    parser.add_argument('-sl', '--share-location', help='Remote share location', metavar='LF')
    parser.add_argument('-ip', '--ip', help='Device IP', metavar='IP')
    parser.add_argument('-user', '--user', help='The username of SMB', default=None)
    parser.add_argument('-password', '--password', help='The password of SMB', metavar='PWD', default=None)
    parser.add_argument('-si', '--ssh-ip', help='SSH server IP on bridge MAC', metavar='IP')
    parser.add_argument('-su', '--ssh-user', help='The username of SSH server on bridge MAC', default="sshd")
    parser.add_argument('-sp', '--ssh-password', help='The password of SSH server on bridge MAC', metavar='PWD', default="Test1234")
    parser.add_argument('-spt', '--ssh-port', help='The port of SSH server on bridge MAC', type=int, metavar='PORT', default=22)
    parser.add_argument('-w', '--write-test', help='Write a small file to SMB share', action='store_true', default=False)
    parser.add_argument('-kd', '--keep-data', help='keep everything generated in share during the test', action='store_true', default=False)
    parser.add_argument('-mf', '--verify-mount-fail', help='Verify mount share is fail', action='store_true', default=False)
    parser.add_argument('-wf', '--verify-write-fail', help='Verify write share is fail', action='store_true', default=False)
    parser.add_argument('-rf', '--remove-file', help='Remove a file in share', default=None)

    AFPShareCheck(parser.parse_args()).main()
