# -*- coding: utf-8 -*-

# std modules
import logging
import requests
import sys
from argparse import ArgumentParser

# platform modules
from platform_libraries.restAPI import RestAPI


class CheckFilesystem(object):

    def __init__(self, parser):
        self.cloud_env = parser.cloud_env
        self.uut_ip = parser.uut_ip + ":8001"
        self.username = parser.username
        self.passwrod = parser.passwrod
        self.folder_name = parser.folder_name
        self.rest_client = RestAPI(
            uut_ip=self.uut_ip, env=self.cloud_env, username=self.username, password=self.passwrod,
            debug=True, stream_log_level=logging.DEBUG, init_session=False)
        self.rest_client.update_device_id()
        self.rest_client.get_id_token()
        self.folder_id = None
        self.root_id = None
 
    def main(self):
        self.check_filesystem()
        self.check_file_perm()

    def check_filesystem(self):
        for f in self.rest_client.get_filesystem()['filesystems']:
            if self.folder_name in f['name']:
                self.folder_id = f['id']
                self.root_id = f['rootID']
        if not self.folder_id:
            raise AssertionError('filesystem not found')
        self.rest_client.log.info('filesystem found')

    def check_file_perm(self):
        if not 'FileAll' in self.rest_client.get_file_perms(file_id=self.root_id)['filePerms'][0]['value']:
            raise AssertionError('file perms != FileAll')
        self.rest_client.log.info('file perms is correct')


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Check filesystems ***
        ./run.sh jenkins_scripts/godzilla/check_filesystem.py -env qa1 -ip 10.200.141.101 -u wdcautotw+qawdc.gza15@gmail.com -p Auto1234 -fn Test123
        """)
    parser.add_argument('-env', '--cloud_env', help='Cloud test environment', default='qa1', choices=['dev1', 'qa1', 'prod'])
    parser.add_argument('-ip', '--uut_ip', help='Destination UUT IP address', metavar='IP')
    parser.add_argument('-u', '--username', help='Test user name', metavar='NAME')
    parser.add_argument('-p', '--passwrod', help='Test user password', metavar='PW')
    parser.add_argument('-fn', '--folder_name', help='Folder name to verify', metavar='NAME')

    CheckFilesystem(parser.parse_args()).main()
