# -*- coding: utf-8 -*-
""" Test cases to check Remove Personal Identification Information from Platform verification Check.
"""
__author__ = "Ben Lin <ben.lin@wdc.com>"

# std modules
import sys
import time
import argparse
import os

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from bat_scripts_new.usb_auto_mount import UsbAutoMount
from bat_scripts_new.usb_slurp_backup_file import UsbSlurpBackupFile
from platform_libraries.restAPI import RestAPI

class RemovePersonalInfomation(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Remove Personal Identification Information from Platform verification'
    # Popcorn
    TEST_JIRA_ID = 'KAM-18208'

    SETTINGS = {
        'uut_owner': True
    }

    start = time.time()

    def declare(self):
        self.timeout = 300

    def test(self):
        self.check_device_bootup()
        self.adb.clean_logcat()

        UsbAutoMount(self).test()
        UsbSlurpBackupFile(self).test()

        logcat_string = self.adb.executeShellCommand('logcat -b wdlog-safe -d')[0]

        check_list = ["User name", "Personal name", "User password", "BSSID", "Access tokens", "MAC address",
            "Security code", "Directory and file name", "USB drive volume/label name", "SSIDs"]

        for item in check_list:
            if item in logcat_string:
                raise self.err.TestFailure('Get Personal Information: {}'.format(item))

        # Install a 3rd App
        self.adb.clean_logcat()
        app_id ='com.elephantdrive.ibi'
        owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password)
        owner.install_app(app_id=app_id)

        logcat_string = self.adb.executeShellCommand('logcat -b wdlog-safe -d')[0]

        check_list = ["User", "Folder", "File"]

        for item in check_list:
            if item in logcat_string:
                raise self.err.TestFailure('Get Personal Information: {}'.format(item))

        owner.uninstall_app(app_id=app_id)

    def check_device_bootup(self):
        # check device boot up
        while not self.is_timeout(self.timeout):
            boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed', timeout=10)[0]
            if '1' in boot_completed:
                self.log.info('Boot completed')
                break
            time.sleep(2)

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Remove Personal Identification Information from Platform verification Check Script ***
        Examples: ./run.sh functional_tests/remove_Personal_information.py --uut_ip 10.92.224.68\
        """)

    test = RemovePersonalInfomation(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
