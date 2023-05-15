# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import re
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class RaidConversion(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'raid_conversion'
    # Popcorn
    TEST_JIRA_ID = 'KAM-18889'
    SETTINGS = { # Disable all utilities.
        'disable_firmware_consistency': False,
        'adb': True, # Disbale ADB and ignore any relevant input argument.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        self.raid_type = 'span,stripe,mirror'
        self.timeout = 7200

        
    def test(self):
        if self.uut.get('model') != 'pelican':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(self.uut.get('model')))

        if ',' in self.raid_type:
            self.raid_list = self.raid_type.split(",")
        else:
            self.raid_list = [self.raid_type]

        for raid in self.raid_list:
            self._reset_start_time()
            try:
                # Factory reset
                self.adb.executeShellCommand('notify_cloud -s reset_button -n 136')  # To notify cloud that the device will be executed "factory_reset"
                time.sleep(5)  # This is also used in "/system/bin/reset_button.sh" in device.
                self.adb.executeShellCommand('busybox nohup factory_reset.sh {0}'.format(raid))
                self.adb.disconnect()
                time.sleep(300)
                self.check_adb(self.timeout)

                # check device boot up
                while not self._is_timeout(self.timeout):
                    boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed', timeout=10)[0]
                    if '1' in boot_completed:
                        self.log.info('"sys.boot_completed" is turned into 1.')
                        break
                    time.sleep(2)
                
                '''
                For http://jira.wdmv.wdc.com/browse/KAMBKLG-953
                print 'KAMBKLG-953 print logcat after sys.boot_completed is 1.'
                self.adb.executeShellCommand('logcat -d', timeout=20)
                self.adb.executeShellCommand('getprop | grep factory', timeout=10)
                self.adb.executeShellCommand('ps', timeout=10)
                time.sleep(300)
                print 'KAMBKLG-953 print logcat after sys.boot_completed is 1 and 300 seconds pass by.'
                self.adb.executeShellCommand('logcat -d', timeout=20)
                self.adb.executeShellCommand('getprop | grep factory', timeout=10)
                self.adb.executeShellCommand('ps', timeout=10)
                '''

                # check platform boot completed
                if not self.adb.wait_for_device_boot_completed(timeout=3600):
                    raise self.err.TestFailure('Devce not boot_completed')

                # check if userRoots is mounted
                while not self._is_timeout(self.timeout):
                    userRoots = self.adb.executeShellCommand('df | grep userRoots', timeout=10)[0]
                    if '/data/wd/diskVolume0/restsdk/userRoots' in userRoots:
                        self.log.info('"/data/wd/diskVolume0/restsdk/userRoots" is mounted.')
                        break
                    time.sleep(2)               

                if self._is_timeout(self.timeout):
                    print 'KAMBKLG-953 print logcat when timeout.'
                    self.adb.executeShellCommand('logcat -d', timeout=20)
                    self.adb.executeShellCommand('getprop | grep factory', timeout=10)
                    self.adb.executeShellCommand('ps', timeout=10)
                    raise self.err.StopTest('Device is not ready, timeout for {} minutes'.format(self.timeout/60))
                else:
                    self.log.info('Factory Reset is finished.')
            
                # stop otaclient
                self.adb.stop_otaclient()

                # check if raid level is the same as expectation.
                self.raid_type_check(raid=raid)

                # check if raid size is the same as expectation.
                self.raid_size_check(raid=raid)
                
            except Exception as ex:
                raise self.err.TestError('Failed to execute factory Reset due to {0}!'.format(ex))
            
        # Add keyword 'pass' to the result that will be uploaded to logstash
        self.data.test_result['result'] = 'pass'  


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
            for element in re.findall('sectors, .*TiB', result):
                raw_disk_size_list.append(float(element.split('sectors, ')[1].split(' TiB')[0]))  # Unit of size: TiB
            # check raid size
            result = self.adb.executeShellCommand('df | grep userRoots', timeout=10)[0]
            raid_size_actual = float(result.split()[1].split('G')[0])/1024  # Unit of size: TiB

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


    def _reset_start_time(self):
        self.start_time = time.time()


    def _is_timeout(self, timeout):
        return (time.time() - self.start_time) >= timeout


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/raid_conversion.py --uut_ip 10.92.224.71 --dry_run --debug_middleware\
        """)
    parser.add_argument('--raid_type', help='The raid type to be tested. Multiple raid types can be used at the same time, separated by comma, for example: span,stripe,mirror. By default is span,stripe,mirror.', default='span,stripe,mirror')

    test = RaidConversion(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)