# -*- coding: utf-8 -*-
""" Tools to update GZA OTA default buckets
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import re
from argparse import ArgumentParser
import pprint
# platform modules
from platform_libraries.common_utils import create_logger, execute_local_cmd
from platform_libraries.constants import Godzilla as GZA
from platform_libraries.cloud_api import CloudAPI
from termcolor import colored


class UPDATE_GZA_OTA_BUCKET(object):

    def __init__(self, parser):
        self.log = create_logger(overwrite=False)
        self.env = parser.cloud_env
        self.fw = parser.to_firmware
        self.models = parser.models
        self.special_bucket = parser.special_bucket
        self.last_promoted_build = parser.last_promoted_build
        self.start_fw_version = parser.start_fw_version
        self.method = parser.method

        if not self.env:
            raise RuntimeError("Please enter the -env/--cloud_env value")
        if not self.models:
            raise RuntimeError("Please enter the -m/--models list")
        if self.method == 'update':
            if not self.fw:
                raise RuntimeError("Please enter the -fw/--to_firmware value")

        self.cloud_api = CloudAPI(env=self.env)
        # New fw image prefix since 5.10 version
        if self.env == 'dev1':
            self.fw_image_prefix = 'https://s3-us-west-2.amazonaws.com/cs-yocto.keystone/gza-dev1-wdmc-pr/{}/'.format(
                self.fw)
        elif self.env == 'qa1':
            self.fw_image_prefix = 'https://cs-yocto-keystone-qa1.s3-us-west-2.amazonaws.com/gza-dev1-wdmc-pr/{}/'.format(
                self.fw)
        self.build_server_prefix = "http://repo.wdc.com/content/repositories/projects/Godzilla/gza-firmware/"
        self.ota_md5_checksum_dict = {}
        self.ota_sha256_checksum_dict = {}

    def main(self):
        self.log.info("*** Cloud Env: {}".format(self.env))
        self.log.info("*** To Version: {}".format(self.fw))
        self.log.info("*** Update model lists: {}".format(self.models))

        if self.method == 'update':
            self.log.info("Downloading the fiwmare image MD5 checksum list")
            regex = r"(.+)\.(\d+)"
            matches = re.match(regex, self.fw)
            if matches:  # Full match: 5.00.335, group 1: 5.00, group 2: 335
                self.version = matches.group(1)
                self.build = matches.group(2)

            self.log.info("Setting up the new information of OTA bucket")
            self.build_server_path = "{0}{1}-{2}".format(self.build_server_prefix, self.version, self.build)
            execute_local_cmd('wget -nv -N -t 20 -T 7200 {}/firmware_md5sum.txt'.format(self.build_server_path))
            md5_checksum_list = execute_local_cmd('cat firmware_md5sum.txt', consoleOutput=False)[0].split()
            for index, value in enumerate(md5_checksum_list):
                if index % 2 == 0:
                    self.ota_md5_checksum_dict[value] = md5_checksum_list[index + 1]

            execute_local_cmd('wget -nv -N -t 20 -T 7200 {}/firmware_sha256sum.txt'.format(self.build_server_path))
            sha256_checksum_list = execute_local_cmd('cat firmware_sha256sum.txt', consoleOutput=False)[0].split()
            for index, value in enumerate(sha256_checksum_list):
                if index % 2 == 0:
                    self.ota_sha256_checksum_dict[value] = sha256_checksum_list[index + 1]

            fw_version_in_image = "{}.{}".format(self.version, self.build.zfill(3))

        for model in self.models:
            device_info = GZA.DEVICE_INFO.get(model)
            if self.special_bucket:
                ota_bucket_id = device_info.get('ota_special_bucket_v2_{}'.format(self.env))
            else:
                ota_bucket_id = device_info.get('ota_default_bucket_v2_{}'.format(self.env))

            if self.method == 'update':
                self.log.info("##### Updating the {} OTA bucket of {} #####".format(self.env, model))
                if model == "Glacier":
                    fw_image_name = 'WDMyCloud_{}_{}.bin'.format(fw_version_in_image, self.env)
                elif model == "Mirrorman":
                    fw_image_name = 'WDCloud_{}_{}.bin'.format(fw_version_in_image, self.env)
                else:
                    fw_image_name = 'WDMyCloud{}_{}_{}.bin'.format(model, fw_version_in_image, self.env)
                fw_url = "{}{}".format(self.fw_image_prefix, fw_image_name)
                fw_md5_checksum = self.ota_md5_checksum_dict.get(fw_image_name)
                if not fw_md5_checksum:
                    raise RuntimeError(
                        "Unable to find the md5 checksum inforamtion for image:{}!".format(fw_image_name))

                fw_sha256_checksum = self.ota_sha256_checksum_dict.get(fw_image_name)
                if not fw_sha256_checksum:
                    raise RuntimeError(
                        "Unable to find the sha256 checksum inforamtion for image:{}!".format(fw_image_name))

                if not ota_bucket_id:
                    self.log.warning("Unable to find the {} OTA bucket information of {}, check the constant file!".
                                     format(self.env, model))
                    continue
                else:
                    if not self.last_promoted_build:
                        self.last_promoted_build = self.cloud_api.get_ota_bucket_last_promoted_build(ota_bucket_id)
                    if not self.start_fw_version:
                        # The start version will not be changed normally so get it from constant.
                        self.start_fw_version = device_info.get('ota_default_bucket_v2_start_version')
                    ota_update_info = dict(bucketType="multiversion",
                                           versions={self.last_promoted_build: None,
                                                     self.fw: {"maxServed": -1,
                                                               "url": fw_url,
                                                               "md5sum": fw_md5_checksum,
                                                               "sha256sum": fw_sha256_checksum,
                                                               "startVersion": self.start_fw_version,
                                                               "updateFailCount": 5,
                                                               "isImmediate": False,
                                                               "updateUboot": False}
                                                     }
                                           )
                    print(colored(pprint.pformat(ota_update_info), 'magenta'))
                    response = self.cloud_api.update_ota_bucket(bucket_id=ota_bucket_id, bucket_info=ota_update_info)
                    if response:
                        self.log.info("Response: {}".format(response))
                        self.log.info("Update the {} OTA bucket of {} PASSED!".format(self.env, model))
                    else:
                        raise RuntimeError("Update the {} OTA bucket of {} FAILED!".format(self.env, model))
            else:
                response = self.cloud_api.get_ota_bucket_info(bucket_id=ota_bucket_id)
                print('** data =')
                print(colored(pprint.pformat(response), 'magenta'))

        self.log.info("##### All the OTA buckets are completed successfully! #####")


if __name__ == '__main__':
    parser = ArgumentParser("""\
        *** Update GZA OTA Buckets ***
        """)

    parser.add_argument('-env', '--cloud_env', help='The cloud environment')
    parser.add_argument('-fw', '--to_firmware', help='The firmware version after OTA')
    parser.add_argument('-m', '--models', nargs='+', help='The list of models, e.g. -m PR2100 PR4100')
    parser.add_argument('-sb', '--special_bucket', action="store_true",
                        help='Select special buckets in constant.py, otherwise the default buckets will be updated')
    parser.add_argument('-last_promoted_build', '--last_promoted_build',
                        help='Specify the last to_version and remove that field. If it is None, '
                             'script will choose the latest version', default=None)
    parser.add_argument('-start_fw_version', '--start_fw_version',
                        help='Start firmware version info inside the to_version. '
                             'If it is None, script will get the default value from constant', default=None)
    parser.add_argument('--method', choices=['get', 'update'], help='choose to get bucket info or update bucket',
                        default="update")

    test = UPDATE_GZA_OTA_BUCKET(parser.parse_args())
    test.main()
