# -*- coding: utf-8 -*-
""" Tool for detach user.
"""
# std modules
import logging
import sys
from argparse import ArgumentParser

# platform modules
from platform_libraries.ssh_client import SSHClient
from platform_libraries.restAPI import RestAPI
from platform_libraries.pyutils import retry


class DetachOwnerUser(object):

    def __init__(self, parser):
        self.cloud_env = parser.cloud_env
        self.uut_ip = parser.uut_ip + ":8001"
        self.rest_client = RestAPI(
            uut_ip=self.uut_ip, env=self.cloud_env, username=parser.username, password=parser.password, debug=True, 
            stream_log_level=logging.DEBUG, init_session=False)
        self.rest_client.update_device_id()
        self.ssh_client = SSHClient(parser.uut_ip, parser.ssh_user, parser.ssh_password, parser.ssh_port)
        self.ssh_client.connect()
 
    def main(self):
        try:
            users, _ = self.rest_client.get_users()
            if not users:
                self.rest_client.log.info('No cloud user in device')
                return 0
            if self.rest_client.detach_user_from_device() not in [200, 409]:
                raise RuntimeError('Fail to detach user')
            self.ssh_client.remove_cloud_user_from_local_user(user='admin')
            self.ssh_client.enable_restsdk_minimal_mode()
        except Exception, e:
            self.rest_client.log.error(e)
            return 1

if __name__ == '__main__':
    parser = ArgumentParser("""\
        *** Detach user ***
        """)
    parser.add_argument('-env', '--cloud_env', help='Cloud test environment', default='qa1', choices=['dev1', 'qa1', 'prod'])
    parser.add_argument('-ip', '--uut_ip', help='Destination UUT IP address', metavar='IP')
    parser.add_argument('-u', '--username', help='User account', metavar='NAME')
    parser.add_argument('-p', '--password', help='User password', metavar='PW')
    parser.add_argument('-ssh_user', '--ssh_user', help='The username of SSH server', default="sshd")
    parser.add_argument('-ssh_password', '--ssh_password', help='The password of SSH server', metavar='PWD', default="Test1234")
    parser.add_argument('-ssh_port', '--ssh_port', help='The port of SSH server', type=int, metavar='PORT', default=22)

    sys.exit(DetachOwnerUser(parser.parse_args()).main())
