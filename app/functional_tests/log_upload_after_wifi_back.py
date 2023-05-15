# -*- coding: utf-8 -*-
""" Test cases for KAM-29233
    Logs will be uploaded after wifi disconnect and reconnect back.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"


# std modules
import sys
import os
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.restAPI import RestAPI
from platform_libraries.pyutils import retry
from platform_libraries.sumologicAPI import sumologicAPI

class LogUploadAfterWIFIBack(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Log Upload after wifi back'
    # Popcorn
    TEST_JIRA_ID = 'KAM-29233'

    SETTINGS = {
        'uut_owner': False
    }


    def init(self):
        pass


    def test(self):
        stdout, stderr = self.adb.executeShellCommand('echo wdcautotw`date +%s`')
        self.adb.executeShellCommand('touch /data/wd/diskVolume0/logs/upload/wd-safe/{}.log'.format(stdout.strip()))
        sumo_keyword = 'LogUploader {}'.format(stdout.strip())
        self.adb.executeShellCommand('logcat -c')
        # Turn off WiFi
        self.serial_client.serial_write('svc wifi disable')
        time.sleep(7)
        # Turn on WiFi
        self.serial_client.serial_write('svc wifi enable')
        time.sleep(30)
 
        # 1. Check logcat
        stdout, stderr = self.adb.executeShellCommand("logcat -d | grep -E 'LogUploader'.*'Uploading complete'")
        if 'Uploading complete' not in stdout:
            raise self.err.TestFailure('There is not "LogUploader: Uploading complete" in logcat.')

        # 2. Check sumologic
        self.log.info("sumo_keyword: '{}'".format(sumo_keyword))
        message_count = self._sumologic_search(sumo_keyword=sumo_keyword)
        if int(message_count) < 1 or int(message_count) > 3:
            self.log.error('message_count: {}'.format(message_count))
            raise self.err.TestFailure('Doesn\'t find keyword:"{}" or too many keywords in sumologic. (message_count:{})'.format(sumo_keyword, message_count))


    def _sumologic_search(self, sumo_keyword=None):
        try:
            sumologic = sumologicAPI()
            # The unit of relativeTime is "minute"
            self.result = sumologic.searchRQ(_adb_client=self.adb, searching=sumo_keyword, relativeTime=10, timezone="GMT")
            self.log.info(self.result)
            return self.result["messageCount"]
        except Exception as ex:
            self.log.error("Failed to send sumologic API: {}".format(ex))
            raise self.err.StopTest("Test failed related to sumologicAPI method.")


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Log Upload after wifi back Script ***
        Examples: ./run.sh functional_tests/log_upload_after_wifi_back.py --cloud_env qa1
                    --uut_ip 10.92.224.68 -dcll
                    --serial_server_ip 10.0.0.6 --serial_server_port 20000\
        """)
    test = LogUploadAfterWIFIBack(parser)
    resp = test.main()

    if resp:
        sys.exit(0)
    sys.exit(1)
