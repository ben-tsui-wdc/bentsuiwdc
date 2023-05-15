# -*- coding: utf-8 -*-
""" Test cases to check cron job moves device logs every 15 minutes when disk is mounted.
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


class CronJobMoveLog(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Cron job moves device logs Check'
    # Popcorn
    TEST_JIRA_ID = 'KAM-17602'

    SETTINGS = {
        'uut_owner': False
    }

    start = time.time()

    def declare(self):
        self.timeout = 300

    def test(self):
        self.check_device_bootup()
        self.check_restsdk_service()
        self.check_disk_mounted()

        self.log.info('Create default main.log.01 file')
        self.adb.executeShellCommand('echo "blanka_test" >> /data/logs/main.log.01')

        self.log.info('Wait main.log file created')
        while not self.is_timeout(60*5):
            find_main_logs_file = self.adb.executeShellCommand(cmd='find /data/logs/ -name main.log', consoleOutput=False)[0].strip()
            self.log.info('find_main_logs_file : {}'.format(find_main_logs_file))
            if 'main.log' in find_main_logs_file:
                self.log.info('detect log files(main.log)')
                break
            time.sleep(10)

        # check Rotated logs file has been created
        while not self.is_timeout(60*5):
            find_main_logs_rotate_file = self.adb.executeShellCommand(cmd='find /data/logs/ -name main.log.01', consoleOutput=False)[0].strip()
            self.log.info('find_main_logs_rotate_file : {}'.format(find_main_logs_rotate_file))
            if 'main.log.01' in find_main_logs_rotate_file:
                self.log.info('detect rotated log files(main.log.01)')
                break
            else:
                time.sleep(10)

        # Get current file list of upload file
        ls_upload_logs_list1 = self.adb.executeShellCommand(cmd='find /data/wd/diskVolume0/logs/upload/main -name *_main_*.log', consoleOutput=False)[0].strip()
        ls_upload_logs_list1 = ls_upload_logs_list1.split('\r\n')
        self.log.info('ls_upload_logs_list1 = {}'.format(ls_upload_logs_list1))

        self.log.info('Wait 15 minutes')
        check_point1 = False
        check_point2 = False
        while not self.is_timeout(60*15):
             # check Rotated logs file has been moved
            if not check_point1:
                find_main_logs_rotate_file = self.adb.executeShellCommand(cmd='find /data/logs/ -name main.log.01', consoleOutput=False)[0].strip()
                if 'main.log.01' not in find_main_logs_rotate_file:
                    self.log.info('/data/logs/ no longer has rotated log files')
                    check_point1 = True
                else:
                    time.sleep(10)
                    continue

            if not check_point2:
                 # Get current file list of upload file
                ls_upload_logs_list2 = self.adb.executeShellCommand(cmd='find /data/wd/diskVolume0/logs/upload/main -name *_main_*.log', consoleOutput=False)[0].strip()
                ls_upload_logs_list2 = ls_upload_logs_list2.split('\r\n')
                self.log.info('ls_upload_logs_list2 = {}'.format(ls_upload_logs_list2))

                for name in ls_upload_logs_list2:
                    if name in ls_upload_logs_list1:
                        continue
                    else:
                        self.log.info('Log file moved')
                        check_point2 = True
                        break

            if check_point1 and check_point2:
                break

            if check_point1 and check_point2:
                self.log.info('Log file moved')
                break
            else:
                raise self.err.TestFailure("Check move log failed!!")

    def check_device_bootup(self):
        # check device boot up
        while not self.is_timeout(self.timeout):
            boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed', timeout=10)[0]
            if '1' in boot_completed:
                self.log.info('Boot completed')
                break
            time.sleep(2)

    def check_disk_mounted(self):
        # check disk mounted
        while not self.is_timeout(self.timeout):
            disk_mounted= self.adb.executeShellCommand('getprop sys.wd.disk.mounted', timeout=10)[0]
            if '1' in disk_mounted:
                self.log.info('Disk mounted')
                break
            time.sleep(5)

    def check_restsdk_service(self):
        self.start = time.time()
        while not self.is_timeout(60*3):
            # Execute command to check restsdk is running
            grepRest = self.adb.executeShellCommand('ps | grep restsdk')[0]
            if 'restsdk-server' in grepRest:
                self.log.info('Restsdk-server is running\n')
                break
            time.sleep(3)
        else:
            raise self.err.TestFailure("Restsdk-server is not running after wait for 3 mins")

        # Sometimes following error occurred if making REST call immediately after restsdk is running.
        # ("stdout: curl: (7) Failed to connect to localhost port 80: Connection refused)
        # Add retry mechanism for get device info check
        self.start = time.time()
        while not self.is_timeout(60*2):
            # Execute sdk/v1/device command to check device info to confirm restsdk service running properly
            curl_localHost = self.adb.executeShellCommand('curl localhost/sdk/v1/device?pretty=true')[0]
            if 'Connection refused' in curl_localHost:
                self.log.warning('Connection refused happened, wait for 5 secs and try again...')
                time.sleep(5)
            else:
                break
        else:
            raise self.err.TestFailure("Connected to localhost failed after retry for 2 mins ...")

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Cron job moves device logs Check Script ***
        Examples: ./run.sh functional_tests/cron_move_log.py --uut_ip 10.92.224.68\
        """)

    test = CronJobMoveLog(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
