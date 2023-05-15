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

from functional_tests.service_check import ServiceCheck

class RaidRebuild(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'raid_rebuild'
    # Popcorn
    TEST_JIRA_ID = 'KAM-7949'
    SETTINGS = { # Disable all utilities.
        'disable_firmware_consistency': False,
        'adb': True, # Disbale ADB and ignore any relevant input argument.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        self.timeout = 300
        self.test_file_path = '/data/wd/diskVolume0/TEST_FILE'
        self.dd_count = 1000  # unit is 1 MB
        self.dd_blocksize = '1m'


    def init(self):
        if 'pelican' not in self.uut.get('model'):
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(self.uut.get('model')))


    def before_test(self):
        # Creata a testing file via urandom
        self.dd_urandom(of=self.test_file_path, count=self.dd_count, bs=self.dd_blocksize)
        self.original_checksum = self.md5_checksum(test_file_path=self.test_file_path, device_type='tested_device')
        
        # For SMB test
        stdout, stderr = self.adb.executeShellCommand('cp {} /data/wd/diskVolume0/samba/share'.format(self.test_file_path))
        if not os.path.isdir('/mnt/cifs'):
            os.mkdir('/mnt/cifs')
        self.adb.mount_samba(share_location='//{}/Public'.format(self.env.uut_ip), mount_point='/mnt/cifs')


    def test(self):

        #sys.exit(0)


        # Mark the specified disk as failed.
        self.adb.executeShellCommand('mdadm /dev/md1 --fail /dev/block/{0}'.format(self.failed_disk))
        # Compare checksum on the tested device
        self.checksum_compare(new_checksum=self.md5_checksum(test_file_path=self.test_file_path, device_type='tested_device'))

        # Remove the failed disk from RAID.
        self.adb.executeShellCommand('mdadm /dev/md1 --remove /dev/block/{0}'.format(self.failed_disk))
        stdout, stderr = self.adb.executeShellCommand('mdadm --detail /dev/md1', timeout=10)
        if 'State : clean, degraded' in stdout and 'removed' in stdout:
            pass
        elif 'State : active, degraded' in stdout and 'removed' in stdout:
            pass
        else:
            raise self.err.StopTest('Failed to remove the specified disk: {0} from RAID!!!'.format(self.failed_disk))

        # SMB and AFP test when RAID is degraded. (That means only ONE availabe disk in tested device.)
        self.checksum_compare(new_checksum=self.md5_checksum(test_file_path='/mnt/cifs/TEST_FILE', device_type='script_client'))

        # compare checksum on the tested device
        self.checksum_compare(new_checksum=self.md5_checksum(test_file_path=self.test_file_path, device_type='tested_device'))

        # break the failed_disk partition
        self.dd_urandom(of='/dev/block/{}'.format(self.failed_disk), count=self.dd_count, bs=self.dd_blocksize)

        # re-add the same disk to RAID then wait until the RAID finishing recovering.
        self.adb.executeShellCommand('mdadm /dev/md1 --add /dev/block/{0}'.format(self.failed_disk))

        # check if the RAID rebuiling is in progress.
        time.sleep(30)
        if self.mdadm_detail(string='spare rebuilding   /dev/block/{}'.format(self.failed_disk)):
            pass
        else:
            raise self.err.TestFailure('RAID rebuilding doesn\'t proceed.')
        '''
        # The LED behavior needs to be confirmed.
        # check LED status
        led_dict = self.search_event(event_type='LED', event_after='Heartbeating')
        sys_dict = self.search_event(event_type='SYS', event_after='Start building DISK RAID')
        if self.led_list.index(sys_dict) - self.led_list.index(led_dict) < 5:  # 5 is just an approximate number.
            pass
        else:
            self.adb.print_led_info(self.led_list)
            raise self.err.TestFailure('Led is not Heartbeating while building DISK RAID.')
        '''
        # SMB and AFP test while RAID reduilding is in progress.
        self.checksum_compare(new_checksum=self.md5_checksum(test_file_path='/mnt/cifs/TEST_FILE', device_type='script_client'))

        # Clean logcat before RAID building finished
        stdout, stderr = self.adb.executeShellCommand('logcat -c')

        # check if the RAID rebuilding finished.
        rebuild_start_time = time.time()

        time.sleep(16200)  # Since 2TB disk * 2 will spend more than 5 hours to execute RAID rebuild. Let script wait for a while.
        
        while True:
            if not self.mdadm_detail(string='State : clean, degraded, recovering') and \
               not self.mdadm_detail(string='Rebuild Status'):
               break
            elif time.time() - rebuild_start_time > 86400:  # Accoding to the experiment, Pelican with 8T disk * 2 needs more than 800 mins to rebuild RAID.
                raise self.err.StopTest('RAID rebuild doesn\'t finish within 86400 seconds.')
            time.sleep(1200)
        rebuild_total_time = (time.time() - rebuild_start_time)/60
        '''
        # The LED behavior needs to be confirmed.
        # Check LED after RAID rebuilding finished
        led_dict = self.search_event(event_type='LED', event_after='Slow Breathing')
        sys_dict = self.search_event(event_type='SYS', event_after='Disk RAID Build Completed')
        if self.led_list.index(sys_dict) - self.led_list.index(led_dict) < 5:  # 5 is just an approximate number.
            pass
        else:
            #self.adb.print_led_info(self.led_list)
            raise self.err.TestFailure('Led is not Slow Breathing after DISK RAID building finished.')

        self.checksum_compare(new_checksum=self.md5_checksum(test_file_path=self.test_file_path, device_type='tested_device'))
        '''
        # Check if mdadm state is healthy
        if self.mdadm_detail(string='State : active', exact_comparison=True) or self.mdadm_detail(string='State : clean', exact_comparison=True):
            pass
        else:
            raise self.err.TestFailure('RAID State is not healthy after rebuilding finished!')


    def after_test(self):
        self.adb.umount_samba(mount_point='/mnt/cifs')
        pass


    def mdadm_detail(self, string=None, exact_comparison=False):
        stdout, stderr = self.adb.executeShellCommand('mdadm --detail /dev/md1', timeout=60)
        check_flag = False

        for item in stdout.splitlines():
            if exact_comparison:
                if '{}'.format(string) == item.strip():
                    check_flag = True
                    break
            else:
                if '{}'.format(string) in item:
                    check_flag = True
                    break
        return check_flag


    def dd_urandom(self, of=None, count=None, bs=None):
        self.log.info("dd via urandom: {}...".format(of))
        try:
            stdout, stderr = self.adb.executeShellCommand('dd if=/dev/urandom of={0} count={1} bs={2}'.format(of, count, bs), timeout=1800)
            if "I/O error" in stdout:
                raise self.err.StopTest("Failed to dd by urandom: {0}, there is I/O error.".format(of))
        except Exception as e:
            raise self.err.StopTest("Failed to dd by urandom: {0}, error message: {}".format(of, repr(e)))


    def md5_checksum(self, test_file_path=None, device_type=None):
        if device_type == 'tested_device':
            stdout, stderr = self.adb.executeShellCommand('md5sum {}'.format(test_file_path), timeout=900)
        elif device_type == 'script_client':
            stdout, stderr = self.adb.executeCommand('md5sum {}'.format(test_file_path), timeout=900)
        if 'No such file or directory' in stderr:
            raise self.err.StopTest("{}".format(stderr))
        else:
            return stdout.strip().split()[0]


    def checksum_compare(self, old_checksum=None, new_checksum=None):
        if old_checksum == None:
            old_checksum = self.original_checksum
        if new_checksum != old_checksum:
            self.err.TestFailure('The md5_checksum is different between before and after removing disk!')
        else:
            print 'checksum comparison pass'


    def renew_led_log(func):
        def get_led_log(self, *args, **kwargs):
            # Get current LedServer log from logcat
            self.led_list = self.adb.get_led_logs()
            if not self.led_list:
                raise self.err.StopTest('There are no LED info in logcat!')
            return func(self, *args, **kwargs)
        return get_led_log


    @renew_led_log
    def search_event(self, event_type=None, event_before=None, event_after=None):
        count = 0
        dict_list = []
        for item in self.led_list:
            if event_type and event_before and event_after:
                if item.get('type')==event_type and item.get('before')==event_before and item.get('after')==event_after:
                    dict_list.append(item)
                    count+=1
            elif event_type and event_after:
                if item.get('type')==event_type and item.get('after')==event_after:
                    dict_list.append(item)
                    count+=1
        if count == 0:
            return None
        elif count > 0:
            if count > 1:
                self.log.warning('The LedServer item occurred many times({})! [type] {} [before] {} [after] {}'.format(count, event_type, event_before, event_after))
                self.log.warning('{}'.format(dict_list))
            return dict_list[0]


if __name__ == '__main__':
    parser = InputArgumentParser("""\
    *** raid type conversion test on Kamino Android ***
    Examples: ./run.sh functional_tests/raid_rebuild.py --uut_ip 10.92.224.71 --dry_run --debug_middleware\
    """)
    parser.add_argument('--failed_disk', help='Specify the disk which is going to be marked as "failed". By default is sataa2.', choices=['sataa2', 'satab2'], default='sataa2')

    test = RaidRebuild(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
