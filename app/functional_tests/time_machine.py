# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import os
import re
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.inventoryAPI import InventoryAPI, InventoryException
from platform_libraries.ssh_client import SSHClient


class TimeMachine(TestCase):
    TEST_SUITE = 'Performance_Tests'
    TEST_NAME = 'time_machine_throughput'
    # Popcorn
    TEST_JIRA_ID = 'KAM-7070'

    SETTINGS = { # Disable all utilities.
        'disable_firmware_consistency': False,
        'adb': True, # Disbale ADB and ignore any relevant input argument.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }


    # Pre-defined parameters for IntegrationTest
    def declare(self):
        self.mac_server_ip = 'xxxxxxx'
        self.mac_os = ''
        self.timeout = 7200


    def init(self):
        self.inventory = InventoryAPI('http://{}:8010/InventoryServer'.format(self.inventory_server_ip), debug=True)
        self.device_in_inventory = None

    def before_test(self):
        self.log.info('[ Run before_test step ]')
        self.device_in_inventory = self._checkout_device(uut_platform='mac-client', firmware=self.mac_os)
        if self.device_in_inventory:
            self.mac_server_ip = self.device_in_inventory.get('internalIPAddress')
        else:
            raise self.err.TestSkipped('There is no spare mac client can be checked out from Inventory Server.')

        print '\n\n111111111111111111111111111\n\n'
        print self.mac_server_ip
        print self.mac_username
        print self.mac_password
        print self.backup_pattern
        print self.data_path
        print '\n\n111111111111111111111111111\n\n'

        self.mac_ssh = SSHClient(self.mac_server_ip, self.mac_username, self.mac_password)
        self.mac_ssh.connect()
        self.mac_ssh.tm_add_exclusion(path='/KAT_TM_TEST')  # This is because the Mac client is also used by tm_machine_stress.


    # main function
    def test(self):
        self.model = self.adb.getModel().strip()

        if self.backup_pattern == 'newbackup':
            # Clear out timemachine folder in NAS
            self.adb.executeShellCommand('rm -rf /data/wd/diskVolume0/backups/timemachine/*')
            
            # New backup
            self._tm_prerequisite()
            self.mac_ssh.tm_add_exclusion(path=self.data_path)
            tm_throughput_newbackup, tm_duration_newbackup = self._tm_start_backup()
            self._check_tm_backup_status()

            print "\r\nI can't figure out why although 'check tmutil status' passed, it still failed to \
    execute 'tmutil startbakup' again. 'Umount time machinde folder' or 're-connect SSH session' \
    can not work, either. The only effective way is 'sleep 30 seconds' between two times of 'tmutil startbakup'.\r\n"
            time.sleep(30)

        elif self.backup_pattern == 'incremental':
            # Incremental backup
            self._tm_prerequisite()
            self.mac_ssh.tm_del_exclusion(path=self.data_path)
            tm_throughput_incremental, tm_duration_incremental = self._tm_start_backup()
            self._check_tm_backup_status()

            print "\r\nI can't figure out why although 'check tmutil status' passed, it still failed to \
    execute 'tmutil startbakup' again. 'Umount time machinde folder' or 're-connect SSH session' \
    can not work, either. The only effective way is 'sleep 30 seconds' between two times of 'tmutil startbakup'.\r\n"
            time.sleep(30)

        '''
        self.data.test_result['testName'] = 'time_machine_KPI'
        self.data.test_result['model'] = self.model
        self.data.test_result['protocol'] = self.protocol
        self.data.test_result['tm_throughput_newbackup'] = tm_throughput_newbackup
        self.data.test_result['tm_duration_newbackup'] = tm_duration_newbackup
        self.data.test_result['tm_throughput_incremental'] = tm_throughput_incremental
        self.data.test_result['tm_duration_incremental'] = tm_duration_incremental
        self.data.test_result['wifi_mode'] = self.wifi_mode
        '''

    def after_test(self): 
        self.log.info('[ Run after_test step ]')
        self.mac_ssh.tm_del_exclusion(path='/KAT_TM_TEST')  # This is because the Mac client is also used by tm_machine_stress.
        self.mac_ssh.close()
        self._checkin_device()


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


    def _check_tm_backup_status(self):
        while True:
            print 'wait 2 seconds'
            time.sleep(2)            
            if self.mac_ssh.tm_backup_status().get('Running') == '0':
                self.log.info('tmutil backup finished.')
                break


    def _tm_prerequisite(self):
        self.mac_ssh.unmount_folder('/Volumes/TimeMachineBackup', force=True)
        self.mac_ssh.create_folder('/Volumes/TimeMachineBackup')
        self.mac_ssh.mount_folder(self.protocol, self.env.uut_ip, 'TimeMachineBackup', '/Volumes/TimeMachineBackup')
        self.mac_ssh.tm_disable_autobackup()
        tm_dest = self.mac_ssh.tm_get_dest()
        if tm_dest:
            self.mac_ssh.tm_del_dest(tm_dest.get('ID'))
        self.mac_ssh.tm_set_dest('/Volumes/TimeMachineBackup')
        tm_dest = self.mac_ssh.tm_get_dest()
        if not tm_dest:
            raise self.err.StopTest('Failed to set tmutil destination')


    def _tm_start_backup(self):
        print '\r\n ### startbackup in {} ### \r\n'.format(self.backup_pattern)
        for i in xrange(3):
            tm_result = ''
            tm_result = self.mac_ssh.tm_start_backup(block=True, time=True)  # block =True means that tmutil backup will be executed in the foreground.
            print "start_backup result. Iteration: {}".format(i)
            print tm_result
            if "XPC error for connection com.apple.backupd.xpc: Connection interrupted" in tm_result:
                time.sleep(30)
            else:
                break
        # The unit of tm_throughput is MB/sec.
        tm_throughput = float(re.findall('Avg speed:    .+ MB/min', tm_result)[0].split('Avg speed:    ')[1].split(' MB/min')[0])/60
        # The unit of tm_throughput is second(s).
        tm_duration = float(re.findall('real\t\d+m.+s', tm_result)[0].split('real\t')[1].split('m')[0]) * 60 + \
                      float(re.findall('real\t\d+m.+s', tm_result)[0].split('m')[1].split('s')[0])
        return tm_throughput, tm_duration



if __name__ == '__main__':

    parser = InputArgumentParser("""\
        *** time_machine_throughput test on Kamino Android ***
        Examples: ./run.sh functional_tests/time_machine_throughput.py --uut_ip 10.92.224.71 \
        --mac_server_ip 10.92.224.26 --dry_run --debug_middleware\
        """)
    parser.add_argument('--inventory_server_ip', help='inventory_server_ip', default='sevtw-inventory-server.hgst.com')
    parser.add_argument('--mac_os', help='mac operating system verison', default='')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='root')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac client', default='`1q')
    parser.add_argument('--protocol', help='protocol which is used to connect mac_server.', choices=['afp', 'smb'])
    parser.add_argument('--wifi_mode', help='type of wifi mode, by default is None', choices=['None','2.4G', '5G'], default='None')
    parser.add_argument('--backup_pattern', help='type of backup_pattern', choices=['newbackup', 'incremental'], default='None')
    parser.add_argument('--data_path', help='the path of testing data', default='None')
    #For example: data_path = '/Volumes/MyPassport500GB/Incremental'
    test = TimeMachine(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)