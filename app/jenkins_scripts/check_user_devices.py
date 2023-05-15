# -*- coding: utf-8 -*-
""" Tool for cehcking user's device info.
"""
# std modules
import logging
import sys
from argparse import ArgumentParser

# platform modules
from platform_libraries.restAPI import RestAPI
from platform_libraries.pyutils import retry


class CheckUserDevices(object):

    def __init__(self, parser):
        self.cloud_env = parser.cloud_env
        self.mac = parser.mac
        self.is_owner = parser.is_owner
        self.is_detach = parser.is_detach
        self.rest_client = RestAPI(
            uut_ip=None, env=self.cloud_env, username=parser.username, password=parser.password, debug=True, 
            stream_log_level=logging.DEBUG, init_session=False)
        self.rest_client.update_device_id()
 
    def main(self):
        devices = self.rest_client.get_devices_info_per_specific_user()
        self.rest_client.log.info("User's devices: {}".format(devices))
        if self.mac:
            if self.is_owner:
                for device in devices:
                    if device['mac'] == self.mac.lower():
                        if device['ownerAccess'] == True and device['attachedStatus'] == 'APPROVED':
                            self.rest_client.log.info("User is owner")
                            return
                        raise AssertionError('Attchment status is not correct')
                raise AssertionError('The device is not attached')
            if self.is_detach:
                for device in devices:
                    if device['mac'] == self.mac.lower():
                        raise AssertionError('User is still attached')
                self.rest_client.log.info("User is detached")


if __name__ == '__main__':
    parser = ArgumentParser("""\
        *** Check user's devices information ***
        """)
    parser.add_argument('-env', '--cloud_env', help='Cloud test environment', default='qa1', choices=['dev1', 'qa1', 'prod'])
    parser.add_argument('-u', '--username', help='User account', metavar='NAME')
    parser.add_argument('-p', '--password', help='User password', metavar='PW')
    parser.add_argument('-m', '--mac', help='MAC of target device', metavar='MAC', default=None)
    parser.add_argument('-io', '--is-owner', help='Verify user is owner of the device', action='store_true', default=False)
    parser.add_argument('-id', '--is-detach', help='Verify user is detached from the device', action='store_true', default=False)

    CheckUserDevices(parser.parse_args()).main()
