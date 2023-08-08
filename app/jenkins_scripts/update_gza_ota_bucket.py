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
        self.last_promoted_build = parser.last_promoted_build
        self.start_fw_version = parser.start_fw_version
        self.method = parser.method
        if parser.special_bucket:
            self.bucket_type = "special"
        else:
            self.bucket_type = "default"

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

    def get_checksum(self, checksum_type, fw_image_name):
        if checksum_type not in ['md5', 'sha256']:
            raise RuntimeError("Invalid checksum format: {}".format(checksum_type))
        checksum_file_name = "{0}.{1}".format(fw_image_name, checksum_type)
        execute_local_cmd('wget -nv -N -t 20 -T 7200 {0}{1}'.format(self.fw_image_prefix, checksum_file_name))
        with open(checksum_file_name, 'r') as f:
            checksum = f.readline().strip()
        execute_local_cmd('rm {}'.format(checksum_file_name))
        if not checksum:
            raise RuntimeError(
                "Unable to find the {0} checksum information of image:{1}!".format(checksum_type, fw_image_name))
        return checksum

    def main(self):
        self.log.info("*** Cloud Env: {}".format(self.env))
        self.log.info("*** Models: {}".format(self.models))
        self.log.info("*** Bucket type: {}".format(self.bucket_type))

        if self.method == 'update':
            self.log.info("*** To Version: {}".format(self.fw))
            # Split version and combine them for the firmware image name
            regex = r"(.+)\.(\d+)"
            matches = re.match(regex, self.fw)
            if matches:  # Full match: 5.00.335, group 1: 5.00, group 2: 335
                self.version = matches.group(1)
                self.build = matches.group(2)
            fw_version_in_image = "{}.{}".format(self.version, self.build.zfill(3))

        for model in self.models:
            # Restore the version value when switching different models
            last_promoted_build = self.last_promoted_build
            start_fw_version = self.start_fw_version 
            # Get the bucket information from constant file
            device_info = GZA.DEVICE_INFO.get(model)
            ota_bucket_id = device_info.get('ota_{}_bucket_v2_{}'.format(self.bucket_type, self.env))
            if not ota_bucket_id:
                raise RuntimeError("Unable to find the {0} {1} OTA bucket information of {2}, check the constant file!".
                                   format(self.env, self.bucket_type, model))
            self.log.info("*** Bucket ID: {}".format(ota_bucket_id))

            if self.method == 'update':
                self.log.info("##### Updating the {0} {1} {2} OTA bucket #####".
                              format(model, self.env, self.bucket_type))
                if model == "Glacier":
                    fw_image_name = 'WDMyCloud_{}_{}.bin'.format(fw_version_in_image, self.env)
                elif model == "Mirrorman":
                    fw_image_name = 'WDCloud_{}_{}.bin'.format(fw_version_in_image, self.env)
                else:
                    fw_image_name = 'WDMyCloud{}_{}_{}.bin'.format(model, fw_version_in_image, self.env)
                fw_url = "{}{}".format(self.fw_image_prefix, fw_image_name)

                self.log.info("Try to fetch the checksum results")
                fw_md5_checksum = self.get_checksum('md5', fw_image_name)
                fw_sha256_checksum = self.get_checksum('sha256', fw_image_name)
                if not self.last_promoted_build:
                    self.log.info('The last promoted version is not specified, check it from current OTA bucket')
                    last_promoted_build = self.cloud_api.get_ota_bucket_last_promoted_build(ota_bucket_id)
                self.log.info('*** Last promoted version: {}'.format(self.last_promoted_build))
                if not self.start_fw_version:
                    self.log.info('Start version is not specified, get default value from constant file')
                    start_fw_version = device_info.get('ota_default_bucket_v2_start_version')
                self.log.info('*** Start version: {}'.format(self.start_fw_version))
                ota_update_info = dict(bucketType="multiversion",
                                       versions={last_promoted_build: None,
                                                 self.fw: {"maxServed": -1,
                                                           "url": fw_url,
                                                           "md5sum": fw_md5_checksum,
                                                           "sha256sum": fw_sha256_checksum,
                                                           "startVersion": start_fw_version,
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
                self.log.info("##### Getting the {0} {1} {2} OTA bucket #####".
                              format(model, self.env, self.bucket_type))
                response = self.cloud_api.get_ota_bucket_info(bucket_id=ota_bucket_id)
                print('** Bucket info =')
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
                        default="get")

    test = UPDATE_GZA_OTA_BUCKET(parser.parse_args())
    test.main()
