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


# KAM-7948: RAID1 Creation - 2Bay
class RaidCreation(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'RaidCreation'
    # Popcorn
    TEST_JIRA_ID = 'KAM-7948'
    SETTINGS = { # Disable all utilities.
        'disable_firmware_consistency': False,
        'adb': True, # Disbale ADB and ignore any relevant input argument.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        self.timeout = 3600


    def test(self):
        self.start_time = time.time()

        if self.uut.get('model') != 'pelican':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(self.uut.get('model')))
        # Break the partition on disks
        stdout, stderr = self.adb.executeShellCommand('dd if=/dev/urandom of=/dev/md1  count=500 bs=1k')
        # reboot device
        self.adb.executeShellCommand('busybox nohup reboot')
        self.adb.disconnect()
        
        while self.is_device_pingable():
            self.log.info('Waiting device power off ...')
            time.sleep(2)
            if time.time() - self.start_time >= 600:
                raise self.err.TestError('Device failed to power off within {} seconds'.format(600))
        
        self.start_time = time.time()
        while not self.is_device_pingable():
            self.log.info('Waiting device boot up ...')
            time.sleep(5)
            if time.time() - self.start_time > 600:
                raise self.err.TestError('Timeout waiting to boot within {} seconds'.format(600))
        self.check_adb(self.timeout)
        time.sleep(30)

        led_dict = self.search_event(event_type='LED', event_before='Heartbeating', event_after='Slow Breathing')
        sys_dict = self.search_event(event_type='SYS', event_before='File system check', event_after='Power up')
        if self.led_list[-1] == sys_dict and self.led_list[-2] == led_dict:
            pass
        else:
            self.adb.print_led_info(self.led_list)
            raise self.err.TestFailure('Led is not Slow Breathing while disks are clear.')
 
        # Factory reset
        self.adb.executeShellCommand('busybox nohup reset_button.sh factory')
        self.adb.disconnect()
        time.sleep(180)
        self.check_adb(self.timeout)

        self.check_parameter('ps | grep mke2fs', 'mke2fs', err_msg='There is no mke2fs process!')
        # check platform boot completed
        if not self.adb.wait_for_device_boot_completed(timeout=3600):
            raise self.err.TestFailure('Devce not boot_completed')            
        self.check_parameter('df | grep userRoots', '/data/wd/diskVolume0/restsdk/userRoots', err_msg='There is no userRoots mounted!')

        # stop otaclient
        self.adb.stop_otaclient()

        # check if raid level is the same as expectation.
        self.raid_type_check(raid='mirror')

        # check if raid size is the same as expectation.
        self.raid_size_check(raid='mirror')
        
        # The LED status will change after a period of time even if userRoots is mounted.    
        time.sleep(60)

        if self.search_event(event_type='LED', event_before='Slow Breathing', event_after='Full Solid'):
            pass
        else:
            self.adb.print_led_info(self.led_list)
            raise self.err.TestFailure('LED is not into Full Solid after raid is ceated.')


    def is_device_pingable(self):
        command = 'nc -zv -w 1 {0} 5555 > /dev/null 2>&1'.format(self.adb.uut_ip)  # 5555 is the adb port
        response = os.system(command)
        if response == 0:
            return True
        else:
            return False


    def check_parameter(self, command, expect, err_msg=None):
        while True:
            stdout, stderr = self.adb.executeShellCommand(command, timeout=10)
            if expect in stdout:
                break
            if self._is_timeout(self.timeout):
                if not err_msg:
                    err_msg = stdout
                raise self.err.TestFailure('{} after {} seconds timeout'.format(err_msg, self.timeout))
            time.sleep(30)
    

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


    def raid_type_check(self, raid=None):
        mdadm_detail = self.adb.executeShellCommand('mdadm --detail -scan | grep /dev/md1', timeout=10)[0]
        if raid == 'span':
            if 'level=linear' in mdadm_detail:
                self.log.info('The device raid is span, which is the same as expectation.')
            else:
                raise self.err.TestFailure('raid was assigned "span", however, the device raid is {0}.'.format(mdadm_detail))
        elif raid == 'stripe':
            if 'level=raid0' in mdadm_detail:
                self.log.info('The device raid is stripe, which is the same as expectation.')
            else:
                raise self.err.TestFailure('raid was assigned "stripe", however, the device raid is {0}.'.format(mdadm_detail))
        elif raid == 'mirror':
            if 'level=raid1' in mdadm_detail:
                self.log.info('The device raid is mirror, which is the same as expectation.')
            else:
                raise self.err.TestFailure('raid was assigned "mirror", however, the device raid is {0}.'.format(mdadm_detail))


    def raid_size_check(self, raid=None):
        result = self.adb.executeShellCommand('mdadm --detail  /dev/md1', timeout=10)[0]
        if len(re.findall('/dev/block/sata\S', result)) != 2:
            raise self.err.StopTest('The number of disks in device is not equal to 2.')
        disk_1 = re.findall('/dev/block/sata\S', result)[0]
        disk_2 = re.findall('/dev/block/sata\S', result)[1]
        result = self.adb.executeShellCommand('sgdisk --print {0}; sgdisk --print {1}'.format(disk_1, disk_2), timeout=10)[0]
        if re.search('Problem opening.*Error is 2.', result):
            raise self.err.StopTest('There is at least one disk that cannot be found on device.')
        else:
            # check disk size
            raw_disk_size_list = []
            if 'TiB' in result:
                for element in re.findall('sectors, .*TiB', result):
                    raw_disk_size_list.append(float(element.split('sectors, ')[1].split(' TiB')[0]))  # transform unit to: TiB
            elif 'GiB' in result:
                for element in re.findall('sectors, .*GiB', result):
                    raw_disk_size_list.append(float(element.split('sectors, ')[1].split(' GiB')[0])/1024)  # transform unit to: TiB
            # check volume size
            result = self.adb.executeShellCommand('df | grep userRoots', timeout=10)[0]
            raid_size_actual = float(result.split()[1].split('G')[0])/1024  # transform unit to: TiB

            if raid == 'span' or raid == "stripe":
                raid_size_expect = sum(raw_disk_size_list)
            elif raid == 'mirror':
                raid_size_expect = min(raw_disk_size_list)

            if 0.9 < raid_size_actual/raid_size_expect and raid_size_actual/raid_size_expect < 1.1:
                pass
            else:
                raise self.err.TestFailure('The raid size is not the same as expectation.')


    def check_adb(self, timeout):
        if self.adb.connected:
            self.adb.disconnect()
        while not self._is_timeout(timeout):
            self.log.info('Attempt to connect...')
            try:
                self.adb.connect(timeout=10)
            except Exception:
                self.log.info('adb not connecting')
                time.sleep(5)
            if self.adb.connected:
                break
        if not self.adb.connected:
            raise self.err.StopTest('Device not responding, timeout for {} secs'.format(timeout))


    def _is_timeout(self, timeout):
        return (time.time() - self.start_time) >= timeout


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/raid_creation.py --uut_ip 10.92.224.71 --dry_run --debug_middleware --disable_clean_logcat_log\
        """)

    test = RaidCreation(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)