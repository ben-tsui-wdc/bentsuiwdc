# -*- coding: utf-8 -*-
""" Test cases to update Firmware image by using fw_update command.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import os
import shutil
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.common_utils import execute_local_cmd
from platform_libraries.constants import KDP
from kdp_scripts.bat_scripts.check_nasadmin_daemon import CheckNasAdminDaemon


class FirmwareUpdate(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-191 - Firmware Update Test with Firmware Signing'
    TEST_JIRA_ID = 'KDP-191,KDP-214,KDP-3204,KDP-3205,KDP-2057,KDP-4576,KDP-5510'
    REPORT_NAME = 'Single_run'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.file_server_ip = 'fileserver.hgst.com'
        self.local_image = False
        self.S3_image = False
        self.keep_fw_img = False
        self.force_update = False
        self.rename_name = 'fw_update.mv'
        self.rename_fw_update = False
        self.clean_restsdk_db = False
        self.tmp_full_test = False
        self.include_gpkg = False
        self.check_enable_root = False
        self.local_image_path = None

    def init(self):
        self.build_name = 'kdp-firmware'
        self.timeout = 60*20
        self.environment = self.uut.get('environment')
        self.model = self.uut.get('model')
        self.fw_update_folder = '{}/firmware_update'.format(KDP.DATA_VOLUME_PATH.get(self.model))
        if self.model == 'monarch2': self.model = 'monarch'
        if self.model == 'pelican2': self.model = 'pelican'
        if self.model == 'yodaplus2': self.model = 'yodaplus'
        self.image = 'install.img'
        self.cert_file = 'image.cert'
        self.outputpath = '/root/app/output'
        self.skip_test = False
        self.enable_root_path = '/wd_config'
        # Delete the folder at the first iteration, if keep_fw_img is enabled,
        # firmware image will not be deleted and can be used in the following iterations
        if self.ssh_client.check_file_in_device(self.fw_update_folder):
            self.ssh_client.execute_cmd('rm -r {}'.format(self.fw_update_folder))

    def before_test(self):
        if not self.ssh_client.scp: self.ssh_client.scp_connect()
        # Device Environment Check
        if self.env.cloud_env != self.environment:
            self.log.warning('Current device env is {0}, is not match with given env {1}, use {2} env to update'
                             .format(self.environment, self.env.cloud_env, self.environment))
            self.env.cloud_env = self.environment

        # Device firmware Check
        if not self.env.firmware_version:
            self.version = self.uut.get('firmware')
        else:
            self.version = self.env.firmware_version

        # Check Download path
        if self.local_image:
            download_path = 'ftp://ftp:ftppw@{}/KDP/firmware/'.format(self.file_server_ip)
        elif self.S3_image:
            if self.env.cloud_env == 'qa1':
                s3_bucket_url = 'https://s3-us-west-2.amazonaws.com/cs-yocto-keystone-qa1/kdp-firmware/qa1/'
            elif self.env.cloud_env == 'dev1':
                s3_bucket_url = 'https://s3-us-west-2.amazonaws.com/cs-yocto.keystone/kdp-firmware/dev1/'
            download_path = s3_bucket_url + self.version + '/'
        else:
            build_server_url = 'http://repo.wdc.com/content/repositories/projects/kdp/kdp-firmware/'
            download_path = build_server_url + self.version + '/'
        if self.S3_image:
            if self.include_gpkg:
                self.fw_img_name = '{0}-{1}-{2}-ota-installer-{3}-gpkg.zip'.format(self.build_name, self.env.cloud_env, self.version, self.model)
            else:
                self.fw_img_name = '{0}-{1}-{2}-ota-installer-{3}.zip'.format(self.build_name, self.env.cloud_env, self.version, self.model)
        else:
            if self.include_gpkg:
                self.fw_img_name = '{0}-{1}-os-ota-installer-{2}-gpkg-{3}.zip'.format(self.build_name, self.version, self.model, self.env.cloud_env)
            else:
                self.fw_img_name = '{0}-{1}-ota-installer-{2}-{3}.zip'.format(self.build_name, self.version, self.model, self.env.cloud_env)
        self.log.info('Firmware image download URL: {0}{1}'.format(download_path, self.fw_img_name))

        self.log.info('***** Checking the device firmware version before update ...')
        current_fw = self.ssh_client.get_firmware_version()
        if self.include_gpkg:
            self.version = self.version + '.s'
        if current_fw == self.version:
            if self.force_update:
                self.log.warning("The firmware version is already in {}, but force to update it again"
                                 .format(current_fw))
            else:
                self.skip_test = True
                raise self.err.TestSkipped("The firmware version is already in {}, skip the update test!"
                                           .format(current_fw))
        self.fw_image_path_on_device = "{0}/{1}".format(self.fw_update_folder, self.image)
        self.cert_file_path_on_device = "{0}/{1}".format(self.fw_update_folder, self.cert_file)
        exist_image_result = self.ssh_client.check_file_in_device(self.fw_image_path_on_device)
        download_new_image = True
        if exist_image_result:
            # Compare the md5 checksum and image in the device to make sure firmware image wasn't corrupt during testing
            if self.firmware_md5_checksum_compare():
                self.log.info("Firmware image already exist in the device and checksum is matched, skip download steps")
                download_new_image = False
            else:
                # self.log.warning('Skip download steps without do firmware checksum comparison !!')
                self.log.warning('The md5 checksum and firmware image in the device was not matched, '
                                 'delete the folder and download again!')
                self.ssh_client.execute_cmd('rm -r {}'.format(self.fw_update_folder))
        if download_new_image:
            self.log.info('***** Start to download firmware image {}*****'.format(self.version))
            max_retries = 5
            retries = 0
            while retries < max_retries:
                try:
                    if os.path.exists(self.build_name): shutil.rmtree(self.build_name, ignore_errors=True)
                    os.mkdir(self.build_name)
                    if self.local_image_path:
                        self.log.info("Local image path: {} is specified, upload it to test device directly".
                                      format(self.local_image_path))
                        self.safe_unzip(zip_file=self.local_image_path, extractpath=self.build_name)
                    else:
                        download_url = "{0}{1}".format(download_path, self.fw_img_name)
                        execute_local_cmd(cmd='wget -nv -N -t 20 -T 7200 {0} -P {1}'.
                                          format(download_url, self.build_name), timeout=60*20)
                        self.safe_unzip(zip_file=os.path.join(self.build_name, self.fw_img_name),
                                        extractpath=self.build_name)
                    if not self.ssh_client.check_file_in_device(self.fw_update_folder):
                        self.ssh_client.execute_cmd('mkdir {}'.format(self.fw_update_folder))
                    self.ssh_client.scp_upload("./{0}/{1}".format(self.build_name, self.image), self.fw_image_path_on_device)
                    self.ssh_client.scp_upload("./{0}/{1}.md5".format(self.build_name, self.image), self.fw_image_path_on_device + '.md5')
                    self.ssh_client.scp_upload("./{0}/{1}".format(self.build_name, self.cert_file), self.cert_file_path_on_device)
                    if not self.ssh_client.check_file_in_device(self.fw_image_path_on_device):
                        raise self.err.TestFailure("The firmware image does not exist in the device, download failed!")
                    if not self.ssh_client.check_file_in_device(self.cert_file_path_on_device):
                        raise self.err.TestFailure("The cert file does not exist in the device, test failed!")
                    if not self.firmware_md5_checksum_compare(): raise
                    valid_fw_image = True
                    break
                except Exception as e:
                    self.log.warning("Download firmware image failed, error message: {}".format(repr(e)))
                    self.log.info("wait for 30 secs to retry, {} retries left...".format(max_retries-retries))
                    retries += 1
                    time.sleep(10)
            if not valid_fw_image:
                raise self.err.TestFailure("Download firmware failed after {} retries!".format(max_retries))

        self.log.info('***** Rename back fw_update binary *****')
        self.ssh_client.execute_cmd('test -e /usr/sbin/{0} && mv /usr/sbin/{0} /usr/sbin/fw_update'.format(self.rename_name))

        if self.check_enable_root:
            self.TEST_JIRA_ID += ',KDP-4196'
            self.log.info('Delete the enable_root file before testing')
            self.ssh_client.remount_and_execute_cmd(remount_path=self.enable_root_path,
                                                    command='test -f {0}/enable_root && rm {0}/enable_root'.
                                                    format(self.enable_root_path))

    def test(self):
        if self.ssh_client.check_is_kdp_device():
            cbr = self.ssh_client.execute_cmd('cat /proc/device-tree/factory/cbr', quiet=True)[0]
            nbr = self.ssh_client.execute_cmd('cat /proc/device-tree/factory/nbr', quiet=True)[0]
            bna = self.ssh_client.execute_cmd('cat /proc/device-tree/factory/bna', quiet=True)[0]
            bootstate = self.ssh_client.execute_cmd('cat /proc/device-tree/factory/bootstate', quiet=True)[0]
            self.log.info('cbr = {}'.format(cbr))
            self.log.info('nbr = {}'.format(nbr))
            self.log.info('bna = {}'.format(bna))
            self.log.info('bootstate = {}'.format(bootstate))
        if self.ssh_client.check_is_rnd_device():
            cur_fw = self.ssh_client.execute_cmd('cat /proc/device-tree/factory/cur_fw', quiet=True)[0]
            self.log.info('cur_fw = {}'.format(cur_fw))

        self.log.info('***** Start to verify {} by using fw_verify tool'.format(self.cert_file))
        if self.model == 'monarch' or self.model == 'pelican' or self.model == 'yodaplus':
            check_model = self.model+'2'
        else:
            check_model = self.model
        fw_verify_cmd = 'fw_verify -f {0} -v {1} -b {2} -m {3}'.format(
            self.cert_file_path_on_device, self.version.split('-')[0], self.version.split('-')[1], check_model)
        return_code, cert_result = self.ssh_client.execute(fw_verify_cmd)
        if return_code != 0:
            raise self.err.TestFailure('Firmware Signing verified failed! Return code: {}, response: {}'.format(
                return_code, cert_result))
        else:
            self.log.info('Firmware Signing test passed, rename image back to {0}'.format(self.fw_image_path_on_device))
            self.ssh_client.execute_cmd('mv {0}/{1} {2}'.format(
                self.fw_update_folder, self.image, self.fw_image_path_on_device))

        if self.tmp_full_test:
            self.log.info('tmp full test setup is True, full up the tmp folder ...')
            tmp_left_space = self.ssh_client.execute_cmd('df | grep tmpfs | grep /tmp').split()[3]
            self.ssh_client.execute_cmd('busybox fallocate -l {0}K /tmp/{1}K.txt'.format(tmp_left_space))
            self.ssh_client.execute_cmd('df')

        self.log.info('***** Start to update firmware image: {} *****'.format(self.version))
        self.ssh_client.unlock_otaclient_service_kdp()
        exitcode, _ = self.ssh_client.execute(command='fw_update {0} -r -v {1}'
                                              .format(self.fw_image_path_on_device, self.version), timeout=self.timeout)
        if exitcode != 0:
            raise self.err.TestFailure('Executed fw_update command failed! Error code: {}'.format(exitcode))
        else:
            if self.check_enable_root:
                if self.ssh_client.check_file_in_device('{}/enable_root'.format(self.enable_root_path)):
                    raise self.err.TestFailure('The enable_root file should not be created after firmware update!')
                else:
                    self.log.info('Checked the enable_root file was not created after firmware update, '
                                  'restore it for ssh connection after device rebooting')
                    self.ssh_client.remount_and_execute_cmd(remount_path=self.enable_root_path,
                                                            command='touch {}/enable_root'.
                                                            format(self.enable_root_path))
            # Enable ota lock before reboot to avoid ota start immediately after reboot process
            # it's a persist property so it won't be changed when device reboot
            if not self.env.enable_auto_ota:
                self.log.info('enable_auto_ota is set to false, lock otaclient service')
                self.ssh_client.lock_otaclient_service_kdp()
            self.log.info('Execute do_reboot command to reboot device ...')
            self.ssh_client.execute_cmd('do_reboot')
        self.log.info('Waiting for device reboot, Timeout: {} seconds.'.format(self.timeout))
        start_time = time.time()
        if not self.ssh_client.wait_for_device_to_shutdown():
            raise self.err.TestFailure('Device was not shut down successfully!')
        if self.serial_client:
            self.serial_client.wait_for_boot_complete_kdp(timeout=self.timeout)
            if 'yodaplus' in self.model: 
                if self.serial_client.check_ifplug_zombie_exist():
                    raise self.err.TestFailure('ifplug zombie found, test failed!!')
            self.env.check_ip_change_by_console()
        if not self.ssh_client.wait_for_device_boot_completed():
            raise self.err.TestFailure('Device was not boot up successfully!')
        self.log.warning("Reboot completed in {} seconds".format(time.time() - start_time))

        # For downgrade restsdk database situation
        self.log.info("Check 'wrong version' log exist or not to handle downgrade case ...")
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60) and not self.ssh_client.check_file_in_device('/var/log/wdlog.log'):
            self.log.info('Waiting for 5 secs for wdpublic.log generated ...')
            time.sleep(5)
        log_wrong_version = self.ssh_client.execute_cmd("cat /var/log/wdpublic.log | grep 'wrong version'")[0]
        if log_wrong_version: self.clean_restsdk_db = True
        # Reset restsdk database
        if self.clean_restsdk_db:
            self.ssh_client.clean_up_restsdk_service(restart_otaclient=self.env.enable_auto_ota)

        fw_updated_ver = self.ssh_client.get_firmware_version()
        if fw_updated_ver == self.version:
            self.ssh_client.check_restsdk_service()
            self.log.info('Firmware Update Utility Test PASSED!!')
            if os.path.exists(self.outputpath):
                self.log.info('Update Firmware Success!!!')
                with open("UpdateSuccess.txt", "w") as f:
                    f.write('Update Firmware Success\n')
                shutil.copy('UpdateSuccess.txt', '{}/UpdateSuccess.txt'.format(self.outputpath))
        else:
            if os.path.exists(self.outputpath):
                self.log.error('Update Firmware Failed!!!')
                with open("UpdateFailed.txt", "w") as f:
                    f.write('Update Firmware Failed\n')
                shutil.copy('UpdateFailed.txt', '{}/UpdateFailed.txt'.format(self.outputpath))
            raise self.err.TestFailure('Current firmware({}) is not match with given update version({}), Test Failed!!'
                                       .format(fw_updated_ver, self.version))

        if self.env.is_nasadmin_supported():
            env_dict = self.env.dump_to_dict()
            check_nasadmin_daemon = CheckNasAdminDaemon(env_dict)
            check_nasadmin_daemon.main()
        self.check_wd_config()  # David's request
        self.check_docker_service_after_reboot() # KDP-4728 request
        if self.include_gpkg:
            self.check_gpkg_daemon()

    def check_docker_service_after_reboot(self):
        self.log.info('Start to check the docker service after boot completed...')
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60): # Wait for dockerd start up
            exitcode, _ = self.ssh_client.execute('pidof dockerd')
            if exitcode != 0: 
                self.log.warning("docker process is not found, wait for 5 secs and try again...")
                time.sleep(5)
            else:
                break
        else:
            raise self.err.TestFailure("dockerd process still not found after retry for 1 min")
        # self.timing.reset_start_time()
        # while not self.timing.is_timeout(60): # Wait for containerd start up
        #     exitcode, _ = self.ssh_client.execute('pidof containerd')
        #     if exitcode != 0: 
        #         self.log.warning("containerd process is not found, wait for 5 secs and try again...")
        #         time.sleep(5)
        #     else:
        #         break
        # else:
        #     raise self.err.TestFailure("containerd process still not found after retry for 1 min")

    def check_wd_config(self):
        if self.model == 'monarch' or self.model == 'pelican' or self.model == 'yodaplus':
            bootConfig_path = "/wd_config/bootConfig"
        else:
            bootConfig_path = "/sys_configs/bootConfig"
        stdout, stderr = self.ssh_client.execute_cmd('[ -e {} ] && echo  "Found" || echo "Not Found"'.
                                                     format(bootConfig_path))
        if stdout.strip() == "Found":
            pass
        else:
            raise self.err.TestFailure('{} doesn\'t exist'.format(bootConfig_path))

    def check_gpkg_daemon(self):
        gpkg_service = self.ssh_client.execute_cmd("ps | grep gpkg | grep -v 'grep gpkg'")
        if not gpkg_service:
            raise self.err.TestFailure('gpkg service dose not exist, test failed !!')

    def safe_unzip(self, zip_file, extractpath='.'):
        import zipfile
        self.log.info('Start unzip file')
        with zipfile.ZipFile(zip_file, 'r') as zf:
            for member in zf.infolist():
                abspath = os.path.abspath(os.path.join(extractpath, member.filename))
                if abspath.startswith(os.path.abspath(extractpath)):
                    zf.extract(member, extractpath)

    def firmware_md5_checksum_compare(self):
        self.log.info("Comparing the md5 checksum of downloaded firmware")
        exist_md5_result = self.ssh_client.check_file_in_device(self.fw_image_path_on_device + '.md5')
        if exist_md5_result:
            md5_expect = self.ssh_client.execute_cmd("cat {0}.md5".format(self.fw_image_path_on_device))[0].rstrip("\n")
            md5_image = self.ssh_client.execute_cmd("busybox md5sum {0}"
                                                    .format(self.fw_image_path_on_device))[0].split()[0]
            self.log.info("Firmware Image MD5: {}".format(md5_image))
            if md5_expect != md5_image:
                raise self.err.TestFailure("The firmware image MD5 should be {}, but it's {}!"
                                           .format(md5_expect, md5_image))
            else:
                self.log.info("Firmware image MD5 checksum comparison PASS!")
                return True
        else:
            self.log.warning('{} is not in the device, cannot compare the firmware image checksum'
                             .format(self.fw_image_path_on_device + '.md5'))
            return False

    def after_test(self):
        if self.enable_root_path:
            if not self.ssh_client.check_file_in_device('{}/enable_root'.format(self.enable_root_path)):
                self.log.warning('The enable_root file was not restored after firmware update for some reason, '
                                 'restore it now')
                self.ssh_client.remount_and_execute_cmd(remount_path=self.enable_root_path,
                                                        command='touch {}/enable_root'.
                                                        format(self.enable_root_path))
        if not self.skip_test:
            if not self.keep_fw_img:
                self.log.info('Not keep firmware image, remove the download folder if it exist ...')
                if self.ssh_client.check_file_in_device(self.fw_update_folder):
                    self.ssh_client.execute_cmd('rm -r {}'.format(self.fw_update_folder))
            if self.rename_fw_update:
                self.log.info('***** Rename fw_update binary *****')
                self.ssh_client.execute_cmd('test -e /usr/sbin/fw_update && mv /usr/sbin/fw_update /usr/sbin/{}'
                                            .format(self.rename_name))
        self.ssh_client.scp_close()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Firmware Update Utility Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/firmware_update.py --uut_ip 10.92.224.68 --firmware_version 4.1.0-725 --cloud_env dev1\
        """)

    # Test Arguments
    parser.add_argument('--file_server_ip', default='fileserver.hgst.com', help='File server IP address')
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    parser.add_argument('--S3_image', action='store_true', default=False,
                        help='Download ota firmware image from S3 bucket server')
    parser.add_argument('--keep_fw_img', action='store_true', default=False, help='Keep downloaded firmware image')
    parser.add_argument('--force_update', action='store_true', default=False, help='Update the firmware even if the version is the same')
    parser.add_argument('--clean_restsdk_db', action='store_true', default=False, help='Clear restsdk database')
    parser.add_argument('--rename_name', default='fw_update.mv', help='Rename name of fw_update binary')
    parser.add_argument('--rename_fw_update', action='store_true', default=False, help='Rename fw_update binary after updated')
    parser.add_argument('--tmp_full_test', action='store_true', default=False, help='Test firmware update during tmp folder is full')
    parser.add_argument('--include_gpkg', action='store_true', default=False, help='Update firmware with gpkg build')
    parser.add_argument('--check_enable_root', action='store_true', default=False, help='Check firmware update should not create enable_root file')
    parser.add_argument('--local_image_path', default=None, help='Specify the absolute path of local firmware image')

    args = parser.parse_args()

    test = FirmwareUpdate(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp or resp is None:
        sys.exit(0)
    sys.exit(1)
