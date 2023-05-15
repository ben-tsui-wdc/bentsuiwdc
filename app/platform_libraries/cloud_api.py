# -*- coding: utf-8 -*-
""" Cloud API libraries
"""

___author___ = 'Ben Tsui <ben.tsui@wdc.com>'

# std modules
import json
import time
import sys
import urllib
from datetime import datetime
# 3rd party modules
import requests
from packaging.version import LegacyVersion
# platform modules
import common_utils
from constants import ClientID, ClientSecret
from platform_libraries.cloud_environment import CloudEnvironment, get_service_urls
from platform_libraries.http_client import HTTPRequester
from platform_libraries.pyutils import log_request, log_response, retry
from constants import GlobalConfigService as GCS


@common_utils.logger()
class CloudAPI(HTTPRequester):

    def __init__(self, env='qa1', log_inst=None):

        if log_inst: self.log = log_inst
        self.base_url = 'https://wdc.auth0.com'
        self.env = env
        self.admin_token = None
        self.admin_token_time = None
        self.token_expire_time = None
        self.environment = CloudEnvironment(env, http_requester=self)

        super(CloudAPI, self).__init__(log_inst=self.log)
        self.environment.update_service_urls()
        self.ota_bucket_url = self.environment.get('service.ota.url')
        self.device_service = self.environment.get('service.device.url')
        self.appcatalog_url = self.environment.get('service.appcatalog.url')
        self.auth_url = self.environment.get('service.auth.url')
        self.m2m_url = self.environment.get('service.m2m.url')

    def set_base_url(self, url):
        self.base_url = url

    def get_admin_token(self):
        """
            Get cloud admin token for OTA use

            :return: Admin token in String format.
        """
        if self.admin_token:
            time_passed = (datetime.now() - self.admin_token_time).seconds
            if time_passed < (self.token_expire_time - 3600):
                self.log.debug('Use existed admin token, it will be expired in {} secs'.
                               format(self.token_expire_time - time_passed))
                return self.admin_token
            else:
                self.log.info('Token will be expired in an hour, renew it.')

        self.log.debug('Getting new admin token...')
        response = self.json_request(
            method='POST',
            url='{}/v9/m2m/token'.format(self.m2m_url),
            data=json.dumps({
                'clientId': self.environment.get_client_id(),
                'secret': self.environment.get_client_secret()
            })
        )

        if response.status_code == 200:
            self.log.debug('Get admin token successfully')
            self.admin_token_time = datetime.now()
            self.admin_token = response.json()['token']
            self.log.debug('Set expire time to 36000 due to cannot get expires_in field by using m2m authrouter')
            self.token_expire_time = 36000

            self.log.debug('Admin token: {}'.format(self.admin_token))
            self.log.debug('Admin token expire time: {}'.format(self.token_expire_time))
            return self.admin_token
        else:
            self.error('Failed to get admin token', response)

    def get_ota_buckets_info(self, to_version=None, product='monarch'):
        """
            Get all buckets info.
            If to_version and product is not specified, all buckets info will be returned.

            :param to_version: The device will be OTA to which version
            :param product: The product is monarch/pelican
            :return: buckets info in json format
        """
        admin_token = self.get_admin_token()
        url = '{}/ota/v1/bucket/null'.format(self.ota_bucket_url)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(admin_token)}

        result = requests.get(url, headers=headers)
        if result.status_code != 200:
            self.error('Get OTA buckets failed, status code:{0}, error log:{1}'.
                       format(result.status_code, result.content))
        else:
            if to_version:
                for bucket in result.json()['data']['Items']:
                    if bucket['to_version'] == to_version and bucket['device_type'] == product:
                        self.log.debug('Bucket info: {}'.format(bucket))
                        return bucket
                self.log.warning("Cannot find specified bucket!")
            else:
                self.log.info("No to_version specified, return all the buckets info")
                return result.json()

    def check_device_in_ota_bucket(self, bucket_id, device_id, adb=None):
        """
            Add specified device in ota bucket
            :param bucket_id: The id of the ota bucket
            :param device_id: The id of device that is in the bucket or not
            :param adb: adb object to restart otaclient during retries
            :return Boolean
        """
        admin_token = self.get_admin_token()
        url = '{}/ota/v1/device/deviceId/{}'.format(self.ota_bucket_url, device_id)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(admin_token)}

        retry = 60
        while retry >= 0:

            result = requests.get(url, headers=headers)
            if result.status_code != 200:
                self.error('Check device in OTA bucket failed, status code:{0}, error log:{1}'.
                           format(result.status_code, result.content))
            else:
                self.log.debug(result.json())
                bucket_data = result.json()['data']
                if not bucket_data:
                    if retry == 0:
                        self.error("Reaching maxinum retries, failed to get check device in ota bucket!")

                    if adb:
                        adb.executeShellCommand('stop otaclient')
                        time.sleep(10)
                        adb.executeShellCommand('start otaclient')

                    self.log.warning("Failed to get bucket info, retry after 60 secs, remaining {} retries".format(retry))

                    time.sleep(60)
                    retry -= 1

                    if adb:
                        # To avoid device is OTA to default bucket
                        adb.executeShellCommand('stop otaclient')
                else:
                    """ 2018/10/22 Seems like it's not a necessary step beacuse otaclient will be started in test cases
                    # If there are any retries we need to start ota client again
                    if adb and retry != 60:
                        adb.executeShellCommand('start otaclient')
                    """
                    get_bucket_id = bucket_data['bucketId']
                    if get_bucket_id == "DEVICE_VERSION":
                        # If bucket id is "DEVICE_VERSION", that means device is even not in the default bucket,
                        # and beta users will not able to be ota forever

                        # self.error("Device is not in the default bucket! Raise exception due to KAM200-7876!")
                        self.log.warning("{}".format(bucket_data))
                        self.log.warning("The bucket id is 'DEVICE_VERSION', this device is not in the default bucket!")
                    if get_bucket_id == bucket_id:
                        self.log.info('Device is in this bucket')
                        return True
                    else:
                        self.log.warning('Device is not in this bucket: {}'.format(bucket_id))
                        return False

    def add_device_in_ota_bucket(self, bucket_id, device_id=[]):
        """
            Add specified device in ota bucket
            :param bucket_id: The id of the ota bucket
            :param device_id: The id list of devices that will be added in bucket
        """
        admin_token = self.get_admin_token()
        url = '{}/ota/v1/bucket/{}'.format(self.ota_bucket_url, bucket_id)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(admin_token)}
        data = {'requestType': 'ADD_DEVICES',
                'deviceList': device_id}
        self.log.info("url:{}".format(url))
        result = requests.post(url, headers=headers, data=json.dumps(data))
        if result.status_code != 200:
            self.error('Add device in OTA buckets failed, status code:{0}, error log:{1}'.
                       format(result.status_code, result.content))
        else:
            self.log.info('Device is added in ota bucket successfully')
            self.log.info('Response: {}'.format(result.content))

    def register_device_in_cloud(self, device_type, device_id, fw_version):
        """
            Register device in the cloud
            :param device_type: monarch or pelican
            :param device_id: The id list of devices that will be added in bucket
            :param fw_version: The current fwversion
        """
        self.log.info('Registering device in the cloud')
        admin_token = self.get_admin_token()
        url = '{}/ota/v1/version/deviceId/{}'.format(self.ota_bucket_url, device_id)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(admin_token)}
        data = {'currVersion': fw_version,
                'deviceType': device_type}
        result = requests.post(url, headers=headers, data=json.dumps(data))
        if result.status_code != 200:
            self.error('Register device in cloud failed, status code:{0}, error log:{1}'.
                       format(result.status_code, result.content))
        else:
            self.log.info('Register device in cloud successfully')

    def get_device_info_with_mac(self, mac_address):
        """
            Get device info with mac address.
        :return:
        "data": {
            "deviceId": "839a5871-146b-4563-9e62-c146d5d224ba",
            "modelId": "0",
            "name": "vance's ibi",
            "mac": "00:00:c0:0b:76:3f",
            "type": "yodaplus",
            "cloudConnected": true,
            "createdOn": "2018-10-09T03:37:30",
            "configuration": {
                "wisb": "global_default"
            },
            "firmware": {
                "wiri": "5.1.0-327"
            },
            "network": {
                "localIpAddress": "192.168.30.23",
                "externalIpAddress": "199.255.47.5",
                "portForwardPort": -1,
                "tunnelId": "TN4yTPxRwEnEqLSgQ2TXDniNZkg",
                "internalDNSName": "device-local-839a5871-146b-4563-9e62-c146d5d224ba.wdtest8.com",
                "internalURL": "http://192.168.30.23",
                "portForwardDomain": "https://device-839a5871-146b-4563-9e62-c146d5d224ba.wdtest8.com",
                "proxyURL": "https://i-0b80db0c7181947bf.ice.wdtest2.com:443/839a5871-146b-4563-9e62-c146d5d224ba",
                "lastSSID": "V5G"
            },
            "lang": "en",
            "serialNumber": "WX71A38216E0"
                }
        """
        self.log.debug('Getting Device Info with MAC address')
        admin_token = self.get_admin_token()
        url = '{0}/device/v1/mac/{1}'.format(self.device_service, mac_address)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(admin_token)}
        result = requests.get(url, headers=headers)
        if result.status_code == 200:
            self.log.info('Get device info successfully')
            return result.json().get('data')
        else:
            self.error('Failed to get device info', result)

    def get_device_info_with_device_id(self, device_id):
        """
            Get device info with device_id.
        :return:
        "data": {
            "deviceId": "b8131235-ff77-4550-85a9-808fca4cd498",
            "name": "Vance's Desktop ibi 45X7",
            "mac": "00:00:c0:0c:45:07",
            "type": "yodaplus",
            "cloudConnected": true,
            "createdOn": "2020-06-01T07:50:30",
            "firmware": {
                "wiri": "7.9.0-128"
            },
            "network": {
                "localIpAddress": "10.200.140.120",
                "externalIpAddress": "129.253.182.11",
                "localHttpPort": 80,
                "localHttpsPort": 443,
                "portForwardPort": -1,
                "tunnelId": "GAkBbdjeQuSQoyJaSBMy",
                "internalDNSName": "device-local-b8131235-ff77-4550-85a9-808fca4cd498.wdtest8.com:443",
                "internalURL": "http://10.200.140.120:80",
                "portForwardDomain": "https://device-b8131235-ff77-4550-85a9-808fca4cd498.wdtest8.com",
                "proxyURL": "https://qa1-1912f6ae7bd8bd7.ice.wdtest2.com/b8131235-ff77-4550-85a9-808fca4cd498",
                "externalURI": "https://qa1-1912f6ae7bd8bd7.ice.wdtest2.com/b8131235-ff77-4550-85a9-808fca4cd498"
            },
            "lastHDStoragePercent": 97,
            "lang": "en",
            "serialNumber": "WX11AA8545X7",
            "apiVersion": "2.7.0-689",
            "region": "US"
        }
        """
        self.log.debug('Getting Device Info with device ID')
        admin_token = self.get_admin_token()
        url = '{0}/device/v1/device/{1}'.format(self.device_service, device_id)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(admin_token)}
        result = requests.get(url, headers=headers)
        if result.status_code == 200:
            self.log.info('Get device info successfully')
            return result.json().get('data')
        else:
            self.error('Failed to get device info', result)

    def get_device_id_from_proxy_portforward_url_connection(self, url):
        admin_token = self.get_admin_token()
        url = '{0}/sdk/v1/device?fields=id'.format(url)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(admin_token)}
        result = requests.get(url, headers=headers)
        if result.status_code ==200:
            self.log.info('Success to get device id from proxy/portforward url connection')
            return result.json().get('id')
        else:
            self.error('Failed to get device id from proxy/portforward url connection', result)

    def get_latest_app_version_info(self, appId, osFamily='KAMINO'):
        """
            Find latest version of Application
            /v1/app/{appId}/{osFamily}/LATEST
        """
        self.log.debug('Getting {} latest app version'.format(appId))
        admin_token = self.get_admin_token()
        # Send request
        response = self.json_request(
            method='GET',
            url='{0}/appcatalog/v1/app/{1}/{2}/LATEST'.format(self.appcatalog_url, appId, osFamily),
            headers={'Authorization': 'Bearer {}'.format(admin_token)}
        )
        if response.status_code != 200:
            self.error('Get latest app version failed', response)
        self.log.debug('Get latest app version successfully')
        return response.json().get('data')

    def update_create_loadtestapp_app_record(self, appId='com.wdc.mycloud.loadtest.app1', osFamily='KAMINO', version='1.0.0'):
        """
            Update Loadtest App record on cloud side. 
        """
        self.log.debug('Updating/Creating App({}) record on cloud side ...'.format(appId))
        admin_token = self.get_admin_token()
        # Sned request
        response = self.json_request(
            method='POST',
            url='{0}/appcatalog/v1/app'.format(self.appcatalog_url),
            headers={'Authorization': 'Bearer {}'.format(admin_token)},
            data=json.dumps({
                "appId": appId,
                "version": version,
                "iconUrl": "https://s3-us-west-2.amazonaws.com/wd-portal-apps/dev1/com.wdc.branded.security/icon/security.png",
                "iconHoverUrl": "https://s3-us-west-2.amazonaws.com/wd-portal-apps/dev1/com.wdc.branded.security/iconHover/security_hover.png",
                "osFamily": osFamily,
                "companyName": "SanDisk",
                "companyWebsiteUrl": "https://ibi.sandisk.com/",
                "supportEmail": "https://ibisupport.sandisk.com/app/answers/detail/a_id/22033",
                "supportedDeviceTypes": ["monarch", "pelican", "yodaplus"],
                "minimumOSVersion": "4.0.0",
                "maximumOSVersion": "9.9.9",
                "supportedCountries" : ["US", "TW"],
                "supportedDASDeviceTypes" : ["NONE"],
                "packageUrl": "http://fileserver.hgst.com/test/app_manager/com.wdc.mycloud.loadtest.app1.apk",
                "localeSpecificContent": [{
                        "locale": "en-US",
                        "title": "Load test 1",
                        "shortDescription": "Load test 1 - TW QA",
                        "longDescription": "Load test App is a app to keep Read and Write in user's owner folder, the app is for app manager test",
                        "releaseNoteUrl": "For App Manager Test.",
                        "localeSpecificImage": "https://s3-us-west-2.amazonaws.com/wd-portal-apps/dev1/com.wdc.branded.security/icon/security.png"
                    }, {
                        "locale": "zh-TW",
                        "title": "讀寫測試軟體 1",
                        "shortDescription": "讀寫測試軟體 - 臺灣測試團隊使用",
                        "longDescription": "讀寫測試軟體是一個可以持續讀寫使用著資料夾的應用程序",
                        "releaseNoteUrl": "App Manager 測試使用",
                        "localeSpecificImage": "https://s3-us-west-2.amazonaws.com/wd-portal-apps/dev1/com.wdc.branded.security/icon/security.png"
                    }
                ]
            })
        )

    def get_ota_status(self, device_id):
        admin_token = self.get_admin_token()
        url = '{}/ota/v1/device/deviceId/{}'.format(self.ota_bucket_url, device_id)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(admin_token)}
        result = requests.get(url, headers=headers)
        if result.status_code != 200:
            self.log.error("Failed to get the OTA status! Status code: {}".format(result.status_code))
            return {}
        else:
            return result.json()

    def get_ota_bucket_info(self, bucket_id):
        self.log.info("Getting info from bucket ID: {}".format(bucket_id))
        admin_token = self.get_admin_token()
        result = self.json_request(
            method='GET',
            url='{}/ota/v1/bucket/{}'.format(self.ota_bucket_url, bucket_id),
            headers={'Content-Type': 'application/json',
                     'Authorization': 'Bearer {}'.format(admin_token),
                     'x-correlation-id': 'Platform-Automation-Test-get_ota_GZA_buckets_info'}
        )
        if result.status_code != 200:
            self.log.error("Failed to get the OTA bucket info! Status code: {}".format(result.status_code))
            return {}
        else:
            return result.json()

    def get_ota_bucket_last_promoted_build(self, bucket_id):
        result = self.get_ota_bucket_info(bucket_id)
        to_versions = result.get('data').get('versions').keys()
        self.log.info("The to_version list in this OTA bucket: {}".format(to_versions))
        last_promoted_build = str(max(map(LegacyVersion, to_versions)))
        self.log.info("The last promoted build is: {}".format(last_promoted_build))
        return last_promoted_build

    def update_ota_bucket(self, bucket_id, bucket_info):
        self.log.info("Updating bucket ID: {}".format(bucket_id))
        admin_token = self.get_admin_token()
        result = self.json_request(
            method='POST',
            url='{}/ota/v1/bucket/{}'.format(self.ota_bucket_url, bucket_id),
            headers={'Authorization': 'Bearer {}'.format(admin_token)},
            data=json.dumps(bucket_info)
        )
        if result.status_code != 200:
            self.log.error("Failed to update the OTA bucket! Status code: {}".format(result.status_code))
            return {}
        else:
            return result.json()

    def get_device_by_security_code(self, security_code):
        self.log.debug('Get device info by security code...')
        admin_token = self.get_admin_token()
        response = self.json_request(
            method='GET',
            url='{}/device/v1/device?securityCode={}'.format(GCS.get(self.env), security_code),
            headers={'Authorization': 'Bearer {}'.format(admin_token)}
        )
        if not response or response.status_code != 200:
            self.error("fail to get device by security code", response)
        return response.json()

    def update_device_ota_status(self, device_id, status="updateReboot"):
        admin_token = self.get_admin_token()
        result = self.json_request(
            method='PUT',
            url='{}/ota/v1/status/deviceId/{}'.format(self.ota_bucket_url, device_id),
            headers={'Authorization': 'Bearer {}'.format(admin_token)},
            data=json.dumps({'status': status})
        )
        if result.status_code != 200:
            self.error('Update device OTA status failed, status code:{0}, error log:{1}'.
                       format(result.status_code, result.content))
        else:
            self.log.info('Update device OTA status successfully')
            self.log.info('Response: {}'.format(result.content))

    def get_user_info_from_cloud(self, user_id=None, email=None):
        self.log.debug('Get user info using user_id or email from cloud ...')
        admin_token = self.get_admin_token()
        if email:
            url = '{0}/authservice/v1/auth0/user?email={1}'.format(self.auth_url, urllib.quote_plus(email))
        else:
            url = '{0}/authservice/v1/auth0/user?userId={1}'.format(self.auth_url, urllib.quote_plus(user_id))
        response = self.json_request(
            method='GET',
            url=url,
            headers={'Authorization': 'Bearer {}'.format(admin_token)}
            )
        if not response or response.status_code != 200:
            self.error("Failed to get the user info from cloud !", response)
        resp = response.json()
        return resp.get('data').pop() if resp.get('data', {}) else None


if __name__ == '__main__':

    cloud_obj = CloudAPI(env='prod')

    result = cloud_obj.get_ota_buckets_info('4.1.1-827', 'monarch')
    monarch_bucket_id = result['bucket_id']
    device_id = '09d5915a-50d8-4bf2-9b02-470e0c20065e'

    cloud_obj.register_device_in_cloud('monarch', device_id, '4.1.1-827')
    result = cloud_obj.check_device_in_ota_bucket(bucket_id=monarch_bucket_id,
                                                  device_id=device_id)
    if not result:
        # Add multiple devices in a list is available
        cloud_obj.add_device_in_ota_bucket(bucket_id=monarch_bucket_id,
                                           device_id=[device_id])
