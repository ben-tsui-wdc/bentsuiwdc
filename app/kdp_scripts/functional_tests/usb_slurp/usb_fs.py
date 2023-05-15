# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"
__note__ = "This testing script supports only ONE USB drive attched to DUT at a time."

# std modules
import json, sys, time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class USBFormat(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-284 - usb_fs'
    # Popcorn
    TEST_JIRA_ID = 'KDP-284'  # This ticket is for MBR drive. 

    def declare(self):
        self.usb_fs = 'fat,ntfs,exfat,hfs'  # fs means file system
        self.timeout = 600
        self.usb_location = None
        self.file_server_ip = '10.200.141.26'
        self.ssh_backup = 'ssh_backup'
        self.usb_export = False
    
    def before_loop(self):
        pass

    def init(self):
        self.user_id = self.uut_owner.get_user_id(escape=True)
        self.device_vol_path = self.ssh_client.getprop(name='device.feature.vol.path')
        self.usb_fs_list = self.usb_fs.split(",")
        # Download the binary in order to format USB drive
        for usb_fs in self.usb_fs_list:
            self.log.info('Donwload the binary(mk{}) from file server ...'.format(usb_fs))
            stdout, stderr = self.ssh_client.execute_cmd('curl ftp:ftppw@{}/KDP/format_binary/mk{} -o {}/mk{}'.format(self.file_server_ip, usb_fs, self.device_vol_path, usb_fs))
            stdout, stderr = self.ssh_client.execute_cmd('chmod +x {}/mk{}'.format(self.device_vol_path, usb_fs))
            if 'No such file or directory' in stderr:
                raise self.err.TestError('There is no necessary binary(mk{})'.format(usb_fs))

    def before_test(self):
        stdout, stderr = self.ssh_client.execute_cmd('mount | grep /mnt/USB')
        if not stdout:
            raise self.err.TestError('There is no USB drive mounted.')
        self.usb_location = '{}'.format(stdout.split()[0])  # /dev/sda1
        self.usb_mnt_point = '{}'.format(stdout.split()[2])  # /mnt/USB/USB1_a1
        stdout, stderr = self.ssh_client.execute_cmd('mkdir {}/{}'.format(self.device_vol_path, self.ssh_backup))
        stdout, stderr = self.ssh_client.execute_cmd('cp -f {}/sshd {}/{}'.format(self.usb_mnt_point, self.device_vol_path, self.ssh_backup))
        stdout, stderr = self.ssh_client.execute_cmd('cp -f {}/sshd.cert {}/{}'.format(self.usb_mnt_point, self.device_vol_path, self.ssh_backup))
        stdout, stderr = self.ssh_client.execute_cmd('cp -f {}/id_ecdsa.pub {}/{}'.format(self.usb_mnt_point, self.device_vol_path, self.ssh_backup))

    def test(self):
        for usb_fs in self.usb_fs_list:
            self.umount_usb_drive()
            self.format_usb_drive(usb_fs=usb_fs)
            self.mount_usb_drive(usb_fs=usb_fs, permission='rw')
            # Copy ssh_cert files back to USB drive 
            stdout, stderr = self.ssh_client.execute_cmd('cp -f {}/{}/* {}'.format(self.device_vol_path, self.ssh_backup, self.usb_mnt_point))
            
            if self.usb_export:
                self.log.info('Create fake dataset in local device...')
                device_dataset_path = '{}/userStorage/{}/usb_fs'.format(self.device_vol_path, self.user_id)
                stdout, stderr = self.ssh_client.execute_cmd('rm -r {}'.format(device_dataset_path))
                stdout, stderr = self.ssh_client.execute_cmd('mkdir {}'.format(device_dataset_path))
                if self.dd_file(path=device_dataset_path, itr=3):
                    pass
                else:
                    raise self.err.TestError('dd files to {} failed.'.format(device_dataset_path))
                # reboot DUT in order to re-mount the USB drive by platform after formatting
                self.reboot_device()
                self.check_usb_fs(usb_fs=usb_fs)
                # Execute USB export
                copy_id, usb_info, resp = self.uut_owner.usb_export(folder_name='usb_fs')
                if resp['status'] != 'done':
                    raise self.err.TestFailure('USB export fail.')
                # Get checksum of dataset from USB and local device respectively
                checksum_dict_usb = self.get_checksum('{}/usb_fs'.format(self.usb_mnt_point))
                checksum_dict_device = self.get_checksum(device_dataset_path)
            else:
                self.log.info('Create fake dataset in USB drive...')
                if self.dd_file(path=self.usb_mnt_point, itr=3):
                    pass
                else:
                    raise self.err.TestError('dd files to {} failed.'.format(self.usb_mnt_point))
                # reboot DUT in order to re-mount the USB drive by platform after formatting
                self.reboot_device()
                self.check_usb_fs(usb_fs=usb_fs)
                usb_id, usb_name = self.get_usb_info()
                # Delete the dataset(which is the same as USB drvie) in userStorage of local device
                stdout, stderr = self.ssh_client.execute_cmd('rm -rf {}/userStorage/{}/{}'.format(self.device_vol_path, self.user_id, usb_name), timeout=180)
                # Execute USB import (slurp)
                copy_id, usb_info, resp = self.uut_owner.usb_slurp()
                #if self.trigger_usb_slurp(usb_id=usb_id):
                if resp['status'] != 'done':
                    raise self.err.TestFailure('USB slurp fail.')
                # Get checksum of dataset from USB and local device respectively
                checksum_dict_usb = self.get_checksum('{}'.format(self.usb_mnt_point))
                checksum_dict_device = self.get_checksum("{}/userStorage/{}/'{}'".format(self.device_vol_path, self.user_id, usb_name))
            
            # Checksum comparison
            if self.compare_checksum(checksum_dict_usb, checksum_dict_device):
                pass
            else:
                raise self.err.TestFailure('checksum comparison failed.')

    def after_test(self):
        pass

    def get_usb_info(self):
        retry = 0
        while True:
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
            break
        return usb_id, usb_name

    def dd_file(self, path=None, itr=1):
        for i in xrange(itr):
            stdout, stderr = self.ssh_client.execute_cmd('dd if=/dev/urandom of={}/testfile{} bs=1024k count=20'.format(path, i), timeout=180)
            stdout, stderr = self.ssh_client.execute_cmd('ls {}/testfile{}'.format(path, i))
            if 'No such file or directory' in stderr:
                return False
        return True

    def get_checksum(self, file_path=None):
        stdout, stderr = self.ssh_client.execute_cmd('md5sum {0}/*'.format(file_path), timeout=180)
        if 'No such file or directory' in stdout:
            return {}
        else:
            checksum_list = stdout.strip().splitlines()
            checksum_dict = dict()
            for element in checksum_list:
                key = element.split()[1].split('/')[-1]  # The test_file name is used as key.
                value = element.split()[0]  # The md5sum is used as value.
                checksum_dict.update({key:value})
            return checksum_dict

    def compare_checksum(self, checksum_dict_before, checksum_dict_after):
        diff = list(item for item in checksum_dict_before.keys() \
                    if checksum_dict_before.get(item) != checksum_dict_after.get(item))
        if diff:
            self.log.warning("MD5 comparison failed! The different items are below:")
            for item in diff:
                self.log.warning("{}: md5 usb [{}], md5 device [{}]".
                                 format(item, checksum_dict_before.get(item), checksum_dict_after.get(item)))
            return False
        else:
            return True

    def check_usb_fs(self, usb_fs=None):
        stdout, stderr = self.ssh_client.execute_cmd("grep '\"driveType\":\"USB\"' /var/log/wdlog* | grep {} | grep {} | grep \"volume inserted\"".format(self.usb_location, self.usb_mnt_point))
        if not stdout:
            stdout, stderr = self.ssh_client.execute_cmd("grep '\"driveType\":\"USB\"' -r /data/kxlog/* | grep {} | grep {} | grep \"volume inserted\" | sort".format(self.usb_location, self.usb_mnt_point))
        restsdk_usb_log = stdout.splitlines()[-1].split(': ')[-1]
        usb_fs_detected = json.loads(restsdk_usb_log).get('fsType')
        if usb_fs == 'ntfs' and usb_fs_detected == 'ntfs':
            return True
        elif usb_fs == 'exfat' and usb_fs_detected == 'exfat':
            return True
        elif usb_fs == 'hfs' and usb_fs_detected == 'hfsplus':
            return True
        elif usb_fs == 'fat' and usb_fs_detected == 'vfat':
            return True
        else:
            raise self.err.TestFailure('The USB drvie fstype is {}, but restsdk recognizes it as "{}"'.format(usb_fs, usb_fs_detected))

    def reboot_device(self):
        self.ssh_client.reboot_device()
        start_time = time.time()
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=self.timeout):
            raise self.err.TestError('Device was not shut down successfully!')
        if not self.ssh_client.wait_for_device_boot_completed(timeout=self.timeout):
            raise self.err.TestError('Device was not boot up successfully!')
        self.log.warning("Reboot complete in {} seconds".format(time.time() - start_time))

    def format_usb_drive(self, usb_fs=None):
        if usb_fs == 'ntfs':
            stdout, stderr = self.ssh_client.execute_cmd('{}/mkntfs -f -v:USB_NTFS -win7 -a:4096 {}'.format(self.device_vol_path, self.usb_location))
        elif usb_fs == 'exfat':
            stdout, stderr = self.ssh_client.execute_cmd('{}/mkexfat -f -v:USB_exFAT -a:32K {}'.format(self.device_vol_path, self.usb_location))
        elif usb_fs == 'hfs':
            stdout, stderr = self.ssh_client.execute_cmd('{}/mkhfs -f -j -c -v:USB_HFS {}'.format(self.device_vol_path, self.usb_location))
        elif usb_fs == 'fat':
            stdout, stderr = self.ssh_client.execute_cmd('{}/mkfat -f -v:USB_FAT32 -t:32 -a:4096 {}'.format(self.device_vol_path, self.usb_location))
        else:
            raise self.err.StopTest('Please specify which format of USB device will be tested.')
        if 'Impossible to format' in stderr or 'not found' in stderr:
            raise self.err.TestError(stderr)

    def mount_usb_drive(self, usb_fs=None, permission='ro'):
        # permission = ro/rw
        cmd = 'mount {} {}'.format(self.usb_location, self.usb_mnt_point)
        if usb_fs == 'ntfs' or usb_fs == 'hfs':
            option = '{},nls=utf8,fmask=0,dmask=0,force,user_xattr'.format(permission)
        else:
            option = None
        if option:
            cmd = '{} -t ufsd -o {}'.format(cmd, option)
        stdout, stderr = self.ssh_client.execute_cmd(cmd)

    def umount_usb_drive(self):
        stdout, stderr = self.ssh_client.execute_cmd('umount -f {}'.format(self.usb_mnt_point))
        if 'Device or resource busy' in stderr or 'target is busy' in stderr:
            raise self.err.StopTest(stderr)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/usb_fs.py --uut_ip 10.92.224.61 --cloud_env qa1 --dry_run --debug_middleware\
        """)
    parser.add_argument('--usb_fs', help='The USB drive filesystem to be tested. \
        Multiple filesystem can be used at the same time, By default is ntfs,exfat,hfs,fat',
        default='ntfs')
    parser.add_argument('--file_server_ip', help='file_server_ip_mvwarrior', default='10.200.141.26')
    parser.add_argument('--usb_export', help='Use USB export mode', action='store_true')

    test = USBFormat(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)