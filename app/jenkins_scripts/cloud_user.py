# -*- coding: utf-8 -*-
""" Tool for create/delete cloud user.
"""
# std modules
import logging
from argparse import ArgumentParser

# platform modules
from platform_libraries.restAPI import RestAPI

class CloudUser(object):

    def __init__(self, parser):
        self.cloud_env = parser.cloud_env
        self.username = parser.username
        self.password = parser.password
        self.first_name = parser.first_name
        self.last_name = parser.last_name
        self.command = parser.command
        self.rest_client = RestAPI(
            uut_ip='', env=self.cloud_env, username=None, password=None, debug=True, 
            stream_log_level=logging.DEBUG, init_session=False)
        self.rest_client.init_variables()
        self.rest_client.environment.update_service_urls()
 
    def main(self):
        if self.command in ['DELETE', 'DELETE-CREATE']:
            self.rest_client.delete_user(username=self.username, password=self.password)
        if self.command in ['CREATE', 'DELETE-CREATE']:
            self.rest_client.create_user(self.username, self.password, first_name=self.first_name, last_name=self.last_name)


if __name__ == '__main__':
    parser = ArgumentParser("""\
        *** Detach user ***
        """)
    parser.add_argument('-env', '--cloud_env', help='Cloud test environment', default='qa1', choices=['dev1', 'qa1', 'prod'])
    parser.add_argument('-u', '--username', help='User account', metavar='NAME')
    parser.add_argument('-p', '--password', help='User password', metavar='PW')
    parser.add_argument('-fn', '--first_name', help='User password', metavar='FN', default='FN')
    parser.add_argument('-ln', '--last_name', help='User password', metavar='LN', default='LN')
    parser.add_argument('-cmd', '--command', help='Command to execute', choices=['DELETE', 'CREATE', 'DELETE-CREATE'])

    CloudUser(parser.parse_args()).main()
