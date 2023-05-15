# -*- coding: utf-8 -*-
""" Tool to verify OTA upgrade path the the checksum of firmware images
"""
# std modules
import re
import pprint
import glob
import os
import xml.etree.ElementTree as ET
from argparse import ArgumentParser

from platform_libraries.common_utils import create_logger, execute_local_cmd
from platform_libraries.constants import Godzilla as GZA


class CheckOTAPath(object):

    def __init__(self, parser):
        self.log = create_logger(overwrite=False)
        self.start_fw = parser.start_fw
        self.to_fw = parser.to_fw
        self.test_model = parser.test_model
        if not self.start_fw:
            raise RuntimeError("Please enter the --start_fw/-sf value")
        if not self.to_fw:
            raise RuntimeError("Please enter the --to_fw/-tf value")
        if not self.test_model:
            raise RuntimeError("Please enter the --test_model/-tm list")
        # Below parameters used to print error messages at the end of testing
        self.test_failed = False
        self.error_list = []
        self.ota_checksum_dict = {}

    def main(self):
        self.log.info("*** Start Version: {}".format(self.start_fw))
        self.log.info("*** Expect To Version: {}".format(self.to_fw))
        self.log.info("*** Test model lists: {}".format(self.test_model))

        self.log.info("Downloading the fiwmare image MD5 checksum list before testing...")
        regex = r"(.+)\.(\d+)"
        matches = re.match(regex, self.to_fw)
        if matches:  # Full match: 5.00.335, group 1: 5.00, group 2: 335
            self.version = matches.group(1)
            self.build = matches.group(2)

        self.build_server_path = "http://repo.wdc.com/content/repositories/projects/Godzilla/gza-firmware/" + \
                                 "{0}-{1}".format(self.version, self.build)

        execute_local_cmd('wget -nv -N -t 20 -T 7200 {}/firmware_md5sum.txt'.format(self.build_server_path))

        checksum_list = execute_local_cmd('cat firmware_md5sum.txt', consoleOutput=False)[0].split()
        for index, value in enumerate(checksum_list):
            if index % 2 == 0:
                self.ota_checksum_dict[value] = checksum_list[index+1]

        for model in self.test_model:
            self.log.info("##### Verifying the download path of: {} #####".format(model))
            device_info = GZA.DEVICE_INFO.get(model)
            url = 'https://support.wdc.com/nas/list.asp?devtype={0}&devfw={1}'.format(device_info.get('ota_name'),
                                                                                      self.start_fw)
            ota_path_info = execute_local_cmd('curl "{}"'.format(url), consoleOutput=False)[0]
            root = ET.fromstring(ota_path_info)
            self.log.info("OTA_path_info:\n{}".format(ota_path_info))
            self.log.info("Comparing the firmware version...")
            ota_to_version = root.find('./Upgrades/Upgrade/Version').text
            self.log.info("OTA_to_version: {}".format(ota_to_version))
            if not ota_to_version:
                self.error("{} firmware version check FAILED! Cannot get the to_version!".format(model))
            elif ota_to_version != self.to_fw:
                self.error("{} firmware version check FAILED! Expect: {}, Actual: {}".
                           format(model, self.to_fw, ota_to_version))
            else:
                self.log.info("{} firmware version check PASSED!".format(model))

            ota_image_url = root.find('./Upgrades/Upgrade/Image').text
            self.log.info("Image URL: {}".format(ota_image_url))
            if not ota_image_url:
                self.error("{} firmware image checksum comparison FAILED! Cannot get the image url!".format(model))
            else:
                self.log.info("Downloading the firmware image...")
                execute_local_cmd('wget -nv -N -t 20 -T 7200 {}'.format(ota_image_url), timeout=60 * 20)
                fw_image_name = ota_image_url.replace('https://downloads.wdc.com/nas/', '')
                self.log.info("Comparing the MD5 checksum...")
                md5sum_expect = self.ota_checksum_dict.get(fw_image_name)
                md5sum_actual = execute_local_cmd('md5sum {}'.format(fw_image_name), consoleOutput=True)[0].split()[0]
                if md5sum_actual != md5sum_expect:
                    self.error("{} firmware image checksum comparison FAILED! Expect: {}, Actual: {}".
                               format(model, md5sum_expect, md5sum_actual))
                else:
                    self.log.info("{} firmware image checksum comparison PASSED!".format(model))

        self.log.info("Clean up the firmware images and checksum file")
        for f in glob.glob("*.bin"):
            os.remove(f)
        os.remove('firmware_md5sum.txt')

        if self.test_failed:
            raise RuntimeError("Check OTA path FAILED! Errors:\n{}".format(self.error_list))
        else:
            self.log.info("##### All the OTA paths are checked and PASSED! #####")

    def error(self, error_msg):
        self.error_list.append(error_msg)
        self.log.error(error_msg)
        if not self.test_failed:
            self.test_failed = True


if __name__ == '__main__':
    parser = ArgumentParser("""\
        *** Get logcat from GZA device ***
        """)

    parser.add_argument('-sf', '--start_fw', help='The OTA start firmware')
    parser.add_argument('-tf', '--to_fw', help='The firmware version after OTA')
    parser.add_argument('-tm', '--test_model', nargs='+', help='The list of test models, e.g. -tm PR2100 PR4100')

    test = CheckOTAPath(parser.parse_args())
    test.main()

