# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class USBFormat(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'usb_fs'
    # Popcorn
    TEST_JIRA_ID = 'KAM-14616'
    #SETTINGS = {'uut_owner':False}

    def declare(self):
        self.usb_fs = 'fat32,ntfs,exfat,hfsplus'  # fs means file system
        self.timeout = 14400

    
    def init(self):
        self.user_id = self.uut_owner.get_user_id(escape=True)
        self.usb_location = None
        stdout, stderr = self.adb.executeShellCommand('ls /dev/block/vold | grep public')
        self.usb_location = '/dev/block/vold/{}'.format(stdout.strip())

    def test(self):

        if self.uut.get('model') == 'yoda':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(self.uut.get('model')))

        if ',' in self.usb_fs:
            self.usb_fs_list = self.usb_fs.split(",")
        else:
            self.usb_fs_list = [self.usb_fs]
        for usb_fs in self.usb_fs_list:
            self._reset_start_time()

            '''
            Note that there is only one USB device that should be plugged into NAS.
            '''
            # umount the USB drive
            stdout, stderr = self.adb.executeShellCommand('umount {}'.format(self.usb_location))
            if 'Device or resource busy' in stdout:
                raise self.err.StopTest(stdout)

            self.format_usb_drive(usb_fs=usb_fs)

            # reboot NAS in order to to re-mount the USB drive after formatting
            self.reboot_device()

            # Check if the USB drive has the correct file system
            if self.check_usb_fs(usb_fs=usb_fs):
                pass
            else:
                raise self.err.TestError('USB device is not formatted as {}!'.format(usb_fs))

            # Workaround for KAM200-5348 and KAM200-5749
            time.sleep(180)

            stdout, stderr = self.adb.executeShellCommand('rm -rf /data/wd/diskVolume0/restsdk/userRoots/{0}/*'.format(self.user_id), timeout=180)

            usb_alias, usb_id, usb_name = self.get_usb_info()

            if self.dd_file_to_usb_drive(usb_alias=usb_alias):
                pass
            else:
                raise self.err.TestError('dd_file_to_usb_drive failed.')

            if self.trigger_usb_slurp(usb_id=usb_id):
                pass
            else:
                raise self.err.TestFailure('usb slurp failed.')

            # Checksum comparison
            checksum_dict_before = self.get_checksum('/mnt/media_rw/{}'.format(usb_alias))
            checksum_dict_after = self.get_checksum("/data/wd/diskVolume0/restsdk/userRoots/{0}/'{1}'".format(self.user_id, usb_name))
            if self.compare_checksum(checksum_dict_before, checksum_dict_after):
                pass
            else:
                raise self.err.TestFailure('checksum comparison failed.')
            
        # Add keyword 'pass' to the result that will be uploaded to logstash
        self.data.test_result['result'] = 'pass'  


    def get_usb_info(self):
        retry = 0
        while True:
            # Sometimes get_usb_info() will get failure.

            usb_info = self.uut_owner.get_usb_info()
            if not usb_info:
                print "There is no usb_info by REST API:get_usb_info(). retry#{}".format(retry)
                retry += 1
                if retry < 10:
                    time.sleep(10)
                    continue
                else:
                    raise self.err.TestFailure('There is no usb_info by REST API:get_usb_info().')
                    
            usb_id = usb_info.get('id')
            usb_name = usb_info.get('name')
            stdout, stderr = self.adb.executeShellCommand('ls /mnt/media_rw')
            usb_alias = stdout.split('\r\n')[0]
            break

        return usb_alias, usb_id, usb_name


    def trigger_usb_slurp(self, usb_id=None):
        self.log.info('Starting USB slurp')
        
        copy_id = self.uut_owner.create_file_copy(usb_id)

        timer = 0
        while timer <= 36000:
            result = self.uut_owner.get_file_copy(copy_id)  # Get File Copy
            self.log.info('USB slurp status: {}'.format(result))
            if result['status'] == 'done':
                self.log.info('USB slurp is done')
                return True
            elif result['status'] == 'error':
                self.log.error('USB Slurp error')
                return False
            else:
                timer += 3
                time.sleep(3)


    def dd_file_to_usb_drive(self, usb_alias=None):
        stdout, stderr = self.adb.executeShellCommand('mount -o remount,rw /mnt/media_rw/{0}'.format(usb_alias))
        stdout, stderr = self.adb.executeShellCommand('dd if=/dev/urandom of=/mnt/media_rw/{0}/testfile bs=1024k count=20'.format(usb_alias), timeout=180)
        stdout, stderr = self.adb.executeShellCommand('ls /mnt/media_rw/{0}/testfile'.format(usb_alias))
        if 'No such file or directory' in stdout:
            return False
        else:
            return True


    def get_checksum(self, file_path=None):
        stdout, stderr = self.adb.executeShellCommand('md5sum {0}/*'.format(file_path), timeout=180)
        if 'No such file or directory' in stdout:
            return {}
        else:
            checksum_list = list(item for item in stdout.split('\r\n') if item)
            checksum_dict = dict()
            for element in checksum_list:
                key = element.split('  /')[1].split('/')[-1]  # The test_file name is as key.
                value = element.split()[0]  # The md5sum is as value.
                checksum_dict.update({key:value})
            return checksum_dict


    def compare_checksum(self, checksum_dict_before, checksum_dict_after):
        diff = list(item for item in checksum_dict_before.keys() \
                    if checksum_dict_before.get(item) != checksum_dict_after.get(item))
        if diff:
            self.log.warning("MD5 comparison failed! The different items:")
            for item in diff:
                self.log.warning("{}: md5 before [{}], md5 after [{}]".
                                 format(item, checksum_dict_before.get(item), checksum_dict_after.get(item)))
            return False
        else:
            return True


    def check_usb_fs(self, usb_fs=None):
        max_retry = 20
        for i in xrange(max_retry):
            stdout, stderr = self.adb.executeShellCommand("logcat -d | grep 'try mount'")
            try_mount_log = stdout.strip()
            if try_mount_log:
                break
            else:
                if i == (max_retry-1):
                    stdout, stderr = self.adb.executeShellCommand("df")
                    raise self.err.TestError("It's empty from logcat -d | grep 'try mount' !")
                time.sleep(10)
        print 'try_mount_log: {0}'.format(try_mount_log)
        if usb_fs == 'ntfs' and 'ntfs try mount success' in try_mount_log:
            return True
        elif usb_fs == 'exfat' and 'ExFat try mount success' in try_mount_log:
            return True
        elif usb_fs =='hfsplus' and 'HfsPlus try mount success' in try_mount_log:
            return True
        elif usb_fs == 'fat32' and 'vfat try mount success' in try_mount_log:
            return True
        else:
            return False
                

    def reboot_device(self):
        self.adb.executeShellCommand('busybox nohup reboot')
        self.log.info('busybox nohup reboot')
        self.adb.disconnect()
        time.sleep(60)
        self.check_adb(self.timeout)

        # check device boot up
        if not self.adb.wait_for_device_boot_completed(timeout=1200):
            self.log.error('Device seems down or system time is not synced.')
            raise self.err.TestFailure('Timeout({}secs) to wait device boot completed..'.format(1200))

        # check if userRoots is mounted
        while not self._is_timeout(self.timeout):
            stdout, stderr = self.adb.executeShellCommand('df | grep userRoots', timeout=10)
            if '/data/wd/diskVolume0/restsdk/userRoots' in stdout:
                break
            time.sleep(2)               

        # check if userRoots is mounted
        while not self._is_timeout(self.timeout):
            stdout, stderr = self.adb.executeShellCommand('ps | grep restsdk', timeout=10)
            if '/system/bin/restsdk/restsdk-server' in stdout:
                break
            time.sleep(2)

        if self._is_timeout(self.timeout):
            raise self.err.StopTest('Device is not ready, timeout for {} minutes'.format(self.timeout/60))
        else:
            self.log.info('Reboot finished.')

        self.log.info('Stop otaclient...')
        self.adb.stop_otaclient()


    def format_usb_drive(self, usb_fs=None):
        if usb_fs == 'ntfs':
            stdout, stderr = self.adb.executeShellCommand('mkntfs -f -win7  {}'.format(self.usb_location))
        elif usb_fs == 'exfat':
            stdout, stderr = self.adb.executeShellCommand('mkexfat -f  {}'.format(self.usb_location))
        elif usb_fs == 'hfsplus':
            stdout, stderr = self.adb.executeShellCommand('mkhfs -f -j  {}'.format(self.usb_location))
        elif usb_fs == 'fat32':
            stdout, stderr = self.adb.executeShellCommand('busybox mkfs.vfat {}'.format(self.usb_location))
        else:
            raise self.err.StopTest('Please specify which format of USB device will be tested.')
        if 'Impossible to format' in stdout:
            raise self.err.StopTest(stdout)


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
            raise self.err.TestError('Device not responding, timeout for {} secs'.format(timeout))


    def _reset_start_time(self):
        self.start_time = time.time()


    def _is_timeout(self, timeout):
        return (time.time() - self.start_time) >= timeout


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/usb_fs.py --uut_ip 10.92.224.61 --cloud_env qa1 --dry_run --debug_middleware\
        """)
    parser.add_argument('--usb_fs', help='The USB drive filesystem to be tested. \
        Multiple filesystem can be used at the same time, By default is ntfs,exfat,hfsplus,fat32',
        default='ntfs,exfat,hfsplus,fat32')

    test = USBFormat(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)