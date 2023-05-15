# -*- coding: utf-8 -*-
""" Tool for upload files to device
"""
# std modules
import logging
import requests
import sys
import os
from argparse import ArgumentParser

# platform modules
from platform_libraries.common_utils import execute_local_cmd
from platform_libraries.restAPI import RestAPI

class UploadFiles(object):

    def __init__(self, parser):
        self.cloud_env = parser.cloud_env
        self.uut_ip = parser.uut_ip + ":8001" if parser.gza else parser.uut_ip
        self.username = parser.username
        self.password = parser.password
        self.video_file_url = parser.video_file_url
        self.local_path = parser.local_path
        self.rest_client = RestAPI(
            username=self.username, password=self.password,
            uut_ip=self.uut_ip, env=self.cloud_env, debug=False, init_session=False)
        self.rest_client.update_device_id()

    def main(self):
        if self.video_file_url:
            self.rest_client.log.info("Download files...")
            if not self.video_file_url.endswith('/') and '.' not in self.video_file_url.split('/').pop():
                self.video_file_url += '/'
            if not os.path.exists(self.local_path):
                os.mkdir(self.local_path)
            execute_local_cmd('wget -r -nc -np -nd -R "index.html*" {} -P {}'.format(self.video_file_url, self.local_path),
                              consoleOutput=True, timeout=60*30)
        self.rest_client.log.info("Upload files to device...")
        self.rest_client.recursive_upload(path=self.local_path)


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Check filesystems ***
        """)
    parser.add_argument('-gza', '--gza', help='For GZA device', action='store_true', default=False)
    parser.add_argument('-env', '--cloud_env', help='Cloud test environment', default='qa1', choices=['dev1', 'qa1', 'prod'])
    parser.add_argument('-ip', '--uut_ip', help='Destination UUT IP address', metavar='IP')
    parser.add_argument('-u', '--username', help='Owner account', metavar='USER', default='wdcautotw+qawdc.kdp@gmail.com')
    parser.add_argument('-p', '--password', help='Owner password', metavar='PW', default='Password1234#')
    parser.add_argument('-vfu', '--video_file_url', help='Source file URL', metavar='URL')
    parser.add_argument('-lp', '--local_path', help='Local path to uplaod', metavar='PATH', default='local')

    sys.exit(UploadFiles(parser.parse_args()).main())
