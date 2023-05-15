# -*- coding: utf-8 -*-
""" A simple tool to udpate/get specific bucket value."""
__author__ = "Vance Lo <Vance.Lo@wdc.com>"
__author2__ = "Ben Tsui <ben.tsui@wdc.com"

# std modules
import argparse
import sys
import json
from datetime import datetime
import pprint
# 3rd party modules
import requests
from uuid import uuid4
from termcolor import colored
# Platform libraries
from platform_libraries.constants import KDP
from platform_libraries.cloud_api import CloudAPI


class OTABucket(object):

    def __init__(self, env, ver, bid, model, gpkg, os_type):
        self.ver = ver
        self.gpkg = gpkg
        if self.gpkg:
            self.to_ver = self.ver + '.s'
        else:
            self.to_ver = self.ver
        self.env = env
        self.bid = bid
        self.model = model
        self.os_type = os_type
        if self.model in ['monarch2', 'pelican2', 'yodaplus2']:
            self.fw_img_model = self.model.strip('2')
        else:
            self.fw_img_model = self.model
        self.cloud_api = CloudAPI(env=self.env)
        self.admin_token = None
        if self.os_type == 'kdp':
            self.s_build_name = 'kdp-firmware'
        else:
            self.s_build_name = 'MCAndroid'
        if self.env == 'qa1':
            if self.os_type == 'kdp':
                self.build_name = '{}-qa1'.format(self.s_build_name)
            else:
                self.build_name = '{}-QA'.format(self.s_build_name)
            self.client_id = "automation"
            self.client_secret = "QEA64Za93rJR8rdhgndtG374"
            self.ota_bucket_url = "https://58ruoa2iek.execute-api.us-west-2.amazonaws.com/staging"
            self.auth0_url = 'https://staging.dev.wdckeystone.com/authrouter'
            self.m2m_url = 'https://staging.dev.wdckeystone.com/m2m'
            self.download_path = 'https://s3-us-west-2.amazonaws.com/cs-yocto-keystone-qa1/{}'.format(self.s_build_name)
        elif self.env == 'prod':
            if self.os_type == 'kdp':
                self.build_name = self.s_build_name
            else:
                self.build_name = '{}-prod'.format(self.s_build_name)
            self.client_id = "ota_management"
            self.client_secret = "n8ZDA]pm9azuo2hnR^[FPyzBv=7]8eUU"
            self.ota_bucket_url = "https://prod-gateway.wdckeystone.com/ota"
            self.auth0_url = 'https://prod.wdckeystone.com/authrouter'
            self.m2m_url = 'https://prod.wdckeystone.com/m2m'
            self.download_path = 'https://updates.mycloud.com/{}'.format(self.s_build_name)
        elif self.env == 'dev1':
            if self.os_type == 'kdp':
                self.build_name = '{}-dev1'.format(self.s_build_name)
            else:
                self.build_name = self.s_build_name
            self.client_id = "automation"
            self.client_secret = "f*(d9Dzh5@MxwK&u"
            self.ota_bucket_url = "https://dev1-gateway.wdtest1.com/ota"
            self.auth0_url = 'https://dev1.wdtest1.com/authrouter'
            self.m2m_url = 'https://dev1.wdtest1.com/m2m'
            self.download_path = 'https://s3-us-west-2.amazonaws.com/cs-yocto.keystone/{}'.format(self.s_build_name)
        elif self.env =='integration':
            self.build_name = '{}-integration'.format(self.s_build_name)
        else:
            print("Unknown environment: {}".format(self.env))
            sys.exit(1)

        if self.bid == 'default' or not self.bid:
            self.bid = KDP.DEFAULT_BUCKET_ID_V2.get(self.model).get(self.env)
        elif self.bid == 'special':
            self.bid = KDP.SPECIAL_BUCKET_ID_V2.get(self.model).get(self.env)

        if not self.bid:
            print("Bucket id is not specified or cannot find specific bucket id in constant file!")
            sys.exit(1)

        self.post_value = uuid4().hex
        if self.gpkg:
            self.image_url = '{0}/{1}/{2}/{3}-{4}-ota-installer-{5}-gpkg.zip' \
                    .format(self.download_path, self.env, self.ver, self.build_name, self.ver, self.fw_img_model)
        else:
            self.image_url = '{0}/{1}/{2}/{3}-{4}-ota-installer-{5}.zip' \
                    .format(self.download_path, self.env, self.ver, self.build_name, self.ver, self.fw_img_model)
        print("image_url: {}".format(self.image_url))

    def update_bucket(self, start_fw_version, last_promoted_build):
        print('********* Start to update bucket -- Model: {}, Environment: {}, Bucket_id: {}, toVersion: {} *********'
              .format(self.model, self.env, self.bid, self.to_ver))
        admin_token = self.get_admin_token()
        # Update image_url due to some situation ver is not given at __init__ steps
        if self.gpkg:
            self.image_url = '{0}/{1}/{2}/{3}-{4}-ota-installer-{5}-gpkg.zip' \
                    .format(self.download_path, self.env, self.ver, self.build_name, self.ver, self.fw_img_model)
        else:
            self.image_url = '{0}/{1}/{2}/{3}-{4}-ota-installer-{5}.zip' \
                    .format(self.download_path, self.env, self.ver, self.build_name, self.ver, self.fw_img_model)
        self.md5sum = self.get_md5()
        self.sha256sum = self.get_sha256()
        url = '{}/ota/v1/bucket/{}'.format(self.ota_bucket_url, self.bid)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(admin_token),
                   'x-correlation-id': 'Automation-Test-update_bucket-{}'.format(self.post_value)}

        if not last_promoted_build:
            last_promoted_build = self.cloud_api.get_ota_bucket_last_promoted_build(self.bid)

        if not start_fw_version:
            start_fw_version = KDP.DEFAULT_BUCKET_V2_START_VERSION.get(self.model)

        data = {"bucketType": "multiversion",
                "versions": {last_promoted_build: None,
                             self.ver: {"maxServed": -1,
                                        "url": self.image_url,
                                        "md5sum": self.md5sum,
                                        "sha256sum": self.sha256sum,
                                        "startVersion": start_fw_version,
                                        "updateFailCount": 5,
                                        "isImmediate": False,
                                        "updateUboot": False}
                             }
                }

        print('** URL = {}'.format(url))
        print('** headers =')
        print('** data =')
        print(colored(pprint.pformat(data), 'magenta'))

        result = requests.post(url, headers=headers, data=json.dumps(data))

        if result.status_code == 200:
            print('********* Bucket values updated *********')
            print('Model: {}'.format(self.model))
            print('Environment: {}'.format(self.env))
            print('Bucket ID: {}'.format(self.bid))
            print('toVersion: {}'.format(self.to_ver))
            print('S3 image URL: {}'.format(self.image_url))
            print('md5sum: {}'.format(self.md5sum))
            print('sha256sum: {}'.format(self.sha256sum))
        else:
            print('Failed to update bucket value, status code:{0}, error message:{1}'
                  .format(result.status_code, result.content))
            sys.exit(1)
        # time.sleep(1)
        # print('********* Check OTA Specific Bucket Info *********')
        # result = self.get_ota_specific_buckets_info()
        # ota_to_version = result.get('to_version')
        # ota_url = result.get('url')
        # ota_md5sum = result.get('md5sum')
        # ota_sha256sum = result.get('sha256sum')
        # bucket_name = result.get('bucket_name')
        # ota_start_version = result.get('start_version')
        # print('bucket_name: {}'.format(bucket_name))
        # print('device_type: {}'.format(result.get('device_type')))
        # print('start_version: {}'.format(ota_start_version))
        # print('to_version: {}'.format(ota_to_version))
        # print('url: {}'.format(ota_url))
        # print('md5sum: {}'.format(ota_md5sum))
        # print('sha256sum: {}'.format(ota_sha256sum))
        # if ota_to_version != self.to_ver or ota_url != self.image_url or ota_md5sum != self.md5sum or ota_sha256sum != self.sha256sum:
        #     print('Update OTA bucket value failed !!!')
        #     sys.exit(1)
        # elif update_bucket_name and bucket_name != update_bucket_name:
        #     print('Update OTA bucket name failed !!!')
        #     sys.exit(1)
        # elif start_fw_version and ota_start_version != start_fw_version:
        #     print('Update OTA start version failed !!!')
        #     sys.exit(1)
        # else:
        #     print('********* Update ota bucket successfully *********')

    def get_admin_token(self):
        """
            Get cloud admin token for OTA use

            :return: Admin token in String format.
        """
        if self.admin_token:
            print('Set expire time to 36000.')
            self.token_expire_time = 36000
            time_passed = (datetime.now() - self.admin_token_time).seconds
            if time_passed < (self.token_expire_time - 3600):
                print('Use existed admin token, it will be expired in {} secs'.
                               format(self.token_expire_time - time_passed))
                return self.admin_token
            else:
                print('Token will be expired in an hour, renew it.')

        print('Getting new admin token...')
        url = '{}/v9/m2m/token'.format(self.m2m_url)
        data = {'clientId': self.client_id,
                'secret': self.client_secret}
        headers = {'Content-Type': 'application/json',
                    'x-correlation-id': 'Vance_Script_get_token'}
        print('** URL = {}'.format(url))
        print('** headers = {}'.format(headers))
        print('** data = {}'.format(data))

        result = requests.post(url, data=json.dumps(data), headers=headers)

        if result.status_code == 200:
            print('Get admin token successfully')
            self.admin_token_time = datetime.now()
            self.admin_token = result.json()['token']
            print('Admin token: {}'.format(self.admin_token))
            return self.admin_token
        else:
            print('Failed to get admin token, status code:{0}, error message:{1}'
                  .format(result.status_code, result.content))
            sys.exit(1)

    def get_ota_specific_buckets_info(self):
        admin_token = self.get_admin_token()
        url = '{}/ota/v1/bucket/{}'.format(self.ota_bucket_url, self.bid)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(admin_token),
                   'x-correlation-id': 'Automation-Test-get_ota_specific_buckets_info-{}'.format(self.post_value)}
        print('** URL = {}'.format(url))
        print('** headers = {}'.format(headers))
        result = requests.get(url, headers=headers)
        if result.status_code != 200:
            print('Get OTA buckets failed, status code:{0}, error log:{1}'.format(result.status_code, result.content))
            sys.exit(1)
        else:
            return result.json()['data']

    def get_md5(self):
        if self.os_type == 'kdp':
            self.md5_url = self.image_url + '.md5'
        else:
            self.md5_url = '{0}/{1}/{2}/{3}-{4}-image-{5}.md5'\
                           .format(self.download_path, self.env, self.ver, self.build_name, self.ver, self.fw_img_model)
        print("md5_url: {}".format(self.md5_url))
        result = requests.get(self.md5_url)
        if result.status_code != 200:
            print('Get image md5sum failed, status code:{0}, error log:{1}'.format(result.status_code, result.content))
            sys.exit(1)
        else:
            if not result.text.strip():
                print('Md5sum is empty!')
                sys.exit(1)
            else:
                return result.text.strip()

    def get_sha256(self):
        if self.os_type == 'kdp':
            self.sha256_url = self.image_url + '.sha256'
        else:
            self.sha256_url = '{0}/{1}/{2}/{3}-{4}-image-{5}.sha256'\
                           .format(self.download_path, self.env, self.ver, self.build_name, self.ver, self.fw_img_model)
        print("sha256_url: {}".format(self.sha256_url))
        result = requests.get(self.sha256_url)
        if result.status_code != 200:
            print('Get image sha256 checksum failed, status code:{0}, error log:{1}'.format(result.status_code, result.content))
            sys.exit(1)
        else:
            if not result.text.strip():
                print('sha256 is empty!')
                sys.exit(1)
            else:
                return result.text.strip()
        '''
        ## Get sha256sum by download the image and calculate by script itself
        download_zip_filename = '{0}-{1}-ota-installer-{2}.zip'.format(self.build_name, self.ver, self.fw_img_model)
        self.image_url = '{0}/{1}/{2}/{3}-{4}-ota-installer-{5}.zip' \
                 .format(self.download_path, self.env, self.ver, self.build_name, self.ver, self.fw_img_model)
        print("Download image from url to calculate sha256: {}".format(self.image_url))
        os.system('wget {}'.format(self.image_url))
        with open(download_zip_filename,"rb") as f:
            bytes = f.read() # read entire file as bytes
            readable_hash = hashlib.sha256(bytes).hexdigest();
        print('sha256sum: {}'.format(readable_hash))
        os.remove(download_zip_filename)
        return readable_hash
        '''
    def get_restdb_version(self, ver):
        if self.env == 'qa1':
            env = 'QA'
        elif self.env == 'dev1':
            env = 'dev'
        elif self.env == 'prod':
            env = 'prod'
        else:
            env = self.env
            print('Unexpected env value !!!')
        print('Start to get {} RestDBVersion ...'.format(ver))
        # corrections right fw_build_rul path
        if self.os_type == 'kdp':
            fw_build_url = 'http://jenkins.wdc.com/job/KDP-{0}/{1}/api/json'\
                .format(ver.split('-')[0], ver.split('-')[1])
        else:
            if ver.startswith('6.2.'):
                fw_build_url = 'http://jenkins.wdc.com/job/MycloudAndroid-{0}_{1}_{2}-{3}-{4}/{5}/api/json'\
                    .format(ver.split('.')[0], ver.split('.')[1], 0,
                        env, self.model, ver.split('-')[1])
            else:
                fw_build_url = 'http://jenkins.wdc.com/job/MycloudAndroid-{0}_{1}_{2}-{3}-{4}/{5}/api/json'\
                    .format(ver.split('.')[0], ver.split('.')[1], ver.split('-')[0].split('.')[2],
                        env, self.model, ver.split('-')[1])
        print('FW Build URL = {}'.format(fw_build_url))
        result = requests.get(fw_build_url)
        if result.status_code != 200:
            print('Get FW build info failed, status code:{0}, error log:{1}'.format(result.status_code, result.content))
            sys.exit(1)
        else:
            description = result.json()['description']
            if self.os_type == 'kdp':
                rest_sdk_ver = [x for x in description.split('<br/>') if 'RestSDK' in x][0].split(': ')[1]
            else:
                rest_sdk_ver = [x for x in description.split('<br/>') if 'Rest SDK' in x][0].split(': ')[1]
            print('RestSDK version = {}'.format(rest_sdk_ver))
            rest_sdk_build = rest_sdk_ver.split('-')[1]
            print('RestSDK build = {}'.format(rest_sdk_build))

            # Get RestDB Version
            if rest_sdk_ver.split('-')[0] == '1.6.0' or rest_sdk_ver.split('-')[0] == '1.8.0' or rest_sdk_ver.split('-')[0] == '2.0.0':
                restsdkdb_url = "http://10.248.38.55/job/rest-api-SDK_stable/{}/api/json".format(rest_sdk_build)
            elif rest_sdk_ver.split('-')[0] == '1.5.0':
                restsdkdb_url = "http://10.248.38.55/job/rest-api-SDK_1.5.0/{}/api/json".format(rest_sdk_build)
            else:
                restsdkdb_url = "http://jenkins.wdc.com/job/rest-api-SDK_devel/{}/api/json".format(rest_sdk_build)
            result = requests.get(restsdkdb_url)
            if result.status_code != 200:
                print('Get RestSDK build info failed, status code:{0}, error log:{1}'.format(result.status_code, result.content))
                sys.exit(1)
            else:
                description = result.json()['description']
                RestDBVersion = [x for x in description.split('<br/>') if 'RestDBVersion' in x][0].split(': ')[1]
                print('RestDBVersion = {}'.format(RestDBVersion))
                return RestDBVersion

    def db_migration(self, start_fw, test_fw):
        start_fw_db = self.get_restdb_version(start_fw)
        test_fw_db = self.get_restdb_version(test_fw)
        if start_fw_db != test_fw_db:
            print('RestDBVersion is different.')
            return True
        else:
            print('RestDBVersion is same.')
            return False


if __name__ == '__main__':
    # Handle input arguments.
    parser = argparse.ArgumentParser(description='Update specific bucket script')
    parser.add_argument('-env', '--environment', help='Target environment', default='dev1')
    parser.add_argument('-ver', '--fw_version', help='Firmware version', default=None)
    parser.add_argument('-bid', '--bucket_id', help='Type "default", "special" or specific Bucket ID', default="default")
    parser.add_argument('-model', '--model', help='Update model', default='yodaplus')
    parser.add_argument('-update', '--bucket_update', help='Action to update bucket value', action='store_true')
    parser.add_argument('-get', '--get_bucket_info', help='Action to get bucket info', action='store_true')
    parser.add_argument('-getDB', '--get_DB_version', help='Action to get restSDK DB version', action='store_true')
    parser.add_argument('-compare_db', '--compare_DB_version', help='Action to compare restSDK DB version', action='store_true')
    parser.add_argument('-start_fw', '--start_fw_version',
                        help='Start firmware version info inside the to_version. '
                             'If it is None, script will get the default value from constant', default=None)
    parser.add_argument('-get_md5', '--get_MD5_checksum', help='Action to get firmware md5sum', action='store_true')
    parser.add_argument('-get_sha', '--get_sha256_checksum', help='Action to get firmware sha256', action='store_true')
    parser.add_argument('-gpkg', '--include_gpkg', help='For Gpkg build use', action='store_true')
    parser.add_argument('-last_promoted_build', '--last_promoted_build',
                        help='Specify the last to_version and remove that field. If it is None, '
                             'script will choose the latest version', default=None)
    parser.add_argument('-os_type', '--os_type', help='Android or KDP firmware', choices=['kdp', 'android'],
                        default='kdp')
    args = parser.parse_args()

    env = args.environment
    ver = args.fw_version
    bid = args.bucket_id
    model = args.model
    update = args.bucket_update
    get = args.get_bucket_info
    getDB = args.get_DB_version
    compare_db = args.compare_DB_version
    start_fw = args.start_fw_version
    get_md5 = args.get_MD5_checksum
    get_sha = args.get_sha256_checksum
    gpkg = args.include_gpkg
    last_promoted_build = args.last_promoted_build
    os_type = args.os_type

    # Start update bucket
    otabucket = OTABucket(env=env, ver=ver, bid=bid, model=model, gpkg=gpkg, os_type=os_type)
    if update:
        otabucket.update_bucket(start_fw_version=start_fw, last_promoted_build=last_promoted_build)
    if get:
        bucket_info = otabucket.get_ota_specific_buckets_info()
        print(colored(pprint.pformat(otabucket.get_ota_specific_buckets_info()), 'magenta'))
        start_version = list()
        to_version = list()
        for k, v in bucket_info.get('versions').items():
            to_version.append(k)
            start_version.append(v.get('start_version'))
        try:
            with open('/root/app/output/bucket_info.txt', 'w') as f:
                for i, start_version in enumerate(start_version):
                    if i == 0:
                        prefix = ""
                    else:
                        prefix = "_{}".format(i)
                    f.write('START_VERSION{}={}\n'.format(prefix, start_version))
                    f.write('TO_VERSION{}={}\n'.format(prefix, to_version[i]))
        except:
            with open('bucket_info.txt', 'w') as f:
                for i, start_version in enumerate(start_version):
                    if i == 0:
                        prefix = ""
                    else:
                        prefix = "_{}".format(i)
                    f.write('START_VERSION{}={}\n'.format(prefix, start_version))
                    f.write('TO_VERSION{}={}\n'.format(prefix, to_version[i]))
    if getDB:
        get_db_version = otabucket.get_restdb_version(ver)
        try:
            with open('/root/app/output/db_ver.txt', 'w') as f:
                f.write('RestDBVersion={}\n'.format(get_db_version))
        except:
            with open('db_ver.txt', 'w') as f:
                f.write('RestDBVersion={}\n'.format(get_db_version))

    if compare_db:
        compare_db = otabucket.db_migration(start_fw=start_fw, test_fw=ver)
        try:
            with open('/root/app/output/db_migration.txt', 'w') as f:
                f.write('DB_MIGRATION={}\n'.format(compare_db))
        except:
            with open('db_migration.txt', 'w') as f:
                f.write('DB_MIGRATION={}\n'.format(compare_db))

    if get_md5:
        md5sum = otabucket.get_md5()
        print('md5sum: {}'.format(md5sum))

    if get_sha:
        sha256 = otabucket.get_sha256()
        print('sha256sum: {}'.format(sha256))
