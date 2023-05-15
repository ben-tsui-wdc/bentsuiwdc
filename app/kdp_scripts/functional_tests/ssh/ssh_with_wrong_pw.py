# -*- coding: utf-8 -*-

__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"
__compatible__ = 'KDP'

# std modules
import sys
import subprocess
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
# 3rd party
import paramiko


class SshWithWrongPassword(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-3682 - SSH access with wrong password test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3682'
    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.worng_key_url = 'http://10.200.141.26/KDP/ssh_cert/key/pass/id_ecdsa'

    def init(self):
        self.log.info('Download test private key')
        resp = subprocess.Popen('wget {} -O key'.format(self.worng_key_url), shell=True)
        assert resp.returncode != 0, 'Fail to download key'
        subprocess.Popen('chmod 400 key', shell=True)

    def test(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.log.info('Trying to connect {} with the test key'.format(self.env.uut_ip))
            client.connect(self.env.uut_ip, username='root', key_filename='key')
        except paramiko.SSHException as e:
            self.log.info('Got an exception: {}'.format(e))
            self.log.info('Failed to connect as expected')
            return
        raise self.err.TestFailure('Can access SSH with the wrong key')

    def after_test(self):
        subprocess.Popen('rm key', shell=True)

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** SSH access with wrong password test ***
        """)
    parser.add_argument('--worng_key_url', help='URL to get test private key',
        default='http://10.200.141.26/KDP/ssh_cert/key/pass/id_ecdsa')

    test = SshWithWrongPassword(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)