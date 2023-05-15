# -*- coding: utf-8 -*-
""" Test cases to verify http fallback method to get time, if NTP requests are failing.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
import urllib2
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.pyutils import retry


class TimeSyncHTTPFallback(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-215 - Time Sync With HTTP Fallback'
    TEST_JIRA_ID = 'KDP-215, KDP-435'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.drop_ntp_traffic = 'iptables -A OUTPUT -p udp --dport 123 -j DROP'
        self.addback_ntp_traffic = 'iptables -D OUTPUT -p udp --dport 123 -j DROP'
        self.start_time_sync = 'sntp_setup.sh'
        self.set_time_to_past = 'busybox date -s "@1523824222"'
        self.grep_networktime_log = 'cat /var/log/analyticpublic.log* | grep -e NetworkTime'
        self.no_addback = False
        self.http_endpoint = self.ssh_client.get_service_urls_from_cloud(quiet=True).get('service.epoch.url')

    def test(self):
        try:
            retry(func=self.ssh_client.check_machine_time_correct,
                    retry_lambda=lambda x: not x, delay=10, max_retry=60, log=self.log.warning)
        except Exception as ex:
            self.no_addback = True
            raise self.err.TestSkipped('Machine time is not correct after wait for 10 mins !!! '
                                       'Skipped the test !!! Exception: {}'.format(str(ex)))
        self.log.info('Set iptable rule to drop NTP packets on port 123 ...')
        self.ssh_client.execute(self.drop_ntp_traffic)
        self.log.info('Change device date to past ...')
        self.ssh_client.execute(self.set_time_to_past)
        # Wait to make sure machine time is not sync
        time.sleep(10)

        if self.ssh_client.check_machine_time_correct():
            self.log.warning('Machine time is {}, set time to past failed, try again ...'.format(self.ssh_client.get_machine_time()))
            self.ssh_client.execute(self.set_time_to_past)
            if self.ssh_client.check_machine_time_correct():
                raise self.err.TestSkipped('Machine time still synced with local time !!! Skipped the test !!!')
        self.ssh_client.clean_device_logs()
        try:
            retry(func=self.check_url_file_exists, url=self.http_endpoint,
                    retry_lambda=lambda x: not x, delay=10, max_retry=6, log=self.log.warning)
            self.log.info('Time sync server is available.')
        except Exception as ex:
            raise self.err.TestSkipped('Time Sync server is not available, SKipped the test !!! '
                                       'Exception: {}'.format(str(ex)))
        self.log.info('Start automatic time settings ...')
        self.ssh_client.execute(self.start_time_sync)
        # Wait for httpTimeSource occurred
        time.sleep(10)

        try:
            retry(func=self.confirm_machine_time_is_correct_and_retry_if_not_correct,
                    retry_lambda=lambda x: not x, delay=70, max_retry=5, log=self.log.warning)
        except Exception as ex:
            raise self.err.TestFailure('Machine time is not correct after retry 5 times to wait http fallback !!! '
                                       'Test Failed !!! Exception: {}'.format(str(ex)))
        self.check_networktime_logs()

    def check_networktime_logs(self):
        self.log.info('Start to check NetworkTime logs ...')
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60):
            result = self.ssh_client.execute_cmd(self.grep_networktime_log)[0]
            if result:
                break
            else:
                self.log.info('Did not get NetworkTime logs, try again ...')
                time.sleep(5)
        else:
            raise self.err.TestFailure('Failed to get NetworkTime logs.')
        if not 'Successfully set time' in result or 'Failed to get time from http source' in result:
            raise self.err.TestFailure('Query logs not occurred! Test Failed!')

    def confirm_machine_time_is_correct_and_retry_if_not_correct(self):
        if self.ssh_client.check_machine_time_correct():
            return True
        else:
            self.ssh_client.execute(self.start_time_sync)
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
        if not self.no_addback:
            self.ssh_client.execute(self.addback_ntp_traffic)
        if not self.ssh_client.check_machine_time_correct():
            self.log.warning('Machine time not sync, force to trigger NTP/HTTP updating.')
            self.ssh_client.execute(self.start_time_sync)
            time.sleep(10)
            if not self.ssh_client.check_machine_time_correct():
                self.log.warning('Force to trigger NTP updating failed !!!!!!!!!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Time Sync for http fallback check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/timesync_http_fallback.py --uut_ip 10.92.224.68\
        """)

    test = TimeSyncHTTPFallback(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
