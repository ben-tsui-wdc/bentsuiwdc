# -*- coding: utf-8 -*-

__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"
__compatible__ = 'KDP'

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
# 3rd party
import paramiko


class SshSignatureCheckWithCert(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-3308 - SSH signature check with sshd.cert test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3308'
    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        if not self.is_cert_file_in_usb() or not self.is_key_file_in_usb():
            raise self.err.TestFailure('Please prepare SSH file in USB')

    def test(self):
        self.reboot()
        assert self.is_sshd_running(), 'sshd is not running'
        self.connect_via_ssh(key_filename=self.ssh_client.key_filename)

    def after_test(self):
        self.ssh_client.close_all()
        self.ssh_client.connect()

    def connect_via_ssh(self, key_filename, password=None):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.log.info('Trying to connect {} with {}'.format(self.env.uut_ip, key_filename))
            client.connect(self.env.uut_ip, username='root', password=password, key_filename=key_filename)
            self.log.info('Connect successfully, now close it')
            client.close()
            return True
        except paramiko.SSHException as e:
            self.log.info('Got an exception: {}'.format(e))
            return False

    def reboot(self, change_pw=False, use_pre_pw=False, timeout=60*20):
        self.log.info('Use serial command to reboot device.')
        if change_pw:
            mac = self.uut.get('mac_address').upper()
            serial = self.uut.get('serial_number')
            self.serial_client.generate_password(mac=mac, serial=serial)
        if use_pre_pw:
            self.serial_client.use_pre_password()
        self.serial_client.reboot_device_kdp()
        self.serial_client.wait_for_boot_complete_kdp(timeout=timeout)
        self.env.check_ip_change_by_console()

    def is_cert_file_in_usb(self):
        self.log.info('Checking sshd.cert in USB')
        return self.serial_client.file_exists('/mnt/USB/*/sshd.cert')

    def is_key_file_in_usb(self):
        self.log.info('Checking id_ecdsa.pub in USB')
        return self.serial_client.file_exists('/mnt/USB/*/id_ecdsa.pub')

    def is_sshd_running(self):
        self.log.info('Checking sshd is running')
        return self.serial_client.process_exists('sshd')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** SSH signature check with sshd.cert test ***
        """)

    test = SshSignatureCheckWithCert(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
