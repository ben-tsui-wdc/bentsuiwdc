# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings


class USB_Flash_Uboot(TestCase):

    TEST_SUITE = "USB_Flash_Images"
    TEST_NAME = "USB_Flash_Uboot"
    # Popcorn
    TEST_JIRA_ID = 'KAM-7943'

    MAX_RETRIES = 10

    SETTINGS = Settings(**{
        'disable_firmware_consistency': True,
        'uut_owner': False,
    })


    def declare(self):
        self.file_server = '10.200.141.26'


    def before_test(self):
        if "dev" in self.env.cloud_env:
            env = ''
        elif "qa" in self.env.cloud_env:
            env = '-QA'
        else:
            env='-prod'
    
        stdout, stderr = self.adb.executeCommand(cmd="curl http://repo.wdc.com/content/repositories/projects/MyCloudOS/MCAndroid{}/{}/".format(env, self.env.UUT_firmware_version))
        for element in stdout.strip().split():
            check_list = [self.env.UUT_firmware_version, self.uut['model'], 'uboot']
            check_no_list = ['md5', 'sha1']
            if all([ word in element for word in check_list]) and all([word not in element for word in check_no_list]):
                self.uboot_name = element.split('"')[1].split('/')[-1]


    def test(self):
        product = self.uut.get('model')
        self.log.info('Step 1: Download the uboot image from file server and unzip it')
        self.adb.executeShellCommand(cmd='busybox wget ftp://ftp:ftppw@{}/firmware/download_uboot.sh -O /tmp/download_uboot.sh'.format(self.file_server))
        usb_name = self.adb.executeShellCommand(cmd='ls /mnt/media_rw')[0].strip()

        for retries in range(self.MAX_RETRIES):
            self.adb.executeShellCommand(cmd='sh /tmp/download_uboot.sh {} {}'.format(self.uboot_name, self.file_server), timeout=600)
            uboot_name = self.adb.executeShellCommand(cmd='ls /mnt/media_rw/{} | grep uboot | grep zip | grep MCAndroid'.format(usb_name))[0].strip()        
            if uboot_name:
                self.uboot_version = uboot_name.split("{}-".format(self.uut.get('model')))[1].split('.zip')[0]
                break
            else:
                time.sleep(2)
        if not uboot_name:
            raise self.err.TestSkipped('Cannot acquire uboot_name from USB drive after {} retries.'.format(self.MAX_RETRIES))

        # Compare current uboot version with uboot image version
        # Note: The uboot version CANNOT be downgraded.
        current_uboot_version = self.adb.executeShellCommand('factory.spi load; fw_printenv ver', consoleOutput=True)[0].strip().split('=')[1]
        self.log.warning('current_uboot_version:{}'.format(current_uboot_version))
        self.log.warning('image_uboot_version:{}'.format(self.uboot_version))
        temp_1 = current_uboot_version.split('.')
        temp_2 = self.uboot_version.split('.')
        for i, element in enumerate(temp_1):
            if int(temp_1[i]) > int(temp_2[i]):
                raise self.err.TestSkipped('current_uboot_version:{}    image_uboot_version:{}. Since uboot version CANNOT be downgraded, skipped the test !!'.format(current_uboot_version, self.uboot_version))

        uboot_image = 'wd_{}.uboot32.fb.dvrboot.exe.bin'.format(product)  # Todo: get the uboot image name
        expect_md5 = self.adb.executeShellCommand(cmd='cat /mnt/media_rw/{}/{}.md5'.format(usb_name, uboot_image))[0].strip()
        actual_md5 = self.adb.executeShellCommand(cmd='busybox md5sum /mnt/media_rw/{}/{}'.format(usb_name, uboot_image), timeout=300)[0].strip().split()[0]
        if expect_md5:  # http://jira.wdmv.wdc.com/browse/KAM200-4024
            if expect_md5 != actual_md5:
                raise self.err.TestFailure('uboot image MD5 comparisson failed! Expect: {}, Actual: {}'.format(expect_md5, actual_md5))

        self.log.info('Step 2: Reboot the device and press esc until we see "Realtel>" key word')
        found_keyword = False
        for retries in range(self.MAX_RETRIES):
            self.serial_client.serial_write('busybox nohup reboot')
            self.serial_client.serial_wait_for_string('prepare poweroff', timeout=60, raise_error=False)
            time.sleep(5)  # Device will reboot 5 secs after seeing prepare poweroff
            for i in range(30):
                self.serial_client.serial_write('\x1b')
                # Check the Realtek> keywork every sec for total 30 secs
                output = self.serial_client.serial_wait_for_string('Realtek>', timeout=1, raise_error=False)
                if output:
                    self.log.warning('Found the "Realtek>" keyword!')
                    found_keyword = True
                    break
            if found_keyword:
                break
            else:
                self.log.info('ESC button might not be pressed, {} retries remaining...'.format(self.MAX_RETRIES-int(retries)-1))

        if not found_keyword:
            raise self.err.StopTest('Cannot enter Realtek mode in {} retries!'.format(self.MAX_RETRIES))

        self.log.info('Step 3: Flash the uboot image and wait for device reboot')
        try:
            self.serial_client.serial_write('\n')  # Write an emypt sting for the first time
            self.serial_client.serial_write('usb start')
            self.serial_client.serial_wait_for_string('USB Device(s) found', timeout=30, raise_error=False)
            self.serial_client.serial_wait_for_string('Realtek>', timeout=60, raise_error=True)
            self.serial_client.serial_write('fatload usb 0:1 0x1500000 {}'.format(uboot_image))
            self.serial_client.serial_wait_for_string('bytes read', timeout=10, raise_error=False)
            self.serial_client.serial_wait_for_string('Realtek>', timeout=60, raise_error=True)
            self.serial_client.serial_write('go 0x1500000')
            # Pelican need to run power cycle manually after uboot upgrade
            if product == 'pelican':
                self.serial_client.serial_wait_for_string('Finish', timeout=60, raise_error=True)
                time.sleep(15) # Might not complete yet, wait for 15 secs when seeing finish
                self.power_switch.power_cycle(self.env.power_switch_port, cycle_time=10)
            
            if product == 'yodaplus':
                self.serial_client.wait_for_boot_complete()
            if not self.adb.wait_for_device_boot_completed(max_retries=3):
                raise self.err.TestFailure('Device seems down, device boot not completed')
        except Exception as e:
            raise self.err.TestFailure('Flash uboot image failed! Error message: {}'.format(repr(e)))

        # Send command to check uboot version
        new_uboot_version = self.adb.executeShellCommand('factory.spi load; fw_printenv ver', consoleOutput=True)[0].strip().split('=')[1]
        self.log.warning('new_uboot:{}'.format(new_uboot_version))
        if new_uboot_version != self.uboot_version:
            raise self.err.TestFailure('uboot version is incorrect! Expect: {}, Actual: {}'.format(self.uboot_version, self.new_uboot_version))

if __name__ == '__main__':
    parser = InputArgumentParser("""
        *** flash uBoot Test ***
        """)
    parser.add_argument('--file_server', help='File server IP address', default='10.200.141.26')
    test = USB_Flash_Uboot(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)