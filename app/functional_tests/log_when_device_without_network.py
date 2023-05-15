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

class LogWhenDeviceWithoutNetwork(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KAM-19908: Logging functionality when device is not connected to network'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-19908'
    PRIORITY = 'critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {'uut_owner':True}
    #SETTINGS = {'uut_owner':False, 'adb':False}

    def declare(self):
        self.mac_address_hash = None


    def before_loop(self):
        pass


    def before_test(self):
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

        # Check if logs are generated under /data/logs
        stdout, stderr = self.adb.executeShellCommand('ls /data/logs')
        for item in ['crash.log', 'kernel.log', 'main.log', 'system.log', 'wdlog-safe.log', 'wdlog.log']:
            if item not in stdout:
                raise self.err.TestFailure('{} is not displayed in /data/logs'.format(item))

        # Check if logs are moved every 15 minutres
        move_log_timestamp_list = self._logcat_timestamp(cmd='logcat -d | grep LogUploader |grep data/move_logs.lock | grep finish')
        for index, item in enumerate(move_log_timestamp_list):
            if index+1 == len(move_log_timestamp_list):
                break
            if move_log_timestamp_list[index+1] - move_log_timestamp_list[index] < datetime.timedelta(minutes=14):
                self.log.warning('"move logs" occurred less than 15 minutes. However, it may be reasonable.')
            if move_log_timestamp_list[index+1] - move_log_timestamp_list[index] > datetime.timedelta(minutes=16):
                raise self.err.TestFailure('"move logs" doesn\'t occurr after 15 minutes.')

        # Ensure that PIP is enabled.
        response = self.uut_owner.enable_pip()
        stdout, stderr = self.adb.executeShellCommand('configtool pipstatus')
        if stdout.strip() == 'true':
            pass
        else:
            raise self.err.TestError('configtool pipstatus is still [{}] after enabling pipstatus via REST API'.format(stdout.strip()))

        # Create a dummy log
        dummy_log_timestamp = time.time()
        dummy_log_content = '[{}]{}. timestamp is {}'.format(self.TEST_JIRA_ID, self.TEST_NAME, dummy_log_timestamp)
        self.log.info("dummy_log_content: {}".format(dummy_log_content))
        stdout, stderr = self.adb.executeShellCommand('echo {} > /data/logs/wdlog-safe.log.999999'.format(dummy_log_content), timeout=120)

        # Break the network connectivity of DUT
        if 'yoda' in self.uut.get('model'):
            self.serial_client.disable_wifi()
        else:
            stdout, stderr = self.adb.executeShellCommand('mount -o remount,rw /system')
            stdout, stderr = self.adb.executeShellCommand('mv /system/bin/ifdu.sh /system/bin/ifdu_bak.sh')
            if "Read-only file system" in stdout:
                raise self.err.StopTest('Failed to rename /system/bin/ifdu.sh')
            self.log.info("Disable network connectivity...")
            self.serial_client.serial_write('ifconfig eth0 down')

        # Confirm if the network interface is truly disabled.
        time.sleep(5)
        if self.adb.check_adb_connectable():
            raise self.err.StopTest("The network interface of DUT is not disabled.")

        # Check if logs are moved to /data/wd/diskVolume0/logs/upload even without network connectivity
        starting_time = time.time()
        found_content_flag = False
        while (time.time() < (starting_time + 1200)): #1200 seconds is 15 minutes + 5 minutes as buffer.
            result = self.serial_client.serial_cmd('grep -r {} /data/wd/diskVolume0/logs/upload/wd-safe/*'.format(dummy_log_timestamp))
            if dummy_log_content in result:
                self.log.info('dummy_log_content is found successfully in {}'.format(result))
                found_content_flag = True
                break
            else:
                print "Wait for moving logs for more 90 seconds. Wait up to 20 minutes."
                time.sleep(90)
        if not found_content_flag:
            raise self.err.TestFailure('The dummy log "wdlog-safe.log.999999" is NOT moved to /data/wd/diskVolume0/logs/upload/wd-safe.')

        # Restore the network connectivity of DUT
        if 'yoda' in self.uut.get('model'):
            self.serial_client.enable_wifi()
            print "Wait for DUT network interface up"
            time.sleep(20)
        else:
            self.serial_client.serial_write('ifconfig eth0 up && echo FINISHED')
            self.serial_client.serial_wait_for_string('FINISHED')
            self.log.info("Enable network connectivity...")
            print "Wait for DUT network interface up"
            time.sleep(20)
            stdout, stderr = self.adb.executeShellCommand('mv /system/bin/ifdu_bak.sh /system/bin/ifdu.sh')

        # Upload logs forcibly after network connectivity is restored.
        stdout, stderr = self.adb.executeShellCommand('move_upload_logs.sh -n', timeout=180)  # Upload logs
        print 'Wait for 5 minutes to upload logs to Sumo'
        time.sleep(300)
        # Check Sumologic
        sumologic = sumologicAPI()
        sumo_des = '_sourceName={} AND {} AND {}'.format(self.mac_address_hash, self.TEST_JIRA_ID, dummy_log_timestamp)
        self.log.info("Searching rule: %s" %sumo_des)
        try:
            self.result = sumologic.searchRQ(_adb_client=self.adb, searching=sumo_des, relativeTime=10, timezone="GMT")
            self.counter = int(self.result["messageCount"])
        except Exception as ex:
            raise self.err.TestError("Failed to send sumologic API: {}".format(ex))
        if self.counter != 1:
            raise self.err.TestFailure("Dummy_log({}) is not found in sumologic database after network connectivity of DUT is restored.".format(dummy_log_content))


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
        # Restore the network connectivity of DUT again to ensure that DUT is recovered from broken network connectivity. 
        # Because if there is any failure occurred in def test() stage, script may not recover DUT in time. 
        if not self.adb.check_adb_connectable():
            if 'yoda' in self.uut.get('model'):
                self.serial_client.enable_wifi()
                print "Wait for DUT network interface up"
                time.sleep(20)
            else:
                self.serial_client.serial_write('ifconfig eth0 up && echo FINISHED')
                self.serial_client.serial_wait_for_string('FINISHED')
                self.log.info("Enable network connectivity...")
                print "Wait for DUT network interface up"
                time.sleep(20)
                stdout, stderr = self.adb.executeShellCommand('mv /system/bin/ifdu_bak.sh /system/bin/ifdu.sh')


    def after_loop(self):
        pass


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        Examples: ./run.sh functional_tests/log_when_device_without_network.py --uut_ip 10.0.0.28 --cloud_env qa1 --dry_run --serial_server_ip 10.0.0.15 --serial_server_port 20001 --debug_middleware\
         --disable_clean_logcat_log """)

    test = LogWhenDeviceWithoutNetwork(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)