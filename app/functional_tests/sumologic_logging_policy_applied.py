# -*- coding: utf-8 -*-
""" Test cases to check Logging policy files applied on uploaded logs.
"""
__author__ = "Ben Lin <ben.lin@wdc.com>"

import sys
import time
import datetime
import argparse
import json

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.sumologicAPI import sumologicAPI


class SumologicLogPolicyApplied(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Logging policy files applied on uploaded logs'
    # Popcorn
    TEST_JIRA_ID = 'KAM-19734'

    SETTINGS = {
        'uut_owner': True
    }

    start = time.time()
    timeout = 300

    def before_test(self):
        # Skip test because dev1 environment has no hash mac address
        if self.uut.get('environment') == 'dev1':
            raise self.err.TestSkipped('Environment is {}, skipped the test !!'.format(self.uut.get('environment')))

        # Download the latest policy
        self.adb.executeShellCommand('check_logging_policy.sh')

        if 'yoda' in self.uut.get('model'):
            interface = 'wlan0'
        else:
            interface = 'eth0'
        MAX_RETRIES = 5
        retry = 1
        while retry <= MAX_RETRIES:
            self.mac_address_hash = self.adb.get_hashed_mac_address(interface=interface)
            if not self.mac_address_hash:
                self.log.warning("Failed to get mac address, remaining {} retries".format(retry))
                time.sleep(10)
                retry += 1
            else:
                break

        self.check_device_bootup()
        self.uut_owner.enable_pip()


    def test(self):        
        # Find logging_policy_v2.txt
        logging_policy = self.adb.executeShellCommand(cmd='find /data/logs/ -name logging_policy*.txt')[0].strip()
        if not 'logging_policy' in logging_policy:
            raise self.err.TestFailure("Can not find logging_policy file!")

        # Find logs_black_list_v2.txt
        logs_black_list = self.adb.executeShellCommand(cmd='find /data/logs/ -name logs_black_list*.txt')[0].strip()
        if not 'logs_black_list' in logs_black_list:
            raise self.err.TestFailure("Can not find logs_black_list file!")

        logs_black_content = self.adb.executeShellCommand('cat {} | grep sed'.format(logs_black_list))[0]
        logs_black_array = logs_black_content.split("\n")
        for _log in logs_black_array:
            if not _log:
                continue
            log_time = self.adb.executeShellCommand(cmd='date +"%Y-%m-%eT%H:%M:%S.000Z"')[0].strip() #2019-05-30T08:28:18.765Z
            self.log.info("log_time: {}".format(log_time))
            log_type = _log.split(":")[0]
            self.log.info("log_type: {}".format(log_type))

            # busybox sed '/auth0/d;/LinkAddresses/d;/audit/d'
            black_str = _log.split("sed ")[1].strip("'").replace("/d", "").replace(";", "").replace("\'", "")
            self.log.info("black_str: {}".format(black_str))
            for b in black_str.split("/"):
                if not b:
                    continue
                self.log.info("black: {}".format(b))
                if log_type == "main" or log_type == "system":
                    self.adb.executeShellCommand("echo '{}  1000  1000 I LogUploader: Black_Log_Test: {}_{}' >> /data/logs/{}.log".format(log_time, b, log_type, log_type))
                elif log_type == "kernel":
                    self.adb.executeShellCommand("echo '{}     0     0 W RTW_WD  : Black_Log_Test: {}_{}' >> /data/logs/{}.log".format(log_time, b, log_type, log_type))
                elif log_type == "wdlog":
                    self.adb.executeShellCommand("echo '{}  1000  1000 I restsdk : Black_Log_Test: {}_{}' >> /data/logs/{}.log".format(log_time, b, log_type, log_type))

        # Do reboot and waiting log upload to SumoLogic
        self.adb.reboot_device_and_wait_boot_up()

        sumo_des = '(_sourceName={}) AND Black_Log_Test'.format(self.mac_address_hash)
        counter = self.sumologic_search(sumo_des=sumo_des)
        if counter > 0:
            raise self.err.TestFailure("Find Black string in Sumologic!")


    def sumologic_search(self, sumo_des=None):
        try:
            sumologic = sumologicAPI()
            self.result = sumologic.searchRQ(_adb_client=self.adb, searching=sumo_des, relativeTime=10, timezone="GMT")
            counter = int(self.result["messageCount"])
            self.log.info(self.result)
        except Exception as ex:
            self.log.error("Failed to send sumologic API: {}".format(ex))
            raise self.err.TestFailure("Test failed related to sumologicAPI method.")
        return counter


    def check_device_bootup(self):
        # check device boot up
        while not self.is_timeout(self.timeout):
            if self.adb.check_platform_bootable():
                self.log.info('Boot completed')
                break
            time.sleep(5)


    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Logging policy files applied on uploaded logs Check Script ***
        Examples: ./run.sh functional_tests/sumologic_logging_policy_applied.py --uut_ip 10.92.224.68\
        """)

    test = SumologicLogPolicyApplied(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
