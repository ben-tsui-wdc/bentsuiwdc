# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings


class USB_Flash_Firmware(TestCase):

    TEST_SUITE = "USB_Flash_Images"
    TEST_NAME = "USB_Flash_Firmware"
    # Popcorn
    TEST_JIRA_ID = 'KAM-7944'
    MAX_RETRIES = 10

    SETTINGS = Settings(**{
        'disable_firmware_consistency': True,
        'uut_owner': False,
    })

    def declare(self):
        self.file_server = '10.200.141.26'


    def test(self):
        '''
            For Monarch and Pelican only now. If we need to test yodaplus, might need to run disable_factory.sh after usb flash
        '''
        product = self.uut.get('model')
        
        self.log.info('Step 1: Download the fw image from file server and unzip it')
        self.adb.executeShellCommand(cmd='busybox wget ftp://ftp:ftppw@{}/firmware/download.sh -O /tmp/download.sh'.format(self.file_server), consoleOutput=True)
        self.adb.executeShellCommand(cmd='sh /tmp/download.sh {} {} {} {}'.format(self.img_version, self.img_env, self.img_var, self.file_server), timeout=1200, consoleOutput=True)
        usb_name = self.adb.executeShellCommand(cmd='ls /mnt/media_rw', consoleOutput=False)[0].strip()
        fw_image = 'install.img'
        expect_md5 = self.adb.executeShellCommand(cmd='cat /mnt/media_rw/{}/{}.md5'.format(usb_name, fw_image))[0].strip()
        actual_md5 = self.adb.executeShellCommand(cmd='busybox md5sum /mnt/media_rw/{}/{}'.format(usb_name, fw_image), timeout=300)[0].strip().split()[0]
        if expect_md5 != actual_md5:
            raise self.err.TestFailure('Firmware image MD5 comparisson failed! Expect: {}, Actual: {}'.format(expect_md5, actual_md5))
        
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

        self.log.info('Step 3: Flash the firmware image and wait for device reboot')
        try:
            time.sleep(10)  # Wait for all '\x1b' to run out. 
            for i in range(5):  # Write an emypt sting 5 times first to ensure console prompt stop at Realtek>
                time.sleep(1)
                self.serial_client.serial_write('\n')  
            self.serial_client.serial_write('go ru')
            self.serial_client.serial_wait_for_string('prepare poweroff', timeout=900, raise_error=True)
            self.log.warning('Firmware update complete, rebooting...')
            self.serial_client.serial_wait_for_string('boot_complete_proc_write', timeout=900, raise_error=True)
            self.log.warning('Boot Complete, wait for creating volume...')
            # USB flash fw needs more time to complete boot up, sleep 300 secs
            time.sleep(300)
            if product == 'pelican':
                self.log.warning('Need to rebuild raid after usb flash fw')
                self.serial_client.serial_write('disk_manager_pelican.sh -c')
                self.serial_client.serial_wait_for_string('Allocating group tables', timeout=60, raise_error=False)
                self.serial_client.serial_wait_for_string('Great! Everything looks perfect', timeout=1800, raise_error=False)
                self.serial_client.serial_write('busybox nohup reboot')

            if not self.adb.wait_for_device_boot_completed(timeout=1800, max_retries=3):
                raise self.err.TestFailure('Device seems down, device boot not completed')
        except Exception as e:
            raise self.err.TestFailure('Flash firmware image failed! Error message: {}'.format(repr(e)))

        # Send command to check uboot version
        new_fw_version = self.adb.executeShellCommand('getprop ro.build.version.incremental', consoleOutput=True)[0].strip()
        self.log.warning('new_fw_version:{}'.format(new_fw_version))
        if new_fw_version != self.img_version:
            raise self.err.TestFailure('Firmware version is incorrect! Expect: {}, Actual: {}'.format(self.img_version, self.new_fw_version))

if __name__ == '__main__':
    parser = InputArgumentParser("""
        *** USB flash firmware Test ***
        """)
    parser.add_argument('--file_server', help='File server IP address', default='10.200.141.26')
    parser.add_argument('--img_version', help='test firmware version')
    parser.add_argument('--img_env', help='test firmware environment')
    parser.add_argument('--img_var', help='test firmware variant')
    test = USB_Flash_Firmware(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)