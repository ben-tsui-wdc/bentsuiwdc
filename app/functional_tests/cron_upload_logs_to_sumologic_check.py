# -*- coding: utf-8 -*-
""" Test cases to check cron job uploads device logs to Sumologic [KAM-17604]

    Technically, this test case is automatable.
    However, it needs two hours waiting for cron job to upload logs. (The check of first hour is for device in idle status after rebooting, the check of second hour is to ensure that the cron jobs works as expected.)
    As a result, classify this test case as "Not Automatable" after discussed with manual team Going Liang. 
"""
__author__ = "Andrew Tsai <andrew.tsai@wdc.com>"

# std modules
import sys
import time
import datetime

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.sumologicAPI import sumologicAPI


class CronUploadLogsToSumologicCheck(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Cron Upload Logs to Sumologic Check'
    # Popcorn
    TEST_JIRA_ID = 'KAM-17604'


    def init(self):
        self.logWaitingUploadPath = "/data/wd/diskVolume0/logs/upload"
        self.logAfterUploadPath = "/data/wd/diskVolume0/uploadedLogs"

    def before_test(self):
        self.environment = self.uut.get('environment')
        self.timeout = 60*5
        self.need_wait = True
        self.url_exist = False
        self.sumoURL = ""
        self.logname = ""
        self.jobID = ""
        self.counter = 0
        self.sumologicAPI = sumologicAPI()


    def test(self):
        # Skip test because dev1 environment has no hash mac address
        if self.environment == 'dev1':
            raise self.err.TestSkipped('Environment is {}, skipped the test !!'.format(self.environment))

        self.MAX_RETRIES = 5

        # Do reboot
        self.uut_owner.reboot_device()
        # Wait for reboot.
        self.log.info('Expect device do reboot in {} secs...'.format(self.timeout))
        if not self.adb.wait_for_device_to_shutdown(timeout=self.timeout):
            self.log.error('Reboot device: FAILED.')
            raise self.err.TestFailure('Reboot device failed')
        # Wait for boot up.
        self.log.info('Wait for device boot completed...')
        if not self.adb.wait_for_device_boot_completed(timeout=self.timeout):
            self.log.error('Device seems down.')
            raise self.err.TestFailure('Device seems down, device boot not completed')
        self.log.info('Device reboot completed.')

        # Make sure pip is turn on
        self.make_sure_pip_on()
        self.log.info("Waiting for 60 seconds.")
        time.sleep(60)
        self.log.info("Check if upload frequency and sumo url is set")
        self.log_check_upload_frequency()
        self.log_check_sumo_url()

        # Do reboot and waiting log upload to SumoLogic
        self.adb.reboot_device_and_wait_boot_up()
        self.sumologic_check_log()

    def make_sure_pip_on(self):
        pipstatus = self.adb.executeShellCommand("configtool pipstatus")[0]
        if 'true' in pipstatus:
            self.log.info("PIP is %s" %pipstatus)
        else:
            self.log.info("PIP is %s, try to turn on PIP." %pipstatus)
            response = self.uut_owner.enable_pip()
            self.log.info(response)
            if response.status_code != 200:
                raise self.err.TestFailure("Failed to turn on PIP.")
            else:
                pipstatus = self.adb.executeShellCommand("configtool pipstatus")[0]
                self.log.info("Update PIP status: %s" %pipstatus)

    def log_check_upload_frequency(self):
        retry = 1 
        while retry <= self.MAX_RETRIES:
            time.sleep(15)
            log_upload_frequency = self.adb.executeShellCommand("logcat -d | grep -E 'LogUploader'.*'Device log upload cadence'")[0]
            if log_upload_frequency == "":
                self.log.warning("Log Upload Frequency Check: Log message is empty, remaining {} retries".format(retry))
                retry += 1
            else:
                break
            if retry > self.MAX_RETRIES:
                log_upload_frequency, stderr = self.adb.executeShellCommand("grep -E 'LogUploader'.*'Device log upload cadence' /data/logs/wdlog.log")
                if log_upload_frequency == "":
                    raise self.err.TestError('log_check_upload_frequency is empty')

        if 'hour' not in log_upload_frequency:
            raise self.err.TestFailure('There is not keyword "1 hour" in logcat.')
        else:
            self.log.info('Log Check Upload Frequency: PASSED.')

    def log_check_sumo_url(self):
        log_upload_url = self.adb.executeShellCommand("logcat -d | grep -E 'success-get-sumologicURL'")[0]
        if log_upload_url == "":
            self.log.error('Log Check Sumo URL: FAILED.')
            raise self.err.TestFailure('Log upload frequency check failed')
        else:
            self.log.info('Log Check Sumo URL: PASSED.')
    
    def sumologic_check_log(self):
        # check sumo url
        sumologic_upload_URL = self.adb.check_sumo_URL()
        if sumologic_upload_URL == "":
            self.log.error("sumo URL is empty, please check out your ethernet setting.")
        else:
            self.sumoURL = sumologic_upload_URL
            self.url_exist = True
            self.log.info("URL:{0}".format(self.sumoURL))
        # Get hashed mac address
        if self.url_exist:
            try:
                MAX_RETRIES = 5
                retry = 1
                while retry <= MAX_RETRIES:
                    self.logname = self.adb.get_hashed_mac_address()
                    if not self.logname:
                        self.log.warning("Failed to get mac address, remaining {} retries".format(retry))
                        time.sleep(10)
                        retry += 1
                    else:
                        break
                self.log.info("Hashed mac address: %s" %self.logname)
            except:
                raise self.err.TestFailure("Test failed: cause we cannot parser hashed mac address to search log.")
        else:
            self.log.error("Failed to get hashed mac address.")
            raise self.err.TestFailure("Test failed cause Test Condition does not match.")
        # To prepare request members for sumologic API
        sumo_des = '_sourceName={} AND _sourceCategory={}'.format(self.logname, 'qa1/device/yodaplus/LogUploader')
        self.log.info("Searching rulse: %s" %sumo_des)

        try:
            self.result = self.sumologicAPI.searchRQ(_adb_client=self.adb, searching=sumo_des, relativeTime=10, timezone="GMT")
            self.counter = int(self.result["messageCount"])
            self.log.info(self.result)
        except Exception as ex:
            self.log.error("Failed to send sumologic API: {}".format(ex))
            raise self.err.TestFailure("Test Failed related to sumologicAPI method.")

        if self.counter <= 0:
            self.log.error("Test: Failed. Cannot find the log in sumologic website.")
            raise self.err.TestFailure("Test: Failed, log file is not found in sumologic database.")
        else:
            self.log.info("Cron Upload Logs to Sumologic Test: PASSED")
    
if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Cron Upload Logs to Sumologic Check Script ***
        Examples: ./run.sh functional_tests/cron_upload_logs_to_sumologic_check.py --uut_ip 10.92.224.68 -dcll\
        """)

    test = CronUploadLogsToSumologicCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
