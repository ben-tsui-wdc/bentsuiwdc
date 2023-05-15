# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"
__compatible__ = 'KDP,RnD'

# std modules
import os
import re
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.restAPI import RestAPI

class RaidConversion(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-526 - raid_conversion'
    # Popcorn
    TEST_JIRA_ID = 'KDP-916,KDP-526,KDP-523,KDP-533'
    SETTINGS = { # Disable all utilities.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        self.raid_type = 'span,stripe,mirror'
        self.attach_owner = False
        self.restsdk_version = False
        self.timeout = 180

    def init(self):
        self.device_vol_path = self.ssh_client.getprop(name='device.feature.vol.path')

    def before_test(self):
        if self.uut.get('model') not in ['pelican2', 'drax']:
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(self.uut.get('model')))

    def test(self):
        self.raid_list = self.raid_type.split(",")
        for raid in self.raid_list:
            try:
                # Factory reset
                # To notify cloud that the device will be executed "factory_reset"
                if self.uut['model'] in ['drax']:
                    self.ssh_client.execute_background('system_event.sh eraseAllData {0}'.format(raid))
                elif self.uut['model'] in ['pelican2']:
                    self.ssh_client.execute_cmd('notify_cloud -s reset_button -n 136')
                    time.sleep(5)  # This is also used in "/usr/sbin/reset_button.sh" in device.
                    self.ssh_client.execute_background('factory_reset.sh {0}'.format(raid))
                if not self.ssh_client.wait_for_device_to_shutdown(timeout=60*30):
                    raise self.err.TestError('Device was not shut down successfully!')
                if not self.ssh_client.wait_for_device_boot_completed(timeout=60*10):
                    raise self.err.TestFailure('Device was not boot up successfully!')
                # stop otaclient
                self.ssh_client.lock_otaclient_service_kdp()
                # check sys.boot_completed
                self._reset_start_time()
                while True:
                    if self._is_timeout(self.timeout):
                        raise self.err.TestFailure("sys.boot_completed is not turned into 1 after {} seconds.".format(self.timeout))
                    else:
                        stdout, stderr = self.ssh_client.execute_cmd('getprop sys.boot_completed')
                        if '1' == stdout.strip():
                            self.log.info('"sys.boot_completed" is turned into 1.')
                            break
                        time.sleep(2)
                # check sys.wd.disk.mounted
                self._reset_start_time()
                while True:
                    if self._is_timeout(self.timeout):
                        raise self.err.TestFailure("sys.wd.disk.mounted is not turned into 1 after {} seconds.".format(self.timeout))
                    else:
                        stdout, stderr = self.ssh_client.execute_cmd('getprop sys.wd.disk.mounted')
                        if '1' == stdout.strip():
                            self.log.info('"sys.wd.disk.mounted" is turned into 1.')
                            break
                        time.sleep(2)
                # check if userStorage is mounted
                self._reset_start_time()
                while True:
                    if self._is_timeout(self.timeout):
                        raise self.err.TestFailure('{}/userStorage is not mounted after {} seconds.'.format(self.device_vol_path, self.timeout))
                    else:
                        stdout, stderr = self.ssh_client.execute_cmd('ls {}'.format(self.device_vol_path))
                        if all(i in stdout for i in ['kdpappmgr', 'restsdk', 'restsdk-info', 'userStorage']):
                            self.log.info('"{}/userStorage" is mounted.'.format(self.device_vol_path))
                            break
                        time.sleep(2)
                # check if raid level is the same as expectation.
                self.raid_type_check(raid=raid)
                # check if raid size is the same as expectation.
                self.raid_size_check(raid=raid)
                if self.attach_owner:
                    self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
                    self.uut_owner.id = 0  # Reset uut_owner.id
                    self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']})
                    self.log.warning('Attach owner after factory_reset.')
                if self.read_write_check:
                    if getattr(self, 'uut_owner'):
                        self.read_write_check_after_reboot()
                    else:
                        self.log.warning('uut_owner is False, skip the read_write_check_after_reboot')
            except Exception as ex:
                raise self.err.TestError('Failed to execute factory Reset due to {0}!'.format(ex))

    def raid_type_check(self, raid=None):
        stdout, stderr = self.ssh_client.execute_cmd('mdadm --detail  /dev/md1 | grep "Raid Level"')
        if raid == 'span':
            if 'linear' in stdout:
                self.log.warning('The device raid is span, which is the same as expectation.')
            else:
                raise self.err.TestFailure('raid was assigned "span", however, the device raid is {0}.'.format(stdout))
        elif raid == 'stripe':
            if 'raid0' in stdout:
                self.log.warning('The device raid is stripe, which is the same as expectation.')
            else:
                raise self.err.TestFailure('raid was assigned "stripe", however, the device raid is {0}.'.format(stdout))
        elif raid == 'mirror':
            if 'raid1' in stdout:
                self.log.warning('The device raid is mirror, which is the same as expectation.')
            else:
                raise self.err.TestFailure('raid was assigned "mirror", however, the device raid is {0}.'.format(stdout))

    def raid_size_check(self, raid=None):
        stdout, stderr = self.ssh_client.execute_cmd('mdadm --detail  /dev/md1')
        if len(re.findall('/dev/sd[a-z]\d', stdout)) != 2:
            raise self.err.StopTest('The number of disks in device is not equal to 2.')
        disk_1 = re.findall('/dev/sd[a-z]\d', stdout)[0]
        disk_2 = re.findall('/dev/sd[a-z]\d', stdout)[1]
        stdout, stderr = self.ssh_client.execute_cmd('sgdisk --print {0}; sgdisk --print {1}'.format(disk_1, disk_2))
        if re.search('Problem opening.*Error is 2.', stdout):
            raise self.err.StopTest('There is at least one disk that cannot be found on device.')
        else:
            # check disk size
            raw_disk_size_list = []
            for element in re.findall('sectors, .*TiB', stdout):
                raw_disk_size_list.append(float(element.split('sectors, ')[1].split(' TiB')[0]))  # Unit of size: TiB
            self.log.warning("raw_disk_size_list: {}".format(raw_disk_size_list))
            # check raid size
            stdout, stderr = self.ssh_client.execute_cmd('df -h {} | grep {}'.format(self.device_vol_path, self.device_vol_path))
            raid_size_actual = float(stdout.split()[1].split('T')[0])  # Unit of size: TiB
            self.log.warning("raid_size_actual:{}".format(raid_size_actual))
            if raid == 'span' or raid == "stripe":
                raid_size_expect = sum(raw_disk_size_list)
            elif raid == 'mirror':
                raid_size_expect = min(raw_disk_size_list)
            if 0.9 < raid_size_actual/raid_size_expect and raid_size_actual/raid_size_expect < 1.1:
                self.log.warning('The raid size is the same as expectation.')
            else:
                raise self.err.TestFailure('The raid size is not the same as expectation.')

    def _reset_start_time(self):
        self.start_time = time.time()

    def _is_timeout(self, timeout):
        return (time.time() - self.start_time) >= timeout

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
        user_roots_path = '{}/userStorage'.format(self.device_vol_path)
        nas_md5 = self.ssh_client.execute_cmd('busybox md5sum {0}/{1}/{2}'.
                                                format(user_roots_path, user_id, TEST_FILE), timeout=300, quiet=True)[0].split()[0]
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
        os.remove('{}'.format(TEST_FILE))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh kdp_scripts/functional_tests/raid_conversion.py --uut_ip 10.92.224.71 --dry_run --debug_middleware\
        """)
    parser.add_argument('--raid_type', help='The raid type to be tested. Multiple raid types can be used at the same time, separated by comma, for example: span,stripe,mirror. By default is span,stripe,mirror.', default='span,stripe,mirror')
    parser.add_argument('--attach_owner', help='attach owner after factory_reset', action='store_true')
    parser.add_argument('--read_write_check', help='run read write check after reboot', action='store_true')

    test = RaidConversion(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)