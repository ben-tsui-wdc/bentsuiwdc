# -*- coding: utf-8 -*-

__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"
__compatible__ = 'KDP'

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from ssh_signature_check_with_cert import SshSignatureCheckWithCert


class SshSignatureCheckWithEnableRoot(SshSignatureCheckWithCert):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-3309 - SSH signature check with enable_root test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3309'

    def test(self):
        self.delete_enable_root()
        # Create new console password due to https://csbu.atlassian.net/browse/KDP-5278?focusedCommentId=338064
        self.reboot(change_pw=True)
        assert not self.is_sshd_running(), 'sshd is still running'
        self.touch_enable_root()
        self.reboot(use_pre_pw=True)
        assert self.is_sshd_running(), 'sshd is not running'
        self.connect_via_ssh(key_filename=self.ssh_client.key_filename)

    def after_test(self):
        # Trt to recover testing environment of device
        if not self.is_sshd_running():
            self.touch_enable_root()
            self.reboot()
        self.ssh_client.close_all()
        self.ssh_client.connect()

    def enable_root_exist(self):
        self.log.info('Checking enable_root exist')
        return self.serial_client.file_exists('/wd_config/enable_root')

    def touch_enable_root(self):
        self.log.info('Touching enable_root')
        self.serial_client.serial_cmd("mount -o rw,remount /wd_config; touch /wd_config/enable_root")
        if not self.enable_root_exist():
            raise self.err.TestFailure('Failed to touch enable_root')

    def delete_enable_root(self):
        self.log.info('Deleting enable_root')
        self.serial_client.serial_cmd("mount -o rw,remount /wd_config; rm /wd_config/enable_root")
        if self.enable_root_exist():
            raise self.err.TestFailure('Failed to delete enable_root')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** SSH signature check with enable_root test ***
        """)

    test = SshSignatureCheckWithEnableRoot(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
