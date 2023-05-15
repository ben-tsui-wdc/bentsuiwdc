# -*- coding: utf-8 -*-
""" Tool for check proxy connection.
"""
# std modules
import logging
import requests
import sys
from argparse import ArgumentParser

# platform modules
from platform_libraries.restAPI import RestAPI

class CheckProxyConnect(object):

    def __init__(self, parser):
        self.cloud_env = parser.cloud_env
        self.uut_ip = parser.uut_ip + ":8001"
        self.command = parser.command
        self.rest_client = RestAPI(
            uut_ip=self.uut_ip, env=self.cloud_env, debug=True, stream_log_level=logging.DEBUG, init_session=False)
 
    def main(self):
        exit_code = {
            'cloud_access_enabled': self.check_cloud_access_enabled,
            'cloud_access_disable': self.check_cloud_access_disable
        }[self.command]()
        self.rest_client.log.info('Exit code: {}'.format(exit_code))
        return exit_code

    def check_cloud_access_enabled(self):
        status = self.get_restsdk_status()
        if status and status.get('minimal') is False and status.get('network', {}).get('proxyConnected') is True:
            return 0
        return 1

    def check_cloud_access_disable(self):
        status = self.get_restsdk_status()
        if status and status.get('minimal') is True and status.get('network', {}).get('proxyConnected') is False:
            return 0
        return 1

    def get_restsdk_status(self):
        resp = self.rest_client.get_device(without_auth=True, fields='proxyConnected,minimal')
        if resp.status_code == 200:
            return resp.json()


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Check filesystems ***
        """)
    parser.add_argument('-env', '--cloud_env', help='Cloud test environment', default='qa1', choices=['dev1', 'qa1', 'prod'])
    parser.add_argument('-ip', '--uut_ip', help='Destination UUT IP address', metavar='IP')
    parser.add_argument('-cmd', '--command', help='Command to run', choices=['cloud_access_enabled', 'cloud_access_disable'])

    sys.exit(CheckProxyConnect(parser.parse_args()).main())
