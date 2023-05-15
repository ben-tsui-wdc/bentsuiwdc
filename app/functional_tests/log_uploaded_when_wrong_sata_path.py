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

class LogUploadedWhenWrongSataPath(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KAM-33646: Logs can be uploaded when wrong SATA path'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-33646'
    PRIORITY = 'major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {'uut_owner':True}


    def declare(self):
        self.skip_test_if_sata_path_is_correct = True
        self.mac_address_hash = None
        self.number_of_wrong_sata_path = 0


    def before_loop(self):
        pass


    def before_test(self):
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
        # Check if SATA path is correct
        stdout, stderr = self.adb.executeShellCommand('ls /sys/bus/scsi/devices/0:0:0:0/block')
        print "\n\n\n\nSATA path /sys/bus/scsi/devices/0:0:0:0/block is [{}]. \n\n\n\n".format(stdout.strip())
        if "sataa" == stdout.strip() or "satab" == stdout.strip():
            if self.skip_test_if_sata_path_is_correct:
                stdout, stderr = self.adb.executeShellCommand('busybox nohup reboot')
                if not self.adb.wait_for_device_to_shutdown():
                    raise self.err.TestFailure('Device rebooting Failed !!')
                self.log.info('Device rebooting ...')
                if not self.adb.wait_for_device_boot_completed():
                    raise self.err.TestFailure('Device bootup Failed !!')
            return
        else:
            self.number_of_wrong_sata_path += 1
            print "\n\n\n\nExecuting following test\n\n\n\n"

        # Check DUT standby status
        if 'pelican' in self.uut.get('model'):
            stdout, stderr = self.adb.executeShellCommand('getprop | grep standby')
            if '[wd.sys.standby]: [1]' not in stdout:
                self.log.warning("getprop standby status is not correct.")

        # Check logcat message
        stdout, stderr = self.adb.executeShellCommand("logcat -d |grep 'Disk0 block name'")
        if "Disk0 block name is empty, assign to sataa" not in stdout:
            self.log.warning("There is no message (Disk0 block name is empty, assign to sataa) displayed in logcat .")

        # Create a dummy_log to test if logs could be still uploaded to Sumo successsfully.
        dummy_log_timestamp = time.time()
        dummy_log_content = '[{}]{}. timestamp is {}'.format(self.TEST_JIRA_ID, self.TEST_NAME, dummy_log_timestamp)
        self.log.info("Dummy log message: {}".format(dummy_log_content))
        stdout, stderr = self.adb.executeShellCommand('echo {} > /data/wd/diskVolume0/logs/upload/wd-safe/dummy_log_{}'.format(dummy_log_content, dummy_log_timestamp), timeout=120)

        # Upload logs
        stdout, stderr = self.adb.executeShellCommand('move_upload_logs.sh -n', timeout=180)
        print "Wait for more 2 minute to move logs from '/data/wd/diskVolume0/logs/upload' to '/data/wd/diskVolume0/uploadedLogs'"
        time.sleep(120)
        # Check if dummy log is moved to /data/wd/diskVolume0/uploadedLogs successfully
        stdout, stderr = self.adb.executeShellCommand("ls /data/wd/diskVolume0/uploadedLogs/dummy_log_{}".format(dummy_log_timestamp))
        if 'No such file or directory' in stdout:
            self.log.warning('Cannot find dummy_log_{} in /data/wd/diskVolume0/uploadedLogs.'.format(dummy_log_timestamp))
        print 'Wait for more 3 minutes to upload logs to Sumo'
        time.sleep(180)
        # Check Sumologic. It is expected that the dummy_log will be uploaded to Sumo.
        sumologic = sumologicAPI()
        sumo_des = '_sourceName={} AND {} AND {}'.format(self.mac_address_hash, self.TEST_JIRA_ID, dummy_log_timestamp)
        self.log.info("Searching rule: %s" %sumo_des)
        try:
            self.result = sumologic.searchRQ(_adb_client=self.adb, searching=sumo_des, relativeTime=10, timezone="GMT")
            self.counter = int(self.result["messageCount"])
        except Exception as ex:
            raise self.err.TestError("Failed to send sumologic API: {}".format(ex))
        if self.counter != 1:
            raise self.err.TestFailure("Dummy_log[{}] is NOT found in sumologic database.".format(dummy_log_content))





    def after_test(self):
        pass


    def after_loop(self):
        print "\n\n\n###############\n"
        print "Total iteration: {}".format(self.env.iteration)
        print "Total number_of_wrong_sata_path: {}".format(self.number_of_wrong_sata_path)
        print "\n###############\n\n\n"


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        Examples: ./run.sh functional_tests/log_not_uploaded_when_pip_off.py --uut_ip 10.0.0.28 --cloud_env qa1 --dry_run --debug_middleware\
         --disable_clean_logcat_log """)
    #parser.add_argument('--skip_test_if_sata_path_is_correct', action='store_true')

    test = LogUploadedWhenWrongSataPath(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)