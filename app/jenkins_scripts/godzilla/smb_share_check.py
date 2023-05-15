# -*- coding: utf-8 -*-
""" Tool for SMB share check.
"""
# std modules
import logging
from argparse import ArgumentParser

# platform modules
from platform_libraries.shell_cmds import ShellCommands
from platform_libraries.ssh_client import SSHClient


class SMBShareCheck(object):

    def __init__(self, parser):
        self.mount_point = parser.mount_point
        self.share_location = parser.share_location
        self.share_target = None
        self.ip = parser.ip
        self.user = parser.user
        self.password = parser.password

        self.check_usb = parser.check_usb
        self.run_write_test = parser.write_test
        self.run_clean_data = parser.clean_data
        self.verify_mount_fail = parser.verify_mount_fail
        self.verify_write_fail = parser.verify_write_fail
        self.verify_write_full_share_fail = parser.verify_write_full_share_fail
        self.check_share_size = parser.check_share_size
        self.check_share_size_larger_than = parser.check_share_size_larger_than
        self.check_available_size = parser.check_available_size
        self.dd_bs = parser.dd_bs
        self.dd_count = parser.dd_count
        self.remove_file = parser.remove_file
        self.file_exist = parser.file_exist
        self.file_not_exist = parser.file_not_exist

        self.shell_cmds = ShellCommands()
        self.smb_vers = parser.smb_vers
        if not self.share_location or self.check_usb:
            self.ssh_client = SSHClient(parser.ip, parser.ssh_user, parser.ssh_password, parser.ssh_port)
            self.ssh_client.connect()

    def main(self):
        self.create_mount_point()
        if self.check_usb: self.check_usb_by_ssh()
        if not self.share_location: self.detect_usb_share_name()
        try:
            self.shell_cmds.log.info('|- Mount share...')
            self.share_target = '//{}/{}'.format(self.ip, self.share_location)
            mount_success = self.shell_cmds.mount_samba(
                samba_user=self.user, samba_password=self.password, share_location=self.share_target, mount_point=self.mount_point, vers=self.smb_vers)
            if self.verify_mount_fail and not mount_success:
                self.shell_cmds.log.info('Unable to mount share')
                return
            if not mount_success:
                raise RuntimeError("Fail to mount share")
            self.shell_cmds.log.info('Mount share successfully')

            if self.check_share_size: self.check_remote_share_size(self.check_share_size)
            if self.check_share_size_larger_than: self.check_remote_share_size_larger_than(self.check_share_size_larger_than)
            if self.run_write_test: self.write_test()
            if self.dd_bs and self.dd_count: self.write_data_by_dd(self.dd_bs, self.dd_count)
            if self.verify_write_fail: self.write_fail_test()
            if self.verify_write_full_share_fail: self.write_full_share_fail_test()
            if self.check_available_size: self.check_remote_share_available_size(self.check_available_size)
            if self.remove_file: self.clean_file(self.remove_file)
            if self.file_exist: self.remote_file_exist_test(self.file_exist)
            if self.file_not_exist: self.remote_file_not_exist_test(self.file_not_exist)
        finally:
            if self.run_clean_data: self.clean_data()
            self.shell_cmds.log.info('|- Umount share...')
            if not self.shell_cmds.umount_samba(mount_point=self.mount_point):
                self.shell_cmds.log.error('Fail to umoint share')
            self.shell_cmds.log.info('Umount share successfully')

    def create_mount_point(self):
        self.shell_cmds.log.info('|- Preparing moint point...')
        _, _, exitcode = self.shell_cmds.executeCommand(cmd='test -e {0} || mkdir {0}'.format(self.mount_point), exitcode=True, shell=True)
        if exitcode != 0: raise RuntimeError("Fail to create local mount point")

    def check_usb_by_ssh(self):
        self.shell_cmds.log.info('|- Check USB on device...')
        if not self.ssh_client.get_usb_paths(): raise RuntimeError("Fail to find USB mount point on device")
        self.shell_cmds.log.info('Found USB mount on device')

    def detect_usb_share_name(self):
        self.shell_cmds.log.info('|- Detect USB share name...')
        self.share_location = self.ssh_client.get_usb_smb_name()
        if not self.share_location: raise RuntimeError("SMB USB share is not found")
        self.shell_cmds.log.info('Share location: {}'.format(self.share_location))

    def check_remote_share_size(self, size):
        self.shell_cmds.log.info('|- Check share size...')
        output, _, = self.shell_cmds.executeCommand(cmd="df -h | grep {} | awk '{{ print $2 }}'".format(self.share_target), shell=True)
        if output.strip() != size: raise RuntimeError("Share size is not correct")
        self.shell_cmds.log.info('Share size is correct')

    def check_remote_share_size_larger_than(self, size):
        self.shell_cmds.log.info('|- Check share size is larger than {}...'.format(size))
        output, _, = self.shell_cmds.executeCommand(cmd="df -h | grep {} | awk '{{ print $2 }}'".format(self.share_target), shell=True)
        if self.df_value_to_mega(output.strip()) < self.df_value_to_mega(size): raise RuntimeError("Share available size is not correct")
        self.shell_cmds.log.info('Share size is correct')

    def check_remote_share_available_size(self, size):
        self.shell_cmds.log.info('|- Check share available size...')
        output, _, = self.shell_cmds.executeCommand(cmd="df -h | grep {} | awk '{{ print $4 }}'".format(self.share_target), shell=True)
        if output.strip() != size: raise RuntimeError("Share available size is not correct")
        self.shell_cmds.log.info('Share available size is correct')

    def df_value_to_mega(self, df_value):
        # df_value: 100M/100G/100T
        size = float(df_value[:-1])
        unit = df_value[-1]
        if unit == 'G': return size*1024
        if unit == 'T': return size*1024*1024
        return size

    def write_test(self):
        self.shell_cmds.log.info('|- Writing a small data to share...')
        _, _, exitcode = self.shell_cmds.executeCommand(cmd='echo test > {}/testfile'.format(self.mount_point), exitcode=True, shell=True)
        if exitcode != 0: raise RuntimeError("Fail to write test data on share")
        self.shell_cmds.log.info('Write a small data to share successfully')

    def write_data_by_dd(self, bs, count):
        self.shell_cmds.log.info('|- Writing data to share by dd...')
        _, _, exitcode = self.shell_cmds.executeCommand(cmd='dd if=/dev/zero of={}/dd bs={} count={}'.format(self.mount_point, bs, count), exitcode=True, shell=True)
        if exitcode != 0: raise RuntimeError("Fail to write data to share by dd")
        self.shell_cmds.log.info('Write data to share by dd successfully')

    def write_fail_test(self):
        self.shell_cmds.log.info('|- Trying to write share and expect it fail...')
        _, _, exitcode = self.shell_cmds.executeCommand(cmd='echo test > {}/testfile'.format(self.mount_point), exitcode=True, shell=True)
        if exitcode == 0: raise RuntimeError("Successful to write share which does not perform as expected")
        self.shell_cmds.log.info('Fail to write share as expected')

    def write_full_share_fail_test(self):
        self.shell_cmds.log.info('|- Trying to write full share and expect got a empty file...')
        _, _, exitcode = self.shell_cmds.executeCommand(cmd='echo testcontent > {}/full'.format(self.mount_point), exitcode=True, shell=True)
        if exitcode != 0: raise RuntimeError('Seems no permission to write the share')
        output, _ = self.shell_cmds.executeCommand(cmd='test -e {}/full && echo pass'.format(self.mount_point), shell=True)
        if 'pass' not in output: raise RuntimeError('No file exist')
        output, _ = self.shell_cmds.executeCommand(cmd='[ x$(cat {}/full) = x ] && echo pass'.format(self.mount_point), shell=True)
        if 'pass' not in output: raise RuntimeError('File is not empty')
        self.shell_cmds.log.info('Fail to write share as expected')

    def clean_data(self):
        self.shell_cmds.log.info('|- Clean up test data...')
        if self.run_write_test:
            self.clean_file('testfile')

        if self.dd_bs and self.dd_count:
            self.clean_file('dd')

        if self.verify_write_full_share_fail:
            self.clean_file('full')

    def clean_file(self, filename):
        # File deleted or not found are both successful.
        _, _, exitcode = self.shell_cmds.executeCommand(cmd='test -e {0}/{1} && rm {0}/{1} || echo no file found'.format(self.mount_point, filename), exitcode=True, shell=True)
        if exitcode != 0: raise RuntimeError("Fail to clean file: {}".format(filename))
        self.shell_cmds.log.info('Clean up file: {} successfully'.format(filename))

    def remote_file_exist_test(self, filename):
        _, _, exitcode = self.shell_cmds.executeCommand(cmd='test -e {0}/{1}'.format(self.mount_point, filename), exitcode=True, shell=True)
        if exitcode != 0: raise RuntimeError("File: {} not exist".format(filename))
        self.shell_cmds.log.info('File: {} exist'.format(filename))

    def remote_file_not_exist_test(self, filename):
        _, _, exitcode = self.shell_cmds.executeCommand(cmd='test ! -e {0}/{1}'.format(self.mount_point, filename), exitcode=True, shell=True)
        if exitcode != 0: raise RuntimeError("File: {} exist".format(filename))
        self.shell_cmds.log.info('File: {} not exist'.format(filename))


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** SMB share check. ***
        """)

    parser.add_argument('-mp', '--mount-point', help='Mount point', metavar='MP', default='test')
    parser.add_argument('-sl', '--share-location', help='Remote share location', metavar='LF')
    parser.add_argument('-ip', '--ip', help='Device IP', metavar='IP')
    parser.add_argument('-user', '--user', help='The username of SMB', default=None)
    parser.add_argument('-password', '--password', help='The password of SMB', metavar='PWD', default=None)
    parser.add_argument('-su', '--ssh-user', help='The username of SSH server', default="sshd")
    parser.add_argument('-sp', '--ssh-password', help='The password of SSH server', metavar='PWD', default="Test1234")
    parser.add_argument('-spt', '--ssh-port', help='The port of SSH server', type=int, metavar='PORT', default=22)
    parser.add_argument('-sv', '--smb-vers', help='SMB version for mounting share', metavar='VERS', default='3.0')
    parser.add_argument('-cb', '--check-usb', help='Check USB mount via ssh', action='store_true', default=False)
    parser.add_argument('-w', '--write-test', help='Write a small file to SMB share', action='store_true', default=False)
    parser.add_argument('-c', '--clean-data', help='Clean everything generated in share during the test', action='store_true', default=False)
    parser.add_argument('-mf', '--verify-mount-fail', help='Verify mount share is fail', action='store_true', default=False)
    parser.add_argument('-wf', '--verify-write-fail', help='Verify write share is fail', action='store_true', default=False)
    parser.add_argument('-wfsf', '--verify-write-full-share-fail', help='Verify write full share is fail', action='store_true', default=False)
    parser.add_argument('-css', '--check-share-size', help='Check share size. e.g. 100M', default=None)
    parser.add_argument('-csslt', '--check-share-size-larger-than', help='Check share size is larger-than. e.g. 500M', default=None)
    parser.add_argument('-cas', '--check-available-size', help='Check share available szie at end. e.g. 100M or 0', default=None)
    parser.add_argument('-db', '--dd-bs', help='bs value in dd command to write data to remote share', default='1M')
    parser.add_argument('-dc', '--dd-count', help='count value in dd command to write data to remote share. e.g. 100', default=None)
    parser.add_argument('-rf', '--remove-file', help='Remove a file in share', default=None)
    parser.add_argument('-fe', '--file-exist', help='Remote file exist', metavar='FILENAME', default=None)
    parser.add_argument('-fne', '--file-not-exist', help='Remote file not exist', metavar='FILENAME', default=None)

    SMBShareCheck(parser.parse_args()).main()
