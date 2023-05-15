# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import os
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.inventoryAPI import InventoryAPI, InventoryException
from platform_libraries.ssh_client import SSHClient

class TimeMachineBackupRestore(TestCase):

    """
        Pre-configuration on the MAC OS:
        1. Need to enable root user since most of tmutil command need root permission:
           a. https://support.apple.com/en-us/HT204012
           b. sudo vim /etc/ssh/sshd_config and set "PermitRootLogin yes"
        2. Need to install wget by brew first to download test files from file server:
           a. ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
           b. brew install wget --with-libressl

           http://stackoverflow.com/questions/33886917/how-to-install-wget-in-macos-capitan-sierra
    """

    TEST_SUITE = 'Time_Machine_Tests'
    TEST_NAME = 'Time_Machine_Backup_Restore_Test'
    # Popcorn
    TEST_JIRA_ID = 'KAM-20954'
    REPORT_NAME = 'Stress'

    SETTINGS = {
        'uut_owner' : False # Disbale restAPI.
    }
    FOLDER_TO_BACKUP = '/KAT_TM_TEST'
    LOCAL_MOUNT_PATH = '/Volumes/TimeMachineBackup'
    LOCAL_RESTORE_PATH = '/Volumes/Time Machine Backups'  # Defined by MAC OS
    FILE_SERVER_PATH = '/test/USBSlurp'
    FILE_LIST = []
    FILE_MD5_DICT = dict()
    MAX_RETRIES = 10


    # Pre-defined parameters for IntegrationTest
    def declare(self):
        self.server_ip = ''
        self.mac_os = ''


    def init(self):
        self.device_in_inventory = None
        self.test_failed = False
        if not self.server_ip:
            self.inventory = InventoryAPI('http://{}:8010/InventoryServer'.format(self.inventory_server_ip), debug=True)
            self.device_in_inventory = self._checkout_device(uut_platform='mac-client', firmware=self.mac_os)
            if self.device_in_inventory:
                self.server_ip = self.device_in_inventory.get('internalIPAddress')
            else:
                raise self.err.TestSkipped('There is no spare mac client can be checked out from Inventory Server.')

        self.ssh = SSHClient(self.server_ip, self.server_username, self.server_password)

    def before_test(self):
        self.log.info('[ Run before_test step ]')
        pass

    def _get_checksum_dict(self, path, file_list):
        checksum_dict = dict()
        for file in file_list:
            md5 = self.ssh.get_file_checksum("{}/{}".format(path, file))
            if md5:
                checksum_dict[file] = md5
            else:
                raise self.err.StopTest("Failed to get md5 checksum of file: {}".format(file))

        return checksum_dict

    def test(self):

        def _compare_files(file_list):
            # compare if the file numbers and file names are the same
            if len(self.FILE_LIST) == len(file_list) and \
               len(list(set(self.FILE_LIST).intersection(file_list))) == len(self.FILE_LIST):
                self.log.info("File names comparison passed")
                return True
            else:
                diff = list(set(self.FILE_LIST) ^ set(file_list))
                self.log.error("File names comparison failed! The different files: {}".format(diff))
                return False

        def _compare_md5_checksum(checksum_dict):
            # compare the checksum
            diff = list(file for file in self.FILE_MD5_DICT.keys() \
                        if self.FILE_MD5_DICT.get(file) != checksum_dict.get(file))
            if not diff:
                self.log.info("MD5 checksum comparison passed")
                return True
            else:
                self.log.error("MD5 checksum comparison failed! The different files:")
                for file in diff:
                    self.log.error("{}: md5 before [{}], md5 after [{}]".
                                   format(file, self.FILE_MD5_DICT[file], checksum_dict[file]))
                return False

        # Setup the initial test status
        backup_result = 'Passed'
        restore_result = 'Passed'

        dest_info = self.ssh.tm_get_dest()
        dest_id = dest_info.get('ID')
        if dest_id:
            self.log.info("Start to run time machine backup on dest id: {}".format(dest_id))
            self.ssh.tm_start_backup(dest_id)
        else:
            raise self.err.StopTest('Cannot get dest information!')

        time.sleep(5)  # wait for 5 secs after starting backup

        # Polling to check if the back process is complete
        timer = 86400 * 2
        while timer >= 0:
            backup_status = self.ssh.tm_backup_status()
            run_status = backup_status.get('Running')
            if run_status is '0':
                self.log.info("Backup status: Complete")
                break
            else:
                backup_phase = backup_status.get('BackupPhase')
                self.log.info("Backup status: {}".format(backup_phase))

            time.sleep(10)
            timer -= 10
            if timer < 0:
                self.log.warning("Time's up! TimeMachineBackup doesn't finish in {} seconds.".format(timer))

        time.sleep(10)  # wait for 10 secs after backup finish

        retry = self.MAX_RETRIES
        while retry >= 0:
            lateat_backup_folder = self.ssh.tm_latest_backup()
            if 'failed' in lateat_backup_folder:
                if retry == 0:
                    self.log.error("Reaching maxinum retries, failed to get latest backup info")
                    backup_result = 'Failed'
                    restore_result = 'Failed'
                    break

                self.log.warning("Failed to get latest backup info, remaining {} retries".format(retry))
                time.sleep(10)
                retry -= 1
            else:
                break

        if 'failed' not in lateat_backup_folder:
            path = "{}/{}/{}".format(lateat_backup_folder, self.mac_root_folder, self.FOLDER_TO_BACKUP)
            path = path.replace(" ", "\ ")
            # print path
            backup_file_list = self.ssh.get_file_list(path)
            if not _compare_files(backup_file_list):
                backup_result = 'Failed'

            backup_md5_dict = self._get_checksum_dict(path, backup_file_list)
            if not _compare_md5_checksum(backup_md5_dict):
                backup_result = 'Failed'

            # Remove all the source files and then test restore function
            self.ssh.delete_folder(self.FOLDER_TO_BACKUP)
            self.ssh.tm_restore(path, self.FOLDER_TO_BACKUP)

            restore_file_list = self.ssh.get_file_list(self.FOLDER_TO_BACKUP)
            if not _compare_files(restore_file_list):
                restore_result = 'Failed'

            restore_md5_dict = self._get_checksum_dict(path, restore_file_list)
            if not _compare_md5_checksum(restore_md5_dict):
                restore_result = 'Failed'

        self.log.info("Backup result: {}".format(backup_result))
        self.log.info("Restore result: {}".format(restore_result))

        self.data.test_result['TimeMachineBackup'] = backup_result
        self.data.test_result['TimeMachineRestore'] = restore_result
        self.data.test_result['Protocol'] = self.protocol_type

        if backup_result == 'Failed' or restore_result == 'Failed':
            self.test_failed = True

    def after_test(self):
        self.log.info('[ Run after_test step ]')
        pass

    def before_loop(self):
        self.log.info('[ Run before_loop step ]')
        self.ssh.connect()

        self.log.info("Setting up the test folders and files...")

        if self.ssh.check_folder_exist(self.FOLDER_TO_BACKUP):
            self.log.info("The backup folder already exist, delete it")
            self.ssh.delete_folder(self.FOLDER_TO_BACKUP)
        self.ssh.create_folder(self.FOLDER_TO_BACKUP)

        self.log.info("Download test files from file server to local backup folder")
        download_path = '{0}{1}'.format('ftp://ftp:ftppw@{}'.format(self.file_server), self.FILE_SERVER_PATH)
        cur_dir = self.FILE_SERVER_PATH.count('/')
        # Todo: the wget will show stderr if not -q (quiet), why??
        url = '/usr/local/bin/wget -q --no-host-directories --cut-dirs={0} -r {1} -P {2}'.format(cur_dir, download_path, self.FOLDER_TO_BACKUP)
        self.ssh.execute(url, timeout=1800)

        result = self.ssh.get_file_list(self.FOLDER_TO_BACKUP)
        if result:
            self.FILE_LIST = result

        self.FILE_MD5_DICT = self._get_checksum_dict(self.FOLDER_TO_BACKUP, self.FILE_LIST)
        self.log.info("Setting up time machine environment...")
        self.ssh.tm_disable_autobackup()
        result = self.ssh.tm_get_dest()
        if result:
            dest_id = result.get('ID')
            self.ssh.tm_del_dest(dest_id)

        if self.ssh.check_folder_mounted(self.LOCAL_MOUNT_PATH):
            self.log.warning("Folder: {} is already mounted before".format(self.LOCAL_MOUNT_PATH))
            self.ssh.unmount_folder(self.LOCAL_MOUNT_PATH, force=True)

        """ If the folder is unmounted, it will be also be deleted
        if self.ssh.check_folder_exist(self.LOCAL_MOUNT_PATH):
            self.log.warning("Folder: {} is already exist".format(self.LOCAL_MOUNT_PATH))
            self.ssh.delete_folder(self.LOCAL_MOUNT_PATH)
        """

        # Todo: Exclude some folders will get -50 error code, exclude them manually now (only need to set once)
        """
        exclude_list = ['/Applications', '/Library', '/Users', '/System', '/private']
        for exclude_item in exclude_list:
            self.ssh.tm_add_exclusion(exclude_item)
        """
        self.ssh.create_folder(self.LOCAL_MOUNT_PATH)
        self.ssh.mount_folder(self.protocol_type, self.env.uut_ip, "TimeMachineBackup", self.LOCAL_MOUNT_PATH)
        self.ssh.tm_set_dest(self.LOCAL_MOUNT_PATH)

    def after_loop(self):
        self.log.info('[ Run after_loop step ]')
        self.ssh.close()
        if self.device_in_inventory:
            self._checkin_device()

        if self.test_failed:
            raise self.err.TestFailure('Time Machine Backup and Restore Failed!')


    def _checkout_device(self, device_ip=None, uut_platform=None, firmware=None):
        jenkins_job = '{0}-{1}-{2}'.format(os.getenv('JOB_NAME', ''), os.getenv('BUILD_NUMBER', ''), self.__class__.__name__) # Values auto set by jenkins.
        if device_ip: # Device IP has first priority to use.
            self.log.info('Check out a device with IP: {}.'.format(device_ip))
            device = self.inventory.device.get_device_by_ip(device_ip)
            if not device:
                raise self.err.StopTest('Failed to find out the device with specified IP.')
            checkout_device = self.inventory.device.check_out(device['id'], jenkins_job, force=False)
        elif uut_platform: # Find device with matching below conditions.
            self.log.info('Looking for a available device.')
            checkout_device = self.inventory.device.matching_check_out_retry(
                uut_platform, tag='', firmware=firmware, variant='', environment='', uboot='',
                location='', site='', jenkins_job=jenkins_job, retry_counts=24,
                retry_delay=300, force=False
            )
            # retry_delay 180 seconds, retry_count 120 times.
        else:
            raise self.err.StopTest('Device Platform or Device IP is required.')
        return checkout_device

    def _checkin_device(self):
        if not self.inventory.device.check_in(self.device_in_inventory['id'], is_operational=True):
            raise self.err.StopTest('Failed to check in the device.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Time Machine Backup Restore test on Kamino Android ***
        Examples: ./run.sh  --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-pr', '--protocol_type', help="", default='afp', choices=['afp', 'smb'])
    parser.add_argument('-sip', '--server_ip', help='Server IP address', metavar='IP', default='')
    parser.add_argument('-isip', '--inventory_server_ip', help='inventory_server_ip', default='sevtw-inventory-server.hgst.com')
    parser.add_argument('-mo', '--mac_os', help='mac operating system verison', default='')
    parser.add_argument('-fb', '--folder_to_backup', help='The folder time machine will backup')
    parser.add_argument('-mp', '--mount_point', help='Local mount point', default='/Volumes/TimeMachineBackup')
    parser.add_argument('-mrf', '--mac_root_folder', help='MAC ROOT FOLDER ', default='Macintosh HD')
    

    parser.add_argument('-su', '--server_username', help='Server ssh username', default='root')
    parser.add_argument('-sp', '--server_password', help='Server ssh password', default='`1q')
    parser.add_argument('-fs', '--file_server', help='File server IP address for Mac client, only for MV-Warrior', default='10.200.141.26')

    test = TimeMachineBackupRestore(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)