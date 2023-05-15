# -*- coding: utf-8 -*-
""" Test cases to test device reboot (included send request by restAPI and SSH commands)
    and check service and status after rebooted.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"
__author2__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import random
import sys
import time
import os
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.restsdk_tests.functional_tests.get_video_stream import GetVideoStreamTest
from kdp_scripts.restsdk_tests.functional_tests.upload_file import UploadFileTest
from platform_libraries.constants import KDP
from platform_libraries.constants import RnD
from platform_libraries.restAPI import RestAPI
from kdp_scripts.bat_scripts.check_nasadmin_daemon import CheckNasAdminDaemon


class Reboot(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'Device Reboot Test and check service and status after reboot'
    TEST_JIRA_ID = 'KDP-200,KDP-1008,KDP-1009,KDP-1010,KDP-3296,KDP-1015,KDP-1178,KDP-1936,KDP-3293,KDP-3294,KDP-3295,KDP-3297,KDP-3298,KDP-5510'
    REPORT_NAME = 'Single_run'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.no_wait_device = False
        self.no_rest_api = True
        self.no_read_write_check = False
        self.check_ota_image_path = True
        self.check_device_process_status = True
        self.check_device_ready = True
        self.transcoding_test = True
        self.unsafe_reboot = False
        self.set_hdd_standby = False

    def init(self):
        self.timeout = 60*20
        self.model = self.uut.get('model')
        self.is_kdp_device = self.ssh_client.check_is_kdp_device()
        self.fsck_happened_count = 0

    def test(self):
        if self.set_hdd_standby:
            self.hdd_standby()

        # This is to prevent sometimes device become pingable before rebooting
        if self.ssh_client.check_file_in_device('/tmp/system_ready'):
            self.log.info('Remove the /tmp/system_ready before rebooting the device')
            self.ssh_client.execute_cmd('rm /tmp/system_ready')

        if self.no_rest_api:
            if self.unsafe_reboot:
                self.log.warning('Use unsafe reboot command to reboot device.')
                self.ssh_client.unsafe_reboot_device()
            else:
                self.log.info('Use SSH command to reboot device.')
                self.ssh_client.reboot_device()
        else:
            self.log.info('Start to use REST API to reboot device.')
            if self.env.uut_restsdk_port:
                uut_ip = "{}:{}".format(self.env.uut_ip, self.env.uut_restsdk_port)
            else:
                uut_ip = self.env.uut_ip
            self.uut_owner = RestAPI(uut_ip=uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
            self.uut_owner.id = 0  # Reset uut_owner.id
            self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']})
            self.deviceid_before = self.uut_owner.get_local_code_and_security_code()[0]
            self.log.info('Print out Device ID before reboot: {}'.format(self.deviceid_before))
            self.uut_owner.reboot_device()
            self.log.info('Device rebooting..')

        self.log.info('Expect device reboot complete in {} seconds.'.format(self.timeout))
        start_time = time.time()
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=self.timeout):
            raise self.err.TestFailure('Device was not shut down successfully!')
        if not self.no_wait_device:
            if 'yodaplus' in self.model and self.serial_client:
                self.serial_client.wait_for_boot_complete_kdp(timeout=self.timeout)
                if self.serial_client.check_ifplug_zombie_exist():
                    raise self.err.TestFailure('ifplug zombie found, test failed!!')
            if not self.ssh_client.wait_for_device_boot_completed(timeout=self.timeout):
                raise self.err.TestFailure('Device was not boot up successfully!')
        self.log.warning("Reboot complete in {} seconds".format(time.time() - start_time))

        self.ssh_client.check_restsdk_service()
        if self.check_device_ready:
            self.check_device_is_ready()
        if self.env.is_nasadmin_supported():
            env_dict = self.env.dump_to_dict()
            check_nasadmin_daemon = CheckNasAdminDaemon(env_dict)
            check_nasadmin_daemon.main()
        self.check_ota_download_path()
        self.check_wd_config()  # David's request
        self.check_fsck_happened()
        if self.check_device_process_status:
            self.check_device_process_and_status()
        if not self.no_read_write_check:
            if getattr(self, 'uut_owner', False):
                self.read_write_check_after_reboot()
            else:
                self.log.warning('uut_owner is False, skip the read_write_check_after_reboot')

        if self.transcoding_test:
            if getattr(self, 'uut_owner', False):
                self.transcoding_test_after_reboot()
            else:
                self.log.warning('uut_owner is False, skip the transcoding_test_after_reboot')
        if not self.no_rest_api:
            self.check_device_id_after_reboot()
            self.uut_owner.wait_until_cloud_connected(timeout=60*5)
        self.check_crash_report()
        self.check_md_raid()
        self.check_device_vol_mount_opt()

    def check_wd_config(self):
        if self.is_kdp_device:
            bootConfig_path = "/wd_config/bootConfig"
        else:
            bootConfig_path = "/sys_configs/bootConfig"
        stdout, stderr = self.ssh_client.execute_cmd('[ -e {} ] && echo  "Found" || echo "Not Found"'.format(bootConfig_path))
        if stdout.strip() == "Found":
            pass
        else:
            raise self.err.TestFailure('{} doesn\'t exist'.format(bootConfig_path))

    def read_write_check_after_reboot(self):
        def _local_md5_checksum(path):
            # Only use when the data set is downloaded from file server
            response = os.popen('md5sum {}'.format(path))
            if response:
                result = response.read().strip().split()[0]
                return result
            else:
                self.log.error("There's no response from md5 checksum")
                return None
        
        def _create_random_file(file_name, local_path='', file_size='1048576'):
            # Default 1MB dummy file
            self.log.info('Creating file: {}'.format(file_name))
            try:
                with open(os.path.join(local_path, file_name), 'wb') as f:
                    f.write(os.urandom(int(file_size)))
            except Exception as e:
                self.log.error('Failed to create file: {0}, error message: {1}'.format(local_path, repr(e)))
                raise

        TEST_FILE = 'DummyFileForRWCheck'

        # Create dummy file used for upload/download and calculate checksum
        _create_random_file(TEST_FILE)
        LOCAL_DUMMY_MD5 = _local_md5_checksum(TEST_FILE)
        if not LOCAL_DUMMY_MD5:
            raise self.err.TestFailure('Failed to get the local dummy md5 checksum!')
        self.log.warning("Local dummyfile MD5 Checksum: {}".format(LOCAL_DUMMY_MD5))

        # Delete existing dummy file before upload new dummy file
        try:
            self.uut_owner.delete_file_by_name(TEST_FILE)
        except RuntimeError as ex:
            if 'Not Found' in str(ex):
                self.log.info('No dummy file exist, skip delete file step! Message: {}'.format(ex))
            else:
                raise self.err.TestFailure('Delete dummy file failed! Message: {}'.format(ex))

        self.log.info('Try to upload a dummy file by device owner.....')
        with open(TEST_FILE, 'rb') as f:
            self.uut_owner.chuck_upload_file(file_object=f, file_name=TEST_FILE)
        user_id = self.uut_owner.get_user_id(escape=True)
        if self.is_kdp_device:
            user_roots_path = KDP.USER_ROOT_PATH
        else:
            user_roots_path = RnD.USER_ROOT_PATH
        path = '{0}/{1}/{2}'.format(user_roots_path, user_id, TEST_FILE)
        nas_md5 = self.ssh_client.get_file_md5_checksum(path)
        self.log.warning("NAS MD5 Checksum: {}".format(nas_md5))
        if LOCAL_DUMMY_MD5 != nas_md5:
            raise self.err.TestFailure('After device rebooted and upload a dummyfile to device, MD5 checksum comparison failed!')
        
        self.log.info('Try to download the dummy file.....')
        result, elapsed = self.uut_owner.search_file_by_parent_and_name(name=TEST_FILE, parent_id='root')
        file_id = result['id']
        content = self.uut_owner.get_file_content_v3(file_id).content
        with open('{}_download'.format(TEST_FILE), 'wb') as f:
            f.write(content)
        response = os.popen('md5sum {}_download'.format(TEST_FILE))
        if response:
            download_md5 = response.read().strip().split()[0]
        else:
            raise self.err.TestFailure("Failed to get local dummy file md5 after downloaded from test device!")
        self.log.warning("Downloaded file MD5 Checksum: {}".format(download_md5))
        if LOCAL_DUMMY_MD5 != download_md5:
            raise self.err.TestFailure("After device rebooted and download a dummyfile from device, MD5 checksum comparison failed!")

        self.log.info("Cleanup the dummyfiles")
        self.uut_owner.delete_file(file_id)
        os.remove('{}_download'.format(TEST_FILE))

    def check_device_id_after_reboot(self):
        self.deviceid_after = self.uut_owner.get_local_code_and_security_code()[0]
        self.log.info('Checking device ID after reboot, deivce_id: {}'.format(self.deviceid_after))
        if self.deviceid_before == self.deviceid_after:
            self.log.info('Device ID is match.')
        else:
            raise self.err.TestFailure('Device ID is not match! Test Failed!')

    def transcoding_test_after_reboot(self):
        self.log.info('Start transcoding test after device rebooted ...')
        env_dict = self.env.dump_to_dict()
        env_dict['file_url'] = 'http://fileserver.hgst.com/test/Large100GB/Video20GB/MP4/Elcard test files/BMP2_PSP.mp4'
        env_dict['check_mime_type'] = 'video/mp4'
        upload_file = UploadFileTest(env_dict)
        upload_file.before_test()
        upload_file.test()
        env_dict['file_name'] = 'BMP2_PSP.mp4'
        get_video_stream = GetVideoStreamTest(env_dict)
        get_video_stream.before_test()
        get_video_stream.test()

    def check_fsck_happened(self):
        stdout, stderr = self.ssh_client.execute_cmd('ls /var/log/analyticpublic.log')
        if 'No such file or directory' in stderr:
            self.log.warning("There is no /var/log/analyticpublic.log, maybe it's due to logrotate.")
        else:
            stdout, stderr = self.ssh_client.execute_cmd('cat /var/log/analyticpublic.log | grep -i DiskManager')
            diskmanager_log_list = stdout.split('\n')
            for line in diskmanager_log_list:
                if "Perform filesystem check for non-clean shutdown" in line:
                    self.fsck_happened_count += 1
                    self.log.warning(line)

    def check_ota_download_path(self):
        # If not check_ota_image_path, only print out the warning messages to mention the mount path changed
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60):
            check_path = self.ssh_client.execute_cmd('cat /var/log/otaclient.log | grep ota_start')[0]
            if check_path:
                break
            else:
                self.log.warning('Not found ota_start message, wait for 5 secs and try again ...')
                time.sleep(5)
        else:
            self.log.error('Not found ota_start message, skip ota image path check')
            self.check_ota_image_path = False
        if '/usr/local/upload' not in check_path and '/ota_download' not in check_path:
            self.log.warning('ota imagePath has been changed, not original downloadDir')
            if self.check_ota_image_path:
                raise self.err.TestFailure("ota imagePath has been changed, not original downloadDir !!")

    def check_device_is_ready(self):
        self.log.info('Checking if device is ready and proxyConnect is True')
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60):
            if self.ssh_client.get_device_ready_status() and self.ssh_client.get_device_proxy_connect_status():
                self.log.info('Device is ready and proxyConnect is True.')
                break
            else:
                self.log.warning('Device is not ready, wait for 5 secs and try again ...')
                time.sleep(5)
        else:
            raise self.err.TestFailure('Device status is not ready after retry for 60 secs!')

    def check_crash_report(self):
        self.log.info('Check analyticpublic log to see has crash report or not ...')
        crash_report = self.ssh_client.execute_cmd('grep -E crash_report /var/log/analyticpublic.log')[0]
        if crash_report:
            raise self.err.TestFailure("got crash_report: {}, test failed !!!".format(crash_report))

    def check_device_process_and_status(self):
        self.log.info('Start to check the device status after boot completed...')
        wd_disk_mounted = self.ssh_client.execute('getprop sys.wd.disk.mounted')[1]
        if wd_disk_mounted != '1': raise self.err.TestFailure("'sys.wd.disk.mounted' is not return 1")
        exitcode, _ = self.ssh_client.execute('mount | grep {}'.format(KDP.DATA_VOLUME_PATH.get(self.model)))
        if exitcode != 0: raise self.err.TestFailure("data volume is not in mount list")
        exitcode, _ = self.ssh_client.execute('ls /etc/ssl/certs/ca-certificates.crt')
        if exitcode != 0: raise self.err.TestFailure("ca-certificates.crt not found")
        exitcode, _ = self.ssh_client.execute('ls /tmp/wd_serial.txt')
        if exitcode != 0: raise self.err.TestFailure("wd_serial.txt not found")
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
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60): # Wait for containerd start up
            exitcode, _ = self.ssh_client.execute('pidof containerd')
            if exitcode != 0: 
                self.log.warning("containerd process is not found, wait for 5 secs and try again...")
                time.sleep(5)
            else:
                break
        else:
            raise self.err.TestFailure("containerd process still not found after retry for 1 min")
        exitcode, _ = self.ssh_client.execute('curl -V')
        if exitcode != 0: raise self.err.TestFailure("curl not support")
        # from 9.6.0 firmware, sqlite3 binary has been removed
        # exitcode, _ = self.ssh_client.execute('sqlite3 -version')
        # if exitcode != 0: raise self.err.TestFailure("sqlite3 not support")
        exitcode, _ = self.ssh_client.execute('fusermount -V')
        if exitcode != 0: raise self.err.TestFailure("fusermount not support")
        #exitcode, _ = self.ssh_client.execute('pidof kdpappmgr')
        #if exitcode != 0: raise self.err.TestFailure("kdpappmgr process not found")
        while not self.timing.is_timeout(60): # Wait for containerd start up
            exitcode, _ = self.ssh_client.execute('pidof kdpappmgr')
            if exitcode != 0: 
                self.log.warning("kdpappmgr process is not found, wait for 5 secs and try again...")
                time.sleep(5)
            else:
                break
        else:
            raise self.err.TestFailure("kdpappmgr process still not found after retry for 1 min")
        exitcode, _ = self.ssh_client.execute('pidof kdpappmgrd')
        if exitcode != 0: raise self.err.TestFailure("kdpappmgrd process not found")
        if self.uut['model'] in ['yodaplus2']:
            if self.uut.get('firmware').startswith('9.'):
                self.log.info("onboarding will be monitored with monit since 9.4.0 fw, skip checking onboarding.sh process")
            else:
                onabording_process = 'onboarding'
                exitcode, _ = self.ssh_client.execute('pidof {}.sh'.format(onabording_process))
                if exitcode != 0: raise self.err.TestFailure("{}.sh process not found".format(onabording_process))
                exitcode, _ = self.ssh_client.execute('pidof {}'.format(onabording_process))
                if exitcode != 0: raise self.err.TestFailure("{} process not found".format(onabording_process))

    def check_md_raid(self):
        if self.uut['model'] in ['pelican2', 'drax']:
            stdout, stderr = self.ssh_client.execute_cmd('mdadm --detail /dev/md1')
            if 'State : clean, degraded' in stdout or 'State : active, degraded' in stdout:
                raise self.err.TestFailure('The md raid is degraded.')
            if 'Active Devices : 2' not in stdout or 'Working Devices : 2' not in stdout:
                raise self.err.TestFailure('The "Active/Working Devices" is not 2.')
            self.timing.reset_start_time()
            while not self.timing.is_timeout(300): # Wait for getprop wd.volume.state
                stdout, stderr = self.ssh_client.execute_cmd('getprop wd.volume.state')
                if stdout.strip() != 'clean': 
                    self.log.warning('"getprop wd.volume.state" is not clean, wait for 30 secs and try again...')
                    time.sleep(30)
                else:
                    break
            else:
                raise self.err.TestFailure('"getprop wd.volume.state" is not clean.')

    def hdd_standby(self):
        for drive in self.ssh_client.get_sys_slot_drive():
            self.ssh_client.set_drive_standby(drive, wait_until_standby=True)
        # Dev suspects that ATA error may occur while disk changed from active -> idle -> wakeup.
        sleep_time = random.randint(30,60)
        self.log.warning("sleep at random from 30 to 60 seconds ({})".format(sleep_time))
        time.sleep(sleep_time)
        for drive in self.ssh_client.get_sys_slot_drive():
            result = self.ssh_client.get_drive_state(drive)
            if "drive state is:  standby" not in result:
                self.log.warning("HDD({}) is turned into {}.".format(drive, result))

    def check_device_vol_mount_opt(self):  # KDP-5449 [a few devices fail to set resgid to volume]
        device_vol_path = self.ssh_client.getprop(name='device.feature.vol.path')
        stdout, stderr = self.ssh_client.execute_cmd('mount | grep {} | grep -v docker'.format(device_vol_path))
        if 'resgid=990' not in stdout:
            raise self.err.TestFailure('"resgid=990" is not set successfully on mount option of device volume path({}).'.format(device_vol_path))

    def after_test(self):
        self.log.info("Reconnect SSH protocol after testing")
        self.ssh_client.connect()

    def after_loop(self):
        if self.fsck_happened_count > 0:
            raise self.err.TestFailure('Filesystem check happenend on normal reboot stess test, count: {}'
                                        .format(self.fsck_happened_count))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Device Reboot Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/reboot.py --uut_ip 10.92.224.68\
        """)

    parser.add_argument('-nowait', '--no_wait_device', help='Skip wait for device boot completed', action='store_true')
    parser.add_argument('-noapi', '--no_rest_api', help='Not use restapi to reboot device', action='store_true')
    parser.add_argument('-chkotapath', '--check_ota_image_path', help='raise error if ota download path changed', action='store_true')
    parser.add_argument('-norwchk', '--no_read_write_check', help='Do not run read write check after reboot', action='store_true')
    parser.add_argument('-chkpr', '--check_device_process_status', help='raise error if device process and status is not normal', action='store_true')
    parser.add_argument('-chkready', '--check_device_ready', help='raise error if device ready and proxyConnect value is false', action='store_true')
    parser.add_argument('-transtest', '--transcoding_test', help='Run transcoding test after device reboot', action='store_true')
    parser.add_argument('-sethddsby', '--set_hdd_standby', help='Set HDD of DUT standby before rebooting device', action='store_true')
    parser.add_argument('-ur', '--unsafe_reboot', help='Use reboot command to simulate power cycle the device', action='store_true')


    test = Reboot(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
