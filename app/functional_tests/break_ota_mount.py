# -*- coding: utf-8 -*-

# std modules
import sys
import time
import random

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class BreakOTAMount(TestCase):

    TEST_SUITE = 'Functional Tests'
    TEST_NAME = 'Break OTA Mount'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        image_name = 'MCAndroid-QA-7.9.0-109-os-monarch.zip'

    def test(self):
        self.clean_up()
        if self.mode in 'rm_power':
            self.power_off_to_break_after_rm_otaclient()
        elif self.mode in 'reboot':
            random.choice([self.reboot_to_break_during_download_image, self.reboot_to_break_during_unzip_image])()
        else:
            random.choice([self.power_off_to_break_during_download_image, self.power_off_to_break_during_unzip_image])()
        self.check_mount_point()

    def check_mount_point(self):
        msg = ''
        stdout, _ = self.adb.executeShellCommand("mount | grep otaclient")
        if not stdout:
            msg = 'Mount point broken!'
        stdout, _ = self.adb.executeShellCommand("logcat -d | grep 'unhandled exitCode 24'")
        if stdout:
            msg += 'Hit exitCode 24!'
        if msg:
            raise self.err.TestFailure(msg)

    def power_off_to_break_after_rm_otaclient(self):
        self.adb.executeShellCommand("umount /tmp/otaclient")
        self.adb.executeShellCommand("stop otaclient")
        self.adb.executeShellCommand("rm /data/wd/diskVolume0/kars/com.wd.otaclient")
        self.adb.executeShellCommand("start otaclient")
        time.sleep(random.uniform(0, 2))
        self.adb.executeShellCommand("ls -al /data/wd/diskVolume0/kars/com.wd.otaclient")
        self.power_off_on_device()

    def reboot_to_break_during_download_image(self):
        self.background_slow_download_image()
        self.random_sleep(max_time=100)
        self.reboot_device()

    def power_off_to_break_during_download_image(self):
        self.background_slow_download_image()
        self.random_sleep(max_time=100)
        self.power_off_on_device()

    def reboot_to_break_during_unzip_image(self):
        self.fast_download_image()
        self.background_unzip_image()
        self.random_sleep(max_time=10)
        self.reboot_device()

    def power_off_to_break_during_unzip_image(self):
        self.fast_download_image()
        self.background_unzip_image()
        self.random_sleep(max_time=10)
        self.power_off_on_device()

    def fast_download_image(self):
        self.log.info('download image...')
        self.adb.executeShellCommand("busybox wget -q http://10.200.141.26/firmware/{0} -P /tmp/otaclient/fwupdate/".format(image_name))

    def background_slow_download_image(self):
        # expect to take 150 sec.
        self.log.info('slow download image...')
        self.adb.executeShellCommand("curl -s http://10.200.141.26/firmware/{0} --limit-rate 2m -o /tmp/otaclient/fwupdate/{0} &".format(image_name))

    def background_unzip_image(self):
        # expect to take 30 sec.
        self.log.info('slow unzip image...')
        self.adb.executeShellCommand("busybox unzip /tmp/otaclient/fwupdate/{} -d /tmp/otaclient/fwupdate/ &".format(image_name))

    def clean_up(self):
        self.log.info('Clean up ota folder')
        self.adb.executeShellCommand("rm -r /tmp/otaclient/fwupdate/*")

    def random_sleep(self, max_time):
        t = random.randint(1, max_time)
        self.log.info('sleep {} secs...'.format(t))
        time.sleep(t)

    def reboot_device(self):
        self.log.info('Reboot DUT.')
        self.adb.reboot_device_and_wait_boot_up()

    def power_off_on_device(self):
        self.log.info('Power off DUT.')
        self.power_switch.power_off(self.env.power_switch_port)
        self.log.info('Power on DUT.')
        self.power_switch.power_on(self.env.power_switch_port)
        self.adb.wait_for_device_boot_completed()


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        Script to try to break OTA Mount
        """)
    parser.add_argument('--mode', help='mode to break device' , default='reboot')
    if BreakOTAMount(parser).main():
        sys.exit(0)
    sys.exit(1)
