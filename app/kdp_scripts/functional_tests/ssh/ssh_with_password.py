# -*- coding: utf-8 -*-

__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"
__compatible__ = 'KDP'

# std modules
import sys
import os
# platform modules
from middleware.arguments import KDPInputArgumentParser
from ssh_signature_check_with_cert import SshSignatureCheckWithCert
from platform_libraries.shell_cmds import ShellCommands


class SshAccessWithPassword(SshSignatureCheckWithCert):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-3306 - SSH access with password'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3306'
    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.test_keys_url = 'http://10.200.141.26/KDP/ssh_cert/key/pass' # have id_ecdsa & id_ecdsa.pub
        self.test_password = 'Test1234'
        self.local_key = os.path.dirname(__file__) + "/id_ecdsa"

    def init(self):
        super(SshAccessWithPassword, self).init()
        self.shell_cmds = ShellCommands()
        self.init_usb_path()
        self.backup_key_if_need()

    def test(self):
        self.prepare_test_keys()
        self.reboot()
        assert self.connect_via_ssh(key_filename=self.local_key, password=self.test_password), \
            'Failed to connect to SSH with test password'

    def after_test(self):
        self.log.info('Removing local test key')
        self.shell_cmds.executeCommand('rm {}'.format(self.local_key))
        self.restore_test_keys_by_serial()
        self.reboot()
        self.ssh_client.close_all()
        self.ssh_client.connect()

    def init_usb_path(self):
        self.log.info('Init USB paths')
        self.usb_folder = self.ssh_client.get_usb_path()
        self.backup_folder = "{}/key_backup".format(self.usb_folder)

    def backup_key_if_need(self):
        self.log.info('Backup SSH keys in USB')
        status, _ = self.ssh_client.execute("ls {}".format(self.backup_folder))
        if status != 0:
            self.ssh_client.remount_usb(usb_path=self.usb_folder)
            self.ssh_client.execute("mkdir {}".format(self.backup_folder))
            self.ssh_client.execute("cp {}/id_ecdsa* {}/".format(self.usb_folder, self.backup_folder))

    def prepare_test_keys(self):
        self.log.info('Preparing test keys in USB')
        self.ssh_client.remount_usb(usb_path=self.usb_folder)
        self.ssh_client.execute("rm {}/id_ecdsa* ".format(self.usb_folder))
        self.ssh_client.execute("wget {}/id_ecdsa -P {} ".format(self.test_keys_url, self.usb_folder))
        self.ssh_client.execute("cat {}/id_ecdsa".format(self.usb_folder))
        self.ssh_client.execute("wget {}/id_ecdsa.pub -P {} ".format(self.test_keys_url, self.usb_folder))
        self.ssh_client.execute("cat {}/id_ecdsa.pub".format(self.usb_folder))
        self.ssh_client.scp_connect()
        self.ssh_client.scp_download(remotepath="{}/id_ecdsa".format(self.usb_folder), localpath=self.local_key)
        self.shell_cmds.executeCommand('chmod 400 {}'.format(self.local_key))

    def restore_test_keys_by_serial(self):
        self.log.info('Restoring test keys in USB')
        self.serial_client.remount_usb(usb_path=self.usb_folder)
        self.serial_client.serial_cmd("rm {}/id_ecdsa* ".format(self.usb_folder))
        self.serial_client.serial_cmd("cp {}/* {} ".format(self.backup_folder, self.usb_folder))
        assert self.serial_client.get_exit_code() == 0, 'Failed to recover keys in USB'


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** SSH access with private key has password required test ***
        """)
    parser.add_argument('--test_keys_url', help='URL to get test keys',
        default='http://10.200.141.26/KDP/ssh_cert/key/pass')
    parser.add_argument('--test_password', help='Password of test key', default='Test1234')

    test = SshAccessWithPassword(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
