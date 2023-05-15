# -*- coding: utf-8 -*-
""" Tool for getting logcat logs from device.
"""
# std modules
import logging
import requests
from argparse import ArgumentParser

# platform modules
from platform_libraries.restAPI import RestAPI

class CheckLocalDevice(object):

    def __init__(self, parser):
        self.username = parser.username
        self.password = parser.password
        self.serial_number = parser.serial_number
        self.rest_client = RestAPI(env='qa1', username=self.username, password=self.password, stream_log_level=logging.DEBUG, init_session=False)
        self.rest_client.update_device_id()

    def main(self):
        res_json = self.rest_client.get_localdevice_from_cloud()
        if not self.serial_number:
            return

        self.rest_client.log.info('Input Serial Number: '+self.serial_number)
        if '-' in self.serial_number:
            self.serial_number = self.serial_number.replace('-', '')
            self.rest_client.log.info('Update Serial Number to: '+self.serial_number)

        for device in res_json['data']:
            if 'serialNumber' in device and self.serial_number in device['serialNumber']:
                self.rest_client.log.info('Find device in list.')
                if device['network'].get('internalURL'):
                    self.rest_client.log.info('Ping device via internalURL...')
                    resp = self.rest_client.send_request(method='GET', url=device['network']['internalURL']+'/sdk/v1/device', set_corid=False)
                    if resp.status_code != 200:
                        self.rest_client.log.error('Fail to ping device via internalURL!!')
                if device['network'].get('localIpAddress'):
                    self.rest_client.log.info('Ping device via localIpAddress...')
                    resp = self.rest_client.send_request(method='GET', url='http://'+device['network']['localIpAddress']+'/sdk/v1/device', set_corid=False)
                    if resp.status_code != 200:
                        self.rest_client.log.error('Fail to ping device via localIpAddress!!')

if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Check local device ***
        """)

    parser.add_argument('-u', '--username', help='Test user name', metavar='USERNAME')
    parser.add_argument('-p', '--password', help='Test user password', metavar='PASSWROD')
    parser.add_argument('-sn', '--serial_number', help='Serial number of device to ping it', metavar='SN', default=None)

    test = CheckLocalDevice(parser.parse_args())
    test.main()
