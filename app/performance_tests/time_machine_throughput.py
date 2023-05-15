# -*- coding: utf-8 -*-

# std modules
import os
import re
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.ssh_client import SSHClient

class time_machine_throughput(TestCase):
    TEST_SUITE = 'Performance_Tests'
    TEST_NAME = 'time_machine_throughput'
    # Popcorn
    TEST_JIRA_ID = 'KAM-21036,KAM-21037'


    SETTINGS = { # Disable all utilities.
        'disable_firmware_consistency': False,
        'adb': True, # Disbale ADB and ignore any relevant input argument.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }


    # Pre-defined parameters for IntegrationTest
    def declare(self):
        self.mac_server_ip = 'xxxxxxx'
        self.timeout = 7200


    def _check_tm_backup_status(self, mac_ssh):
        while True:
            print 'wait 2 seconds'
            time.sleep(2)            
            if mac_ssh.tm_backup_status().get('Running') == '0':
                self.log.info('tmutil backup finished.')
                break


    def _tm_prerequisite(self, mac_ssh):
        mac_ssh.unmount_folder('/Volumes/TimeMachineBackup', force=True)
        mac_ssh.create_folder('/Volumes/TimeMachineBackup')
        mac_ssh.mount_folder(self.protocol, self.env.uut_ip, 'TimeMachineBackup', '/Volumes/TimeMachineBackup')
        mac_ssh.tm_disable_autobackup()
        tm_dest = mac_ssh.tm_get_dest()
        if tm_dest:
            mac_ssh.tm_del_dest(tm_dest.get('ID'))
        mac_ssh.tm_set_dest('/Volumes/TimeMachineBackup')
        tm_dest = mac_ssh.tm_get_dest()
        if not tm_dest:
            self.err.StopTest('Failed to set tmutil destination')


    def _tm_start_backup(self, mac_ssh, pattern=None):
        print '\r\n ### startbackup in {} ### \r\n'.format(pattern)
        stdout, stderr = mac_ssh.tm_start_backup(block=True, time=True)  # block =True means that tmutil backup will be executed on foreground.
        print stdout, stderr
        # The unit of tm_throughput is MB/sec.
        tm_throughput = float(re.findall('Avg speed:    .+ MB/min', stdout)[0].split('Avg speed:    ')[1].split(' MB/min')[0])/60
        # The unit of tm_duration is second(s).
        tm_duration = float(re.findall('real\t\d+m.+s', stderr)[0].split('real\t')[1].split('m')[0]) * 60 + \
                      float(re.findall('real\t\d+m.+s', stderr)[0].split('m')[1].split('s')[0])
        
        return tm_throughput, tm_duration


    # main function
    def test(self):
        self.model = self.adb.getModel().strip()

        # exit_status, output = mac_ssh.execute('ifconfig')
        mac_ssh = SSHClient(self.mac_server_ip, self.mac_username, self.mac_password)
        mac_ssh.connect()

        # Clear out timemachine folder in NAS
        self.adb.executeShellCommand('rm -rf /data/wd/diskVolume0/backups/timemachine/*')
        
        # New backup
        self._tm_prerequisite(mac_ssh)
        #mac_ssh.tm_add_exclusion(path='/Volumes/My\ Book\ VelociRaptor\ Duo/42GBIncremental')
        mac_ssh.tm_add_exclusion(path=self.data_path)
        tm_throughput_newbackup, tm_duration_newbackup = self._tm_start_backup(mac_ssh, pattern='newbackup')
        self._check_tm_backup_status(mac_ssh)

        print "\r\nI can't figure out why although 'check tmutil status' passed, it still failed to \
execute 'tmutil startbakup' again. 'Umount time machinde folder' or 're-connect SSH session' \
can not work, either. The only effective way is 'sleep 120 seconds' between two times of 'tmutil startbakup'.\r\n"
        time.sleep(120)

        # Incremental backup
        self._tm_prerequisite(mac_ssh)
        #mac_ssh.tm_del_exclusion(path='/Volumes/My\ Book\ VelociRaptor\ Duo/42GBIncremental')
        mac_ssh.tm_del_exclusion(path=self.data_path)
        tm_throughput_incremental, tm_duration_incremental = self._tm_start_backup(mac_ssh, pattern='Incremental')
        self._check_tm_backup_status(mac_ssh)

        # This is the same as above.
        time.sleep(120)


        mac_ssh.close()

        self.data.test_result['testName'] = 'time_machine_KPI'
        self.data.test_result['model'] = self.model
        self.data.test_result['protocol'] = self.protocol
        self.data.test_result['tm_throughput_newbackup'] = tm_throughput_newbackup
        self.data.test_result['tm_duration_newbackup'] = tm_duration_newbackup
        self.data.test_result['tm_throughput_incremental'] = tm_throughput_incremental
        self.data.test_result['tm_duration_incremental'] = tm_duration_incremental
        self.data.test_result['wifi_mode'] = self.wifi_mode

if __name__ == '__main__':

    parser = InputArgumentParser("""\
        *** time_machine_throughput test on Kamino Android ***
        Examples: ./run.sh functional_tests/time_machine_throughput.py --uut_ip 10.92.224.71 \
        --mac_server_ip 10.92.224.26 --dry_run --debug_middleware\
        """)
    parser.add_argument('--mac_server_ip', help='mac_server_ip which is used to be as client.' , default='10.92.224.28')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='root')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac clientt', default='`1q')
    parser.add_argument('--protocol', help='protocol which is used to connect mac_server.', choices=['afp', 'smb'])
    parser.add_argument('--wifi_mode', help='type of wifi mode, by default is None', choices=['None','2.4G', '5G'], default='None')
    parser.add_argument('--data_path', help='the path of testing data', default='None')
    #For example: data_path = '/Volumes/My\ Book\ VelociRaptor\ Duo/42GBIncremental'
    # data_path='/Volumes/MyPassport'
    test = time_machine_throughput(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)