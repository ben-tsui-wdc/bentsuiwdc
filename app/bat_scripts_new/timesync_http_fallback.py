# -*- coding: utf-8 -*-
""" Test cases to verify http fallback method to get time, if NTP requests are failing.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
import urllib2

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.pyutils import retry


class TimeSyncHTTPFallback(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'KAM-27500 - Time Sync With HTTP Fallback'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-27500'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': True
    }

    def init(self):
        self.drop_ntp_traffic = 'iptables -A OUTPUT -p udp --dport 123 -j DROP'
        self.addback_ntp_traffic = 'iptables -D OUTPUT -p udp --dport 123 -j DROP'
        self.stop_auto_time = 'settings put global auto_time 0 && settings put global auto_timezone 0'
        self.start_auto_time = 'settings put global auto_time 1 && settings put global auto_timezone 1'
        self.set_time_to_past = 'busybox date -s "@1523824222"'
        self.grep_networktime_log = 'logcat -d | grep -e NetworkTime'
        self.grep_mycloudtime_log = 'logcat -d | grep -e MyCloudTime'
        self.http_endpoint = 'http://downloads.mycloud.com/epoch'

    def test(self):
        firmware = self.uut.get('firmware')
        if firmware.startswith('5.0'):
            raise self.err.TestSkipped('Model firmware is {}, Code line is not implemented the http fallback method, '
                                       'skipped the test !!!'.format(firmware))
        try:
            retry(func=self.adb.is_machine_time_correct,
                    retry_lambda=lambda x: not x, delay=10, max_retry=60, log=self.log.warning)
        except Exception as ex:
            raise self.err.TestSkipped('Machine time is not correct after wait for 10 mins !!! '
                                       'Skipped the test !!! Exception: {}'.format(str(ex)))
        self.log.info('Stop auto time settings ...')
        self.adb.executeShellCommand(self.stop_auto_time)
        self.log.info('Set iptable rule to drop NTP packets on port 123 ...')
        self.adb.executeShellCommand(self.drop_ntp_traffic)
        self.log.info('Change device date to past ...')
        self.adb.executeShellCommand(self.set_time_to_past)
        # Wait to make sure machine time is not sync
        time.sleep(10)

        if self.adb.is_machine_time_correct():
            self.log.warning('Machine time is {}, set time to past failed, try again ...'.format(self.adb.get_machine_time))
            self.adb.executeShellCommand(self.set_time_to_past)
            if self.adb.is_machine_time_correct():
                raise self.err.TestSkipped('Machine time still synced with local time !!! Skipped the test !!!')
        self.adb.clean_logcat()
        try:
            retry(func=self.check_url_file_exists, url=self.http_endpoint,
                    retry_lambda=lambda x: not x, delay=10, max_retry=6, log=self.log.warning)
            self.log.info('Time sync server is available.')
        except Exception as ex:
            raise self.err.TestSkipped('Time Sync server is not available, SKipped the test !!! '
                                       'Exception: {}'.format(str(ex)))
        self.log.info('Start automatic time settings ...')
        self.adb.executeShellCommand(self.start_auto_time)
        # Wait for httpTimeSource occurred
        time.sleep(10)

        try:
            retry(func=self.confirm_machine_time_is_correct_and_retry_if_not_correct,
                    retry_lambda=lambda x: not x, delay=70, max_retry=5, log=self.log.warning)
        except Exception as ex:
            raise self.err.TestFailure('Machine time is not correct after retry 5 times to wait http fallback !!! '
                                       'Test Failed !!! Exception: {}'.format(str(ex)))
        result = self.adb.executeShellCommand(self.grep_networktime_log)[0]
        result2 = self.adb.executeShellCommand(self.grep_mycloudtime_log)[0]
        if not ('setHttpTime' and 'Sucessfully set time with') in result:
            raise self.err.TestFailure('"Successfully set time" logs not occurred !!!')

    def confirm_machine_time_is_correct_and_retry_if_not_correct(self):
        if self.adb.is_machine_time_correct():
            return True
        else:
            self.adb.executeShellCommand(self.stop_auto_time)
            self.adb.executeShellCommand(self.start_auto_time)
            return False

    def check_url_file_exists(self, url):
        request = urllib2.Request(url)
        request.get_method = lambda: 'HEAD'
        try:
            urllib2.urlopen(request)
            return True
        except (urllib2.HTTPError, urllib2.URLError) as e:
            self.log.warning('Message: {}'.format(e))
            return False

    def after_test(self):
        self.adb.executeShellCommand(self.addback_ntp_traffic)
        if not self.adb.is_machine_time_correct():
            self.log.warning('Machine time not sync, force to trigger NTP/HTTP updating.')
            self.adb.executeShellCommand(self.stop_auto_time)
            self.adb.executeShellCommand(self.start_auto_time)
            time.sleep(10)
            if not self.adb.is_machine_time_correct():
                self.log.warning('Force to trigger NTP updating failed !!!!!!!!!')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Time Sync for http fallback check Script ***
        Examples: ./run.sh bat_scripts_new/timesync_http_fallback.py --uut_ip 10.92.224.68\
        """)

    test = TimeSyncHTTPFallback(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
