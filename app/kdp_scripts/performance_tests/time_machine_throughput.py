# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import os
import re
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.restAPI import RestAPI
from platform_libraries.nasadmin_client import NasAdminClient
from platform_libraries.ssh_client import SSHClient
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat

# timemachibne backup requires root privileges of Mac.


class time_machine_throughput(KDPTestCase):
    TEST_SUITE = 'Performance_Tests'
    TEST_NAME = 'time_machine_throughput'
    # Popcorn
    TEST_JIRA_ID = ''

    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True
    }


    # Pre-defined parameters for IntegrationTest
    def declare(self):
        self.html_format = '2'
        self.test_result_list = []
        self.mac_server_ip = 'xxxxxxx'
        self.mac_mount_share = '/Volumes/mac_TimeMachineBackupKPI_mountpoint'   # on mac client
        self.time_shell_version = 'bash'
        # Popcorn
        self.VERSION = 'ExternalBeta0605'
        self.timeout = 10800  # 3hrs


    def init(self):
        if self.uut['model'] in ['rocket', 'drax']:
            self.nasadmin_username = 'owner'
            self.nasadmin_password = 'password'
            self.specific_folder = 'TimeMachineBackupUUT'   # on UUT
        else:
            self.nasadmin_username = ''
            self.nasadmin_password = ''
            self.specific_folder = 'TimeMachineBackup'   # on UUT


    def before_loop(self):        
        self.mac_ssh = SSHClient(self.mac_server_ip, self.mac_username, self.mac_password)
        self.mac_ssh.connect()
        #exit_status, output = self.mac_ssh.execute('ifconfig')


    def before_test(self):
        if self.uut['model'] in ['rocket', 'drax']:
            self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
            self.uut_owner.update_device_ip(self.env.uut_ip)
            if self.env.cloud_env == 'prod':
                with_cloud_connected = False
            else:
                with_cloud_connected = True
            self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']}, with_cloud_connected=with_cloud_connected)
            nasadmin_client = NasAdminClient(self.env.uut_ip, rest_client=self.uut_owner)
            # Wait for restsdk aknowledging nasadmin that the owner is attached to UUT.
            if not nasadmin_client.wait_for_nasAdmin_works():
                raise self.err.TestError("nasAdmin does't work")
            if not nasadmin_client.is_owner_attached_restsdk():
                raise self.err.TestError("First user is not attached by RestSDK.")
            if not nasadmin_client.wait_for_owner_attached():
                raise self.err.TestError("Owner isn't attached by nasadmin.")
            # Delete the share(space) of TimeMachineBackup if exists.
            for space in nasadmin_client.get_spaces():
                if space['name'] == self.specific_folder:
                    nasadmin_client.delete_spaces(space['id'])
                    break
            # Create share(space) of TimeMachineBackup by nasadmin on rocket/drax
            space = nasadmin_client.create_space(name=self.specific_folder, allUsers=True, localPublic=False, timeMachine=True)
            nasadmin_users = nasadmin_client.get_users()
            for user in nasadmin_users:
                if user.get('cloudID') == self.uut_owner.get_user_id():
                    nasadmin_user = user
                    break
            self.log.warning('nasadmin_user:{}'.format(nasadmin_user))
            nasadmin_client.update_user(nasadmin_user['id'], localAccess=True, username=self.nasadmin_username, password=self.nasadmin_password)
        else:
            self.ssh_client.execute_cmd('rm -rf /data/wd/diskVolume0/backups/timemachine/*')

        # To acquire the version of macOS
        stdout, stderr = self.mac_ssh.execute_cmd('sw_vers | grep -i  productversion')
        self.macos_version = stdout.split()[1].strip()

        # To confirm what version of "time" used in MacOS's shell
        # Reference: https://linuxize.com/post/linux-time-command/
        stdout, stderr = self.mac_ssh.execute_cmd('type time')
        if "time is a shell keyword" in stdout:
            # Bash
            self.time_shell_version = "bash"
        elif "time is a reserved word" in stdout:
            # Zsh
            self.time_shell_version = "zsh"
        elif "time is /usr/bin/time" in stdout:
            # GNU time (sh)
            self.time_shell_version = "gnu"
        self.log.info("self.time_shell_version: {}".format(self.time_shell_version))
        # workaround for tmuitl bug of MacOS 10.15
        # Becasue all folder will be excluded by default by MacOS 10.15
        self.mac_ssh.tm_del_exclusion(path='/'.join(self.data_path.split('/')[:-1]))


    def test(self):
        # New backup
        self._tm_prerequisite()
        #self.mac_ssh.tm_add_exclusion(path='/Volumes/My\ Book\ VelociRaptor\ Duo/42GBIncremental')
        self.mac_ssh.tm_add_exclusion(path=self.data_path)
        self.log.warning("Wait for 60 seconds after adding data_path to TimeMachineBackup exclusion")
        time.sleep(60)

        tm_throughput_newbackup, tm_duration_newbackup, tm_totalMBs_newbackup = self._tm_start_backup(pattern='newbackup')
        self._check_tm_backup_status()

        print "\r\nI can't figure out why although 'check tmutil status' passed, it still failed to \
execute 'tmutil startbakup' again. 'Umount time machinde folder' or 're-connect SSH session' \
can not work, either. The only effective way is 'sleep 120 seconds' between two times of 'tmutil startbakup'.\r\n"
        time.sleep(120)

        # Incremental backup
        self._tm_prerequisite()
        #self.mac_ssh.tm_del_exclusion(path='/Volumes/My\ Book\ VelociRaptor\ Duo/42GBIncremental')
        self.mac_ssh.tm_del_exclusion(path=self.data_path)
        self.log.warning("Wait for 60 seconds after deleting data_path from TimeMachineBackup exclusion")
        time.sleep(60)

        tm_throughput_incremental, tm_duration_incremental, tm_totalMBs_incremental = self._tm_start_backup(pattern='Incremental')
        self._check_tm_backup_status()
        # This is the same as above.
        time.sleep(120)

        self.data.test_result['testName'] = 'time_machine_KPI'
        self.data.test_result['Protocol'] = self.protocol.upper()
        self.data.test_result['NewbackupThroughput_avg'] = '{:.1f}'.format(tm_throughput_newbackup)
        self.data.test_result['NewbackupDuration_avg'] = '{:.1f}'.format(tm_duration_newbackup)
        self.data.test_result['NewbackupTotalMBs'] = '{:.1f} MB'.format(tm_totalMBs_newbackup)
        self.data.test_result['IncrementalThroughput_avg'] = '{:.1f}'.format(tm_throughput_incremental)
        self.data.test_result['IncrementalDuration_avg'] = '{:.1f}'.format(tm_duration_incremental)
        self.data.test_result['IncrementalTotalMBs'] = '{:.1f} MB'.format(tm_totalMBs_incremental)
        # For Popcorn
        self.data.test_result['NewbackupThroughput_unit'] = 'Mbps'
        self.data.test_result['NewbackupDuration_unit'] = 'sec'
        self.data.test_result['IncrementalThroughput_unit'] = 'Mbps'
        self.data.test_result['IncrementalDuration_unit'] = 'sec'
        self.data.test_result['macOS'] = self.macos_version
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # millisecond


    def after_test(self):
        self.test_result_list.append(self.data.test_result)


    def after_loop(self):
        self.mac_ssh.close()

        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'macOS', 'Protocol', 'iteration', 'NewbackupThroughput_avg', 'NewbackupThroughput_unit' ,'NewbackupDuration_avg', 'NewbackupDuration_unit', 'NewbackupTotalMBs', 'IncrementalThroughput_avg', 'IncrementalThroughput_unit', 'IncrementalDuration_avg', 'IncrementalDuration_unit', 'IncrementalTotalMBs']
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'build', 'macOS', 'Protocol', 'NewbackupThroughput_avg', 'NewbackupThroughput_unit' ,'NewbackupDuration_avg', 'NewbackupDuration_unit', 'IncrementalThroughput_avg', 'IncrementalThroughput_unit', 'IncrementalDuration_avg', 'IncrementalDuration_unit',
        'count', 'executionTime']
        csv_inst.csv_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)


    def _check_tm_backup_status(self):
        self.timing.reset_start_time()
        while not self.timing.is_timeout(self.timeout):
            self.log.info('wait 2 seconds')
            time.sleep(2)            
            if self.mac_ssh.tm_backup_status().get('Running') == '0':
                self.log.info('tmutil backup finished.')
                break


    def _tm_prerequisite(self):
        self.mac_ssh.unmount_folder(self.mac_mount_share, force=True)
        self.mac_ssh.create_folder(self.mac_mount_share)
        self.mac_ssh.mount_folder(self.protocol, self.env.uut_ip, self.specific_folder, self.mac_mount_share, username=self.nasadmin_username, password=self.nasadmin_password)
        self.mac_ssh.tm_disable_autobackup()
        tm_dest = self.mac_ssh.tm_get_dest()
        if tm_dest:
            self.mac_ssh.tm_del_dest(tm_dest.get('ID'))
        self.mac_ssh.tm_set_dest(self.mac_mount_share)
        tm_dest = self.mac_ssh.tm_get_dest()
        if not tm_dest:
            self.err.StopTest('Failed to set tmutil destination')


    def _tm_start_backup(self, pattern=None):
        for i in xrange(3):
            self.log.info('\r\n ### startbackup in {}. Iteration: {} ### \r\n'.format(pattern, i))
            tm_result = ''
            tm_result = self.mac_ssh.tm_start_backup(block=False, time=True)  # block =True means that tmutil backup will be executed in the foreground.
            self.log.info("start_backup result. Iteration: {}".format(i))
            self.log.warning(tm_result)
            if "XPC error for connection com.apple.backupd.xpc: Connection interrupted" in tm_result:
                time.sleep(30)
            else:
                break
        start_time = time.time()
        self.timing.reset_start_time()
        while not self.timing.is_timeout(self.timeout):
            time.sleep(5)
            result  = self.mac_ssh.tm_backup_status()
            if result.get("bytes"):
                backup_totalbytes = result.get("bytes")
            backup_percent = result.get("Percent")
            print 'backup_percent: {}'.format(backup_percent)
            if backup_percent != "1":
                print "backup_percent is not 1. TimeMachineBackup is still in progress."
            else:
                self.log.info("backup_percent is 1.")
                self.log.info("TimeMachineBackup is going to be completed.")
                # To ensure TimeMachineBackup finished completely.
                self._check_tm_backup_status()
                tm_duration = time.time() - start_time
                tm_totalMBs = float(backup_totalbytes)/1024/1024  # bytes -> MB
                tm_throughput = tm_totalMBs/float(tm_duration)  
                self.log.info("tm_duration: {}sec, tm_throughput:{}MB/s".format(tm_duration, tm_throughput))
                return tm_throughput, tm_duration, tm_totalMBs


if __name__ == '__main__':

    parser = KDPInputArgumentParser("""\
        *** time_machine_throughput test on Kamino Android ***
        Examples: ./run.sh functional_tests/time_machine_throughput.py --uut_ip 10.92.224.71 \
        --mac_server_ip 10.92.224.26 --dry_run --debug_middleware\
        """)
    parser.add_argument('--mac_server_ip', help='mac_server_ip which is used to be as client.' , default='192.168.0.43')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='root')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac clientt', default='root')
    parser.add_argument('--protocol', help='protocol which is used to connect mac_server.', choices=['afp', 'smb'], default='smb')
    parser.add_argument('--data_path', help='the path of testing data', default='/Volumes/MyPassport/42GBIncremental')
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--specific_folder', help='folder of TimeMachineBackup in UUT', default='TimeMachineBackupUUT')
    #For example: data_path = '/Volumes/My\ Book\ VelociRaptor\ Duo/42GBIncremental'
    # data_path='/Volumes/MyPassport'
    test = time_machine_throughput(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)

