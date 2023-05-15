# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import datetime
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.sumologicAPI import sumologicAPI

class LogNotUploadWhenPIPOff(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KAM-18927: Logs dont uploaded when PIP is disabled'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-18927'
    PRIORITY = 'critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {'uut_owner':True}


    def declare(self):
        self.mac_address_hash = None


    def before_loop(self):
        pass


    def before_test(self):

        cloud_env = self.adb.get_environment()
        cloud_variant = self.adb.get_variant()

        stdout, stderr = self.adb.executeShellCommand('getprop wd.log.check_pip')
        check_pip = stdout.strip()

        # Check [wd.log.check_pip]
        if cloud_env == 'dev1' or  (cloud_env == 'qa1' and cloud_variant == 'userdebug'):
            if check_pip == 'false':
                raise self.err.TestSkipped('cloud_env:{} and cloud_variant:{} will always upload logs to sumo by default, so skip the test'.format(cloud_env, cloud_variant))
            else:
                raise self.err.TestFailure('cloud_env:{} and cloud_variant:{}, but [wd.log.check_pip] is {}'.format(cloud_env, cloud_variant, check_pip))
        else:
            if check_pip == 'true':
                pass
            else:
                raise self.err.TestFailure('cloud_env:{} and cloud_variant:{}, but [wd.log.check_pip] is {}'.format(cloud_env, cloud_variant, check_pip))

        # Check [debug.log.sumologic_url]
        stdout, stderr = self.adb.executeShellCommand('getprop debug.log.sumologic_url')

        # Get mac_address_hash of DUT
        if 'yoda' in self.uut.get('model'):
            interface = 'wlan0'
        else:
            interface = 'eth0'
        MAX_RETRIES = 3
        retry = 1
        while retry <= MAX_RETRIES:
            self.mac_address_hash = self.adb.get_hashed_mac_address(interface=interface)
            if not self.mac_address_hash:
                self.log.warning("Failed to get mac address, remaining {} retries".format(retry))
                time.sleep(10)
                retry += 1
            else:
                break
        if not self.mac_address_hash:
            raise self.err.TestError("Failed to get mac address, remaining {} retries".format(MAX_RETRIES))


    def test(self):

        response = self.uut_owner.disable_pip()
        stdout, stderr = self.adb.executeShellCommand('configtool pipstatus')
        if stdout.strip() == 'false':
            pass
        else:
            raise self.err.TestError('configtool pipstatus is still [{}] after disabling pipstatus via REST API'.format(stdout.strip()))

        # Check if logs are moved every 15 minutres
        move_log_timestamp_list = self._logcat_timestamp(cmd='logcat -d | grep LogUploader |grep data/move_logs.lock | grep finish')
        for index, item in enumerate(move_log_timestamp_list):
            if index+1 == len(move_log_timestamp_list):
                break
            if move_log_timestamp_list[index+1] - move_log_timestamp_list[index] < datetime.timedelta(minutes=14):
                self.log.warning('"move logs" occurred less than 15 minutes. However, it may be reasonable.')
            if move_log_timestamp_list[index+1] - move_log_timestamp_list[index] > datetime.timedelta(minutes=16):
                raise self.err.TestFailure('"move logs" doesn\'t occurr after 15 minutes.')


        # Create a dummy_log to test if logs is not uploaded to Sumo.
        dummy_log_timestamp = time.time()
        dummy_log_content = '[{}]{}. timestamp is {}'.format(self.TEST_JIRA_ID, self.TEST_NAME, dummy_log_timestamp)
        self.log.info("Dummy log message: {}".format(dummy_log_content))
        stdout, stderr = self.adb.executeShellCommand('echo {} > /data/wd/diskVolume0/logs/upload/wd-safe/dummy_log_{}'.format(dummy_log_content, dummy_log_timestamp), timeout=120)

        # Check if "uploading logs" is actually blocked as PIP is disabled.
        stdout, stderr = self.adb.executeShellCommand('logcat -c', timeout=120)
        stdout, stderr = self.adb.executeShellCommand('move_upload_logs.sh -a', timeout=180)  # Move logs
        stdout, stderr = self.adb.executeShellCommand('move_upload_logs.sh -n', timeout=180)  # Upload logs
        # 1)
        stdout, stderr = self.adb.executeShellCommand("logcat -d | grep LogUploader |grep 'PIP is disabled' |wc -l", timeout=120)
        if int(stdout.strip()) < 1:
            raise self.err.TestFailure('There is no "PIP is disabled" message in logcat after trying to upload logs.')
        # 2)
        stdout, stderr = self.adb.executeShellCommand("ls /data/wd/diskVolume0/uploadedLogs/dummy_log_{}".format(dummy_log_timestamp))
        if 'No such file or directory' not in stdout:
            raise self.err.TestFailure('Find dummy_log_{} in /data/wd/diskVolume0/uploadedLogs.'.format(dummy_log_timestamp))
        # 3) Check Sumologic. It is expected that the dummy_log won't be uploaded to Sumo.
        print 'Wait for 5 minutes to upload logs to Sumo'
        time.sleep(300)
        
        sumologic = sumologicAPI()
        sumo_des = '_sourceName={} AND {} AND {}'.format(self.mac_address_hash, self.TEST_JIRA_ID, dummy_log_timestamp)
        self.log.info("Searching rule: %s" %sumo_des)
        try:
            self.result = sumologic.searchRQ(_adb_client=self.adb, searching=sumo_des, relativeTime=10, timezone="GMT")
            self.counter = int(self.result["messageCount"])
        except Exception as ex:
            raise self.err.TestError("Failed to send sumologic API: {}".format(ex))
        if self.counter > 0:
            raise self.err.TestFailure("Dummy_log[{}] is found in sumologic database even if PIP is disable.".format(dummy_log_content))

        
    def _logcat_timestamp(self, cmd=None):
        logcat_timestamp_list = []
        stdout, stderr = self.adb.executeShellCommand(cmd, timeout=120)
        for element in stdout.split('\n'):
            if element:
                # Conversion from string to "datetime"
                datetime_format = datetime.datetime.strptime(element.split()[0], '%Y-%m-%dT%H:%M:%S.%fZ')
                logcat_timestamp_list.append(datetime_format)
            
        return logcat_timestamp_list


    def after_test(self):
        pass


    def after_loop(self):
        pass


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        Examples: ./run.sh functional_tests/log_not_uploaded_when_pip_off.py --uut_ip 10.0.0.28 --cloud_env qa1 --dry_run --debug_middleware\
         --disable_clean_logcat_log """)

    test = LogNotUploadWhenPIPOff(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)