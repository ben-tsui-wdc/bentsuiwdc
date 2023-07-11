# -*- coding: utf-8 -*-
""" Test case to download and update firmware
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import re
import time
from packaging.version import parse as parse_version

# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.constants import Godzilla as GZA
from platform_libraries.common_utils import execute_local_cmd
from godzilla_scripts.bat_scripts.reboot import Reboot
from godzilla_scripts.bat_scripts.samba_rw_check import SambaRW
from godzilla_scripts.bat_scripts.afp_rw_check import AFPRW
from godzilla_scripts.bat_scripts.factory_reset import FactoryReset


class FirmwareUpdate(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Firmware Update'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1121'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        # self.file_server_ip = 'fileserver.hgst.com'
        self.file_server_ip = '10.200.141.26'
        self.local_image = False
        self.keep_fw_img = False
        self.force_update = False
        self.fw_version = None
        self.io_before_test = False
        self.idle_time = 180
        self.disable_ota = False
        self.overwrite = False
        self.data_integrity = False
        self.check_protocol = False
        self.mac_server_ip = '10.200.141.205'
        self.mac_username = 'wdcautotw10'
        self.mac_password = "Wdctest1234"
        self.skip_checksum_check = False
        self.negative = False
        self.factory_reset_after_upgrade = False
        self.local_image_path = None

    def before_test(self):
        self.exclude_firmware_version = ["3.00", "2.31", "2.40", "2.41", "2.42"]

        self.ssh_client.sftp_connect()

        # Workaround for GZA-7816, will be removed when developers fix the issue
        if self.ssh_client.check_file_in_device("/usr/local/upload/image.cfs"):
            self.ssh_client.execute_cmd("rm /usr/local/upload/image.cfs")

        # For Data Integrity Tests
        self.file_server_data_path = 'test/IOStress'
        self.download_url = 'ftp://ftp:ftppw@{}/{}'.format(self.file_server_ip, self.file_server_data_path)
        self.test_folder_name = 'ota_data_integrity'
        self.test_path = '/shares/{}/'.format(self.test_folder_name)
        if self.data_integrity:
            if not self.ssh_client.check_folder_in_device(self.test_path):
                self.ssh_client.create_share(self.test_folder_name)
            # Todo: Replace with ssh/afp after fixing the password reset problem between OS3 & OS5
            self.log.info("Download data for integrity testing")
            self.ssh_client.download_file(self.download_url, dst_path=self.test_path, timeout=60 * 60, is_folder=True)
            self.folder_md5_before = self.ssh_client.get_folder_md5_checksum(self.test_path)
            self.log.info("Folder MD5 before testing: {}".format(self.folder_md5_before))

        """ self.fw_version might be overwrite when the other test call this function with specified fw number,
            if not, use the environment firmware_version value
        """
        if not self.fw_version:
            self.fw_version = self.env.firmware_version

        self.log.info("Checking the firmware version before testing")
        current_firmware = self.ssh_client.get_firmware_version()
        if current_firmware == self.fw_version:
            if self.force_update:
                self.log.warning("The firmware version is already {} but force to update it again".
                                 format(current_firmware))
            else:
                raise self.err.TestSkipped("The firmware version is already {}, skip the test!".
                                           format(current_firmware))

        self.fw_img_folder = '/usr/local/upload'
        self.fw_update_status = '/tmp/update_fw_status'
        if self.env.model:
            self.model = self.env.model
        else:
            self.model = self.ssh_client.get_model_name()

        regex = r"(.+)\.(\d+)"
        matches = re.match(regex, self.fw_version)
        if matches:
            # Full match: 3.00.8, group 1: 3.00, group 2: 8
            self.version = matches.group(1)
            self.build = matches.group(2)
            self.log.info("*** version = {}".format(self.version))
            self.log.info("*** build = {}".format(self.build))
        else:
            raise self.err.TestSkipped("Unable to parser the firmware number: {}!".format(self.fw_version))

        self.restsdk_version_before = None
        # If original firmware is newer than the upgrade fw, run factory reset after fw update
        matches = re.match(regex, current_firmware)
        if matches:
            # Full match: 5.06.113, group 1: 5.06, group 2: 113
            origin_version = matches.group(1)
            origin_build = matches.group(2)
            # 5.06 -> 5, 06
            origin_os, origin_release = origin_version.split(".")
            new_os, new_release = self.version.split(".")
            if origin_os == '5' and new_os == '5':
                # Get the restsdk version before fw update and check if it's been downgraded after fw update
                self.restsdk_version_before = self.ssh_client.get_restsdk_version()
                # Check if it's OS5 downgrade
                if int(origin_release) > int(new_release) or \
                        int(origin_release) == int(new_release) and int(origin_build) > int(self.build):
                    self.log.info("The original firmware is newer than the upgrade firmware, "
                                  "will run factory reset after firmware upgrade")
                    self.factory_reset_after_upgrade = True

        device_info = GZA.DEVICE_INFO.get(self.model)
        self.fw_version_in_image = "{}.{}".format(self.version, self.build.zfill(3))
        if self.version in self.exclude_firmware_version:
            if self.model == "Mirrorman":
                self.fw_img_name = 'WD_Cloud_{0}_{1}.bin'.format(device_info['os3_fw_name'], self.fw_version_in_image)
            else:
                self.fw_img_name = 'My_Cloud_{0}_{1}.bin'.format(device_info['os3_fw_name'], self.fw_version_in_image)
        else:
            # 3.10 and 5.00 and later
            if self.model == "Glacier":
                self.fw_img_name = 'WDMyCloud_{0}_{1}.bin'.format(self.fw_version_in_image, self.env.cloud_env)
            elif self.model == "Mirrorman":
                self.fw_img_name = 'WDCloud_{0}_{1}.bin'.format(self.fw_version_in_image, self.env.cloud_env)
            else:
                self.fw_img_name = 'WDMyCloud{0}_{1}_{2}.bin'.format(self.model, self.fw_version_in_image,
                                                                     self.env.cloud_env)

        self.log.info("Firmware image name: {}".format(self.fw_img_name))
        if self.local_image:
            self.download_path = 'ftp://ftp:ftppw@{}/GZA/firmware/'.format(self.file_server_ip)
        else:
            if self.env.cloud_env == 'dev1':
                self.download_path = 'https://s3-us-west-2.amazonaws.com/cs-yocto.keystone/gza-dev1-wdmc-pr/{}/'.\
                    format(self.fw_version)
            elif self.env.cloud_env == 'qa1':
                self.download_path = 'https://cs-yocto-keystone-qa1.s3-us-west-2.amazonaws.com/gza-dev1-wdmc-pr/{}/'.\
                    format(self.fw_version)
            self.log.info("Firmware download path: {}".format(self.download_path))
            self.log.info("Try if the firmware image has been uploaded to AWS S3 server")
            try:
                execute_local_cmd(cmd='curl --output /dev/null --silent --head --fail "{}{}"'.
                                  format(self.download_path, self.fw_img_name), consoleOutput=False, timeout=60*5)
                self.log.info("The {} firmware image is on AWS S3 server".format(self.fw_version))
            except RuntimeError as e:
                self.log.error('The firmware image has not uploaded to AWS S3 server yet!')
                self.log.error('Error: {}'.format(repr(e)))
                raise

    def test(self):
        if self.io_before_test:
            self.log.info("Run some IO before testing")
            smbrw = SambaRW(self)
            smbrw.keep_test_data = True
            smbrw.before_test()
            smbrw.test()
            smbrw.after_test()
            if self.idle_time > 0:
                self.log.info("Wait for {} seconds after IO".format(self.idle_time))
                time.sleep(self.idle_time)

        # Download the firmware image
        self.log.info("Start downloading the firmware image and checksum file")
        max_retries = 5
        retries = 0
        valid_fw_image = False
        while retries < max_retries:
            try:
                result = self.ssh_client.check_file_in_device("/shares/Public/{}".format(self.fw_img_name))
                if result:
                    self.log.info("Firmware image already exist in the device, skip download steps")
                else:
                    if self.local_image_path:
                        self.log.info("Local image path: {} is specified, upload it to test device directly".
                                      format(self.local_image_path))
                        self.ssh_client.sftp_upload(self.local_image_path,
                                                    "/shares/Public/{}".format(self.fw_img_name))
                    else:
                        download_url = "{}{}".format(self.download_path, self.fw_img_name)
                        # Download will be skipped if the image already existing and last modified time is the same
                        execute_local_cmd(cmd='wget -nv -N -t 20 -T 7200 {}'.format(download_url), timeout=60*20)
                        self.ssh_client.sftp_upload("./{}".format(self.fw_img_name),
                                                    "/shares/Public/{}".format(self.fw_img_name))
                    if not self.ssh_client.check_file_in_device("/shares/Public/{}".format(self.fw_img_name)):
                        raise self.err.TestFailure("The firmware image does not exist in the device, download failed!")

                if self.version not in self.exclude_firmware_version and not self.skip_checksum_check \
                        and not self.local_image_path:
                    self.log.info("Download the MD5 checksum file and check the value")
                    checksum_file_name = "{}.md5".format(self.fw_img_name)
                    checksum_download_url = "{0}{1}".format(self.download_path, checksum_file_name)
                    execute_local_cmd('wget -nv -N -t 20 -T 7200 {}'.format(checksum_download_url))
                    with open(checksum_file_name, 'r') as f:
                        md5_expect = f.readline().strip()
                    self.log.info("Expect MD5: {}".format(md5_expect))
                    execute_local_cmd('rm {}'.format(checksum_file_name))
                    if not md5_expect:
                        raise self.err.TestFailure("Failed to download the md5 checksum file!")
                    self.log.info("Comparing the md5 checksum of downloaded firmware")
                    md5_image = self.ssh_client.execute_cmd("busybox md5sum /shares/Public/{}".
                                                            format(self.fw_img_name))[0].split()[0]
                    self.log.info("Firmware Image MD5: {}".format(md5_image))
                    if md5_expect != md5_image:
                        raise self.err.TestFailure("The firmware image MD5 should be {}, but it's {}!".
                                                   format(md5_expect, md5_image))
                    else:
                        self.log.info("Firmware image MD5 checksum comparison PASS!")
                valid_fw_image = True
                break
            except Exception as e:
                self.log.warning("Download firmware image failed, error message: {}".format(repr(e)))
                self.log.info("Wait for 30 secs and retry, {} retries left...".format(max_retries-retries))
                retries += 1
                time.sleep(30)
        if not valid_fw_image:
            raise self.err.TestFailure("Download firmware failed after {} retries!".format(max_retries))

        if not self.ssh_client.check_hdd_ready_to_upgrade_fw():
            raise self.err.TestFailure('The HDD is not ready to update firmware!')
        else:
            self.log.info("HDD is ready for firmware upgrade")

        self.log.info("Clone the firmware image to the upload folder")
        self.ssh_client.execute_cmd("cp /shares/Public/{} {}".format(self.fw_img_name, self.fw_img_folder))

        self.log.info("Start upgrading the firmware")
        upgrade_cmd = 'upload_firmware -D'
        if self.overwrite:
            upgrade_cmd += ' -o'  # -o need to be in front of the -n
        upgrade_cmd += ' -n'
        # Add retries when the system is busy and failed to update
        fw_update_max_retries = 3
        fw_update_retries_count = 0
        while True:
            error_msg = self.ssh_client.execute_cmd("{0} {1}".format(upgrade_cmd, self.fw_img_name), timeout=60*30)[1]
            if '--errorCode "systemBusy" --status updateFail' in error_msg:
                if fw_update_retries_count <= fw_update_max_retries:
                    self.log.warning("System is busy, retry fw update after 120 secs")
                    time.sleep(120)
                    fw_update_retries_count += 1
                else:
                    raise self.err.TestFailure("Firmware update failed and reaches the max retries! System is always busy")
            else:
                break

        self.log.info("Firmware update script finished, wait for 30 seconds and check the status...")
        time.sleep(30)
        result = self.ssh_client.execute_cmd("cat {}".format(self.fw_update_status))[0]
        if self.negative:
            # Update firmware failed -> to 2.31 or 2.41, upload firmware file fail -> to 5.00 or 5.01
            if result == "0" or ("Update firmware failed" not in error_msg and
                                 "upload firmware file fail" not in error_msg):
                if result == "-1":
                    self.log.warning("Firmware update failed as expected but missing the error logs, check the results")
                else:
                    raise self.err.TestFailure("Test should have been failed in negative scenario but it's passed!")
            else:
                self.log.info("Test failed as expected in negative scenario!")
        else:
            if result != "0":
                if self.version == "2.31":
                    self.log.warning("The firmware update status is: {} but it might not be real failure in OS3 firmware".format("result"))
                else:
                    raise self.err.TestFailure("The firmware upgrade script failed! Error code: {}".format(result))
            else:
                self.log.info("Firmware upgrade script executed successfully")
                if self.overwrite:
                    # Skip the password cleanup step because the ssh password was cleaned too
                    pass
                    """
                    self.log.info("Try to recover the admin password when using overwrite upgrade")
                    self.ssh_client.execute_cmd("cp /tmp/default/passwd /etc/passwd")
                    self.ssh_client.execute_cmd("cp /tmp/default/shadow /etc/shadow")
                    self.ssh_client.execute_cmd("cp /tmp/default/passwd /usr/local/config/passwd")
                    self.ssh_client.execute_cmd("cp /tmp/default/shadow /usr/local/config/shadow")
                    """
            env_dict = self.env.dump_to_dict()
            if self.factory_reset_after_upgrade:
                factory_reset = FactoryReset(env_dict)
                factory_reset.main()
            else:
                self.log.info("Start rebooting the device")
                env_dict['Settings'] = ['uut_owner=False']
                reboot = Reboot(env_dict)
                reboot.no_rest_api = True
                reboot.test()

                # If original fw is not OS5, restsdk_version_before should be None and skip below step
                if self.restsdk_version_before:
                    # Check RestSDK version to cover the case that fw has been upgraded but restsdk version has been downgraded
                    try:
                        restsdk_info = self.ssh_client.get_device_info()
                        restsdk_version_after = restsdk_info.get('version')
                        self.log.warning("Restsdk version before: {}".format(self.restsdk_version_before))
                        self.log.warning("Restsdk version after: {}".format(restsdk_version_after))
                        if restsdk_info.get('message') == 'Recovering' or \
                                (restsdk_version_after and parse_version(restsdk_version_after) < parse_version(self.restsdk_version_before)):
                            self.log.info("RestSDK version has been downgraded, start running factory reset to clean the DB")
                            self.factory_reset_after_upgrade = True
                    except RuntimeError as e:
                        # In GZA 5.18.117, the restsdk will return 503 error when it's recovering
                        if repr(e) == "Failed to get the device info! Error code: 503":
                            self.log.warning("Restsdk is recovering, start running factory reset to clean the DB")
                            self.factory_reset_after_upgrade = True
                        else:
                            raise

                    if self.factory_reset_after_upgrade:
                        factory_reset = FactoryReset(env_dict)
                        factory_reset.main()

            if self.version not in self.exclude_firmware_version:
                self.ssh_client.stop_otaclient_service()

            if self.version == "2.31":
                self.log.info("Skip /etc/version check because of GZA-5626 will not be fixed in OS3 firmware")
            else:
                self.log.info("Checking the current firmware version")
                result = self.ssh_client.get_firmware_version()
                if result != self.fw_version_in_image:
                    raise self.err.TestFailure("Expect firmware: {0}, Current firmware: {1}".
                                               format(self.fw_version, result))
            if self.data_integrity:
                self.folder_md5_after = self.ssh_client.get_folder_md5_checksum(self.test_path)
                self.log.info("Folder MD5 after testing: {}".format(self.folder_md5_after))
                if self.folder_md5_before != self.folder_md5_after:
                    raise self.err.TestFailure("Data integrity check failed!")
                else:
                    self.log.info("Data integrity check passed")

            if self.check_protocol:
                self.log.info("Check SMB after firmware update")
                smbrw = SambaRW(self)
                smbrw.keep_test_data = True
                smbrw.before_test()
                smbrw.test()
                smbrw.after_test()

                self.log.info("Check AFP after firmware update")
                """ Skip the AFP temporarily since there's issues in long term testing
                afprw = AFPRW(self)
                afprw.mac_server_ip = self.mac_server_ip
                afprw.mac_username = self.mac_username
                afprw.mac_password = self.mac_password
                afprw.before_test()
                afprw.test()
                afprw.after_test()
                """

            self.log.info("Restart RestSDK service if it's in minimal mode")
            self.ssh_client.disable_restsdk_minimal_mode()
            self.log.info("Firmware is upgraded to {}, test PASSED!".format(result))

    def after_test(self):
        self.log.info("Setup the admin password after firmware update")
        self.ssh_client.execute_cmd('account -m -u "admin" -p "adminadmin"')

        if not self.keep_fw_img:
            file_path = '/shares/Public/{1}'.format(self.fw_img_folder, self.fw_img_name)
            if self.ssh_client.check_file_in_device(file_path):
                self.ssh_client.execute_cmd('rm {}'.format(file_path))

        if self.io_before_test:
            self.log.info("Clean the IO test file")
            file_name = "test50MB"  # the dummy test file in the samrw test
            if self.ssh_client.check_file_in_device("/shares/Public/{}".format(file_name)):
                self.ssh_client.execute_cmd("rm /shares/Public/{}".format(file_name))

        self.ssh_client.sftp_close()


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Firmware Update Test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/firmware_update.py --uut_ip 10.136.137.159:8001 \
                  --firmware_version 3.00.8 --local_image \
        """)
    # parser.add_argument('--file_server_ip', default='fileserver.hgst.com', help='File server IP address')
    parser.add_argument('--file_server_ip', default='10.200.141.26', help='File server IP address')
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    parser.add_argument('--keep_fw_img', action='store_true', default=False, help='Keep downloaded firmware')
    parser.add_argument('--force_update', action='store_true', default=False, help='Update the firmware even if the version is the same')
    parser.add_argument('--io_before_test', help='Use samba to run IO before testing', action='store_true')
    parser.add_argument('--idle_time', help='idle time after io', default=180)
    parser.add_argument('-do', '--disable_ota', help='disable the otaclient', action='store_true')
    parser.add_argument('-o', '--overwrite', help='use to force downgrade to OS3 versions', action='store_true')
    parser.add_argument('-di', '--data_integrity', help='check data integrity before firmware update', action='store_true')
    parser.add_argument('-cp', '--check_protocol', help='check I/O works with different protocols after firmware update', action='store_true')
    parser.add_argument('-scc', '--skip_checksum_check', help='skip the fw image checksum comparison', action='store_true')
    parser.add_argument('--mac_server_ip', help='mac operating system verison', default='10.200.141.205')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='wdcautotw10')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac client', default='Wdctest1234')
    parser.add_argument('-n', '--negative', help='Run negative test and expect the test should failed', action='store_true')
    parser.add_argument('-frau', '--factory_reset_after_upgrade', action='store_true',
                        help='If we already know restsdk will be downgraded after fw update, clean the db directly')
    parser.add_argument('--local_image_path', default=None, help='Specify the absolute path of local firmware image')

    test = FirmwareUpdate(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
