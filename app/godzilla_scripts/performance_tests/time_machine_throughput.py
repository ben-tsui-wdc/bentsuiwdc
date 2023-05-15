# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import os
import re
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.ssh_client import SSHClient
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat

# timemachibne backup requires root privileges of Mac.


class time_machine_throughput(GodzillaTestCase):
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
        self.timeout = 7200
        self.mac_mount_share = '/Volumes/mac_TimeMachineBackupKPI_mountpoint'
        self.time_shell_version = 'bash'
        # Popcorn
        self.VERSION= 'ExternalBeta0605'


    def _check_tm_backup_status(self):
        while True:
            print 'wait 2 seconds'
            time.sleep(2)            
            if self.mac_ssh.tm_backup_status().get('Running') == '0':
                self.log.info('tmutil backup finished.')
                break


    def _tm_prerequisite(self):
        self.mac_ssh.unmount_folder(self.mac_mount_share, force=True)
        self.mac_ssh.create_folder(self.mac_mount_share)
        self.mac_ssh.mount_folder(self.protocol, self.env.uut_ip, 'TimeMachineBackup', self.mac_mount_share)
        self.mac_ssh.tm_disable_autobackup()
        tm_dest = self.mac_ssh.tm_get_dest()
        if tm_dest:
            self.mac_ssh.tm_del_dest(tm_dest.get('ID'))
        self.mac_ssh.tm_set_dest(self.mac_mount_share)
        tm_dest = self.mac_ssh.tm_get_dest()
        if not tm_dest:
            self.err.StopTest('Failed to set tmutil destination')


    def _tm_start_backup(self, pattern=None):
        print '\r\n ### startbackup in {} ### \r\n'.format(pattern)
        tm_result = self.mac_ssh.tm_start_backup(block=True, time=True)  # block =True means that tmutil backup will be executed on foreground.
        print tm_result

        # The unit of tm_throughput is MB/sec.
        tm_throughput = float(re.findall('Avg speed:    .+ MB/min', tm_result)[0].split('Avg speed:    ')[1].split(' MB/min')[0])/60

        # The unit of tm_duration is second(s).
        tm_duration = None
        if self.time_shell_version == 'bash':
            tm_duration = float(re.findall('real\t\d+m.+s', tm_result)[0].split('real\t')[1].split('m')[0]) * 60 + \
                          float(re.findall('real\t\d+m.+s', tm_result)[0].split('m')[1].split('s')[0])
        elif self.time_shell_version == 'zsh':
            time_hms = tm_result.split('cpu')[1].split('total')[0].strip()
            for index, item in enumerate(list(reversed(time_hms.split(':')))):
                if index == 0:  # second
                    tm_duration = float(item)
                elif index == 1:  # minute
                    tm_duration += float(item) * 60
                elif index == 2:  # hour
                    tm_duration += float(item) * 3600
        elif self.time_shell_version == 'gnu':
            # Maybe need to do in the future.
            pass

        return tm_throughput, tm_duration


    def before_loop(self):        
        self.mac_ssh = SSHClient(self.mac_server_ip, self.mac_username, self.mac_password)
        self.mac_ssh.connect()
        #exit_status, output = self.mac_ssh.execute('ifconfig')


    def before_test(self):
        # Clear out timemachine folder in GZA device
        self.ssh_client.execute_cmd('rm -rf /mnt/HD/HD_a2/TimeMachineBackup/*')

        # To confirm what version of "time" used in MacOS's shell
        # Reference: https://linuxize.com/post/linux-time-command/
        exit_status, output = self.mac_ssh.execute('type time')
        if "time is a shell keyword" in output:
            # Bash
            self.time_shell_version = "bash"
        elif "time is a reserved word" in output:
            # Zsh
            self.time_shell_version = "zsh"
        elif "time is /usr/bin/time" in output:
            # GNU time (sh)
            self.time_shell_version = "gnu"
        print "self.time_shell_version: {}".format(self.time_shell_version)

        # workaround for tmuitl bug of MacOS 10.15
        # Becasue all folder will be excluded by default by MacOS 10.15
        self.mac_ssh.tm_del_exclusion(path='/'.join(self.data_path.split('/')[:-1]))


    # main function
    def test(self):
        # New backup
        self._tm_prerequisite()
        #self.mac_ssh.tm_add_exclusion(path='/Volumes/My\ Book\ VelociRaptor\ Duo/42GBIncremental')
        self.mac_ssh.tm_add_exclusion(path=self.data_path)
        tm_throughput_newbackup, tm_duration_newbackup = self._tm_start_backup(pattern='newbackup')
        self._check_tm_backup_status()

        print "\r\nI can't figure out why although 'check tmutil status' passed, it still failed to \
execute 'tmutil startbakup' again. 'Umount time machinde folder' or 're-connect SSH session' \
can not work, either. The only effective way is 'sleep 120 seconds' between two times of 'tmutil startbakup'.\r\n"
        time.sleep(120)

        # Incremental backup
        self._tm_prerequisite()
        #self.mac_ssh.tm_del_exclusion(path='/Volumes/My\ Book\ VelociRaptor\ Duo/42GBIncremental')
        self.mac_ssh.tm_del_exclusion(path=self.data_path)
        tm_throughput_incremental, tm_duration_incremental = self._tm_start_backup(pattern='Incremental')
        self._check_tm_backup_status()
        # This is the same as above.
        time.sleep(120)

        self.data.test_result['testName'] = 'time_machine_KPI'
        self.data.test_result['Protocol'] = self.protocol.upper()
        self.data.test_result['NewbackupThroughput'] = '{:.1f}'.format(tm_throughput_newbackup)
        self.data.test_result['NewbackupDuration'] = '{:.1f}'.format(tm_duration_newbackup)
        self.data.test_result['IncrementalThroughput'] = '{:.1f}'.format(tm_throughput_incremental)
        self.data.test_result['IncrementalDuration'] = '{:.1f}'.format(tm_duration_incremental)


    def after_test(self):
        self.test_result_list.append(self.data.test_result)


    def after_loop(self):
        self.mac_ssh.close()

        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'Protocol', 'iteration', 'NewbackupThroughput', 'NewbackupDuration', 'IncrementalThroughput', 'IncrementalDuration']
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'build', 'Protocol', 'iteration', 'NewbackupThroughput', 'NewbackupDuration', 'IncrementalThroughput', 'IncrementalDuration']
        csv_inst.csv_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)


if __name__ == '__main__':

    parser = GodzillaInputArgumentParser("""\
        *** time_machine_throughput test on Kamino Android ***
        Examples: ./run.sh functional_tests/time_machine_throughput.py --uut_ip 10.92.224.71 \
        --mac_server_ip 10.92.224.26 --dry_run --debug_middleware\
        """)
    parser.add_argument('--mac_server_ip', help='mac_server_ip which is used to be as client.' , default='192.168.0.19')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='root')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac clientt', default='root')
    parser.add_argument('--protocol', help='protocol which is used to connect mac_server.', choices=['afp', 'smb'], default='afp')
    parser.add_argument('--data_path', help='the path of testing data', default='/Volumes/KPI/NewSmallTMOSDataSet0')

    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    #For example: data_path = '/Volumes/My\ Book\ VelociRaptor\ Duo/42GBIncremental'
    # data_path='/Volumes/MyPassport'
    test = time_machine_throughput(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)