# -*- coding: utf-8 -*-
""" Nas Admin API libraries
"""
___author___ = 'Ben Tsui <ben.tsui@wdc.com>'

# std modules
import json
import time
import socket
import sys
from datetime import datetime
from pprint import pformat
from base64 import b64encode
# 3rd party modules
import requests
# platform modules
import common_utils
from platform_libraries.pyutils import retry
from constants import GlobalConfigService as GCS
from platform_libraries.cloud_api import HTTPRequester


class NasAdminAPI(HTTPRequester):
    """ This library is deprecated since most of the APIs can only be sent locally (127.0.0.1),
        please use the methods in ssh_client library
    """
    def __init__(self, uut_ip=None, username="admin", password="adminadmin", log_inst=None):
        self.log = log_inst if log_inst else common_utils.create_logger()
        self.base_url = 'http://{}'.format(uut_ip)
        self.username = username
        self.password = b64encode(password)
        self.token = None
        self.token_expire_time = None
        super(NasAdminAPI, self).__init__(log_inst=self.log)

    def set_base_url(self, url):
        self.base_url = url

    def get_token(self):
        """
            Get nas admin token
            :return: Admin token in String format.
        """

        """ Try to get tokens every time since the expire time is only 5 mins
        if self.token:
            return self.token
        """
        self.log.debug('Getting new nasAdmin token...')
        response = self.json_request(
            method='POST',
            url='{}/nas/v1/auth'.format(self.base_url),
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                "username": self.username,
                "password": self.password
            })
        )

        if response.status_code == 200:
            self.log.debug('Response: {}'.format(response.json()))
            self.token = None
            for c in response.cookies:
                if c.name == "Authorization" or c.name == "fe97238703cba":  # add "fe97238703cba" due to GZA-6651
                    self.token = c.value
                    self.log.debug('nasAdmin token: {}'.format(self.token))
                    break
            if self.token:
                self.log.debug('Get nasAdmin token successfully')
            else:
                self.error('Failed to get nasAdmin token from cookie', response.cookies)
            self.token_expire_time = response.json()['expires']
            return self.token
        else:
            self.error('Failed to get nasAdmin token', response)

    def get_nas_admin_info(self):
        self.log.info("Getting the nasAdmin status")
        response = self.json_request(
            method='GET',
            url='{}/nas/v1/locale'.format(self.base_url),
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            self.log.info('Get nasAdmin info successfully')
            self.log.info('nasAdmin info: {}'.format(response.json()))
            return response.json()
        else:
            self.error('Failed to get nasAdmin info', response)

    def ota_get_firmware_update_status(self):
        self.log.debug("Get the OTA firmware update status")
        self.get_token()
        response = self.json_request(
            method='GET',
            url='{}:8002/ota/v1/firmware'.format(self.base_url),
            headers={'Content-Type': 'application/json',
                     'Authorization': 'Bearer {}'.format(self.token)}
        )
        if response.status_code == 200:
            self.log.debug('Get the OTA firmware update status successfully')
            return response.json()
        else:
            self.error('Failed to get the OTA firmware update status!', response)

    def ota_change_auto_update(self, mode="enabled"):
        self.log.debug("Changing the ota auto update mode to: {}".format(mode))
        result = self.ota_get_firmware_update_status()
        if result.get('updatePolicy').get('mode') == mode:
            self.log.info("The auto update mode is already {}".format(mode))
        else:
            self.log.info("Changing the auto update mode")
            self.get_token()
            response = self.json_request(
                method='PUT',
                url='{}:8002/ota/v1/firmware'.format(self.base_url),
                headers={'Content-Type': 'application/json',
                         'Authorization': 'Bearer {}'.format(self.token)},
                data=json.dumps({"updatePolicy":{"mode": "{}".format(mode)}})
            )
            if response.status_code == 204:
                self.log.info('Change the auto update mode successfully')
            else:
                self.error('Failed to change the auto update mode!', response)

            result = self.ota_get_firmware_update_status()
            self.log.warning(result)

    def ota_check_for_firmware_update_now(self):
        self.get_token()
        self.log.info("Run the check for firmware update so that we can get the ota status from cloud")
        response = self.json_request(
            method='POST',
            url='{}:8002/ota/v1/firmware/check'.format(self.base_url),
            headers={'Content-Type': 'application/json',
                     'Authorization': 'Bearer {}'.format(self.token)}
        )
        if response.status_code == 204:
            self.log.info('Check the firmware update successfully')
        else:
            self.error('Failed to run the ota check the firmware update!', response)

    def ota_update_firmware_now(self):
        self.get_token()
        self.log.info("Trigger the OTA immediately")
        response = self.json_request(
            method='POST',
            url='{}:8002/ota/v1/firmware/update'.format(self.base_url),
            headers={'Content-Type': 'application/json',
                     'Authorization': 'Bearer {}'.format(self.token)}
        )
        if response.status_code == 204:
            self.log.info('Trigger the OTA successfully')
        else:
            self.error('Failed to trigger the OTA!', response)


if __name__ == '__main__':
    nasadmin_obj = NasAdminAPI("10.92.235.193")
    nasadmin_obj.get_token()
