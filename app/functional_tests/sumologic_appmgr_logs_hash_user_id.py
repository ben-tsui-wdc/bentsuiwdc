# -*- coding: utf-8 -*-
""" Test cases to check [ANALYTICS] Hash user id in appmgr logs instead of general MASKED.
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


class SumologicAppmgrHashUserID(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KAM-19735: [ANALYTICS] Hash user id in appmgr logs instead of general MASKED'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-19735,KAM-21411'
    PRIORITY = 'critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {'uut_owner':True}


    def declare(self):
        self.app_id = 'None'


    def init(self):
        # Determine the app_id
        if self.app_id == 'None':
            if 'yoda' in self.uut.get('model'):
                self.app_id ='com.wdc.importapp.ibi'
            else:
                self.app_id ='com.wdc.importapp'


    def before_test(self):
        # Skip test because dev1 environment has no hash mac address
        if self.uut.get('environment') == 'dev1':
            raise self.err.TestSkipped('Environment is {}, skipped the test !!'.format(self.uut.get('environment')))

        self.app_info = []
        self.uut_owner.uninstall_app(app_id=self.app_id)

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

        self.adb.clean_logcat()


    def test(self):
        self.uut_owner.install_app(app_id=self.app_id)
        self.start = time.time()

        while not self.is_timeout(300):
            logcat_string = self.adb.executeShellCommand('logcat -d | grep appmgr | grep userId | grep add.*user.*success')[0]
            if logcat_string:
                logcat_array = logcat_string.split("\n")
                if len(logcat_array) >= 2:
                    for _log in logcat_array:
                        if not _log:
                            continue
                        info = _log.split(" : ", 1)
                        self.app_info.append(json.loads(info[1]))

                    self.log.info("app_info: {}".format(self.app_info))
                    break
            time.sleep(10)

        if len(self.app_info) == 0:
            raise self.err.StopTest("Can not get appmgr log by command logcat")

        # Upload logs to Sumologic
        self.adb.executeShellCommand("move_upload_logs.sh -i")
        self.adb.executeShellCommand("move_upload_logs.sh -n")

        self.log.info("Wait for 300 seconds for uploading log to sumo...")
        time.sleep(300)


        user_id = self.uut_owner.get_user_id()

        for ai in self.app_info:
            sumo_des = '_sourceName={} AND _sourceCategory=qa1/device/{}/appmgr userId {} appID {} {}'.format(
                self.mac_address_hash,
                self.uut.get('model'),
                ai['userId'].replace('|', '%7C'),
                self.app_id,
                ai['msgid'],
            )

            self.log.info('sumo_des: {}'.format(sumo_des))

            counter = self.sumologic_search(sumo_des=sumo_des)
            if ai['userId'] == self.uut_owner.get_user_id(): # userID is unhashed
                if counter > 0:
                    raise self.err.TestFailure("Find unhashed userID in Sumologic: {}".format(ai['userId']))
            else: # userID is hashed
                if counter == 0:
                    raise self.err.TestFailure("Can not find hashed userID in Sumologic: {}".format(ai['userId']))


    def after_test(self):
        self.uut_owner.uninstall_app(app_id=self.app_id)


    def sumologic_search(self, sumo_des=None):
        try:
            sumologic = sumologicAPI()
            self.result = sumologic.searchRQ(_adb_client=self.adb, searching=sumo_des, relativeTime=10, timezone="GMT", MAX_RETRIES=12)
            counter = int(self.result["messageCount"])
            self.log.info(self.result)
        except Exception as ex:
            self.log.error("Failed to send sumologic API: {}".format(ex))
            raise self.err.TestFailure("Test failed related to sumologicAPI method.")

        return counter


    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** [ANALYTICS] Hash user id in appmgr logs instead of general MASKED Check Script ***
        Examples: ./run.sh functional_tests/sumologic_appmgr_logs_hash_user_id.py --uut_ip 10.92.224.68\
        """)

    parser.add_argument('--app_id', help='app_id of MCH/ibi', default='None')

    test = SumologicAppmgrHashUserID(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
