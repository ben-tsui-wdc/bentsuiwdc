# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import datetime
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.restAPI import RestAPI


class DiskHealthMonitor(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KAM-23593: Disk healthy monitoring'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-23593'
    PRIORITY = 'critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {'uut_owner':False}


    def declare(self):
        pass


    def before_loop(self):
        pass


    def before_test(self):
        pass


    def _healthcheck_timestamp(self):
        healthcheck_timestamp_list = []
        stdout, stderr = self.adb.executeShellCommand('logcat -d | grep diskmgrd', timeout=180)
        for element in stdout.split('\n'):
            if 'S.M.A.R.T.' in element and 'healthcheck' in element and 'sataa' in element:
                #print element

                # Conversion from string to "datetime"
                absolute_time = datetime.datetime.strptime(element.split()[0], '%Y-%m-%dT%H:%M:%S.%fZ')
                healthcheck_timestamp_list.append(absolute_time)
                #print element
        print '$$$$$$$$$$$$$$$$'
        print 'healthcheck_timestamp_list:\n{}'.format(healthcheck_timestamp_list)
        return healthcheck_timestamp_list


    def test(self):

        healthcheck_timestamp_list = self._healthcheck_timestamp()

        starting_time = time.time()

        # 2100 seconds equal to 35 minutes
        origin_num = len(healthcheck_timestamp_list)
        if origin_num > 1:
            if healthcheck_timestamp_list[1] > healthcheck_timestamp_list[0] + datetime.timedelta(minutes=35) or \
                healthcheck_timestamp_list[1] < healthcheck_timestamp_list[0] + datetime.timedelta(minutes=25):
                raise self.err.TestFailure('The time interval of disk healthcheck is not 30 minutes.')
        else:
            while time.time() < (starting_time + 2100):
                print 'Wait more 180 seconds for new healthcheck record displayed.'
                time.sleep(180)
                healthcheck_timestamp_list = self._healthcheck_timestamp()
                if len(healthcheck_timestamp_list) == origin_num + 1:
                    self.log.info("The healthycheck happens exactly after/within 30 minutes.")
                    break
            if len(healthcheck_timestamp_list) == origin_num:
                raise self.err.TestFailure('The disk healthcheck didn\'t occur every 30 minutes.')


    def after_test(self):
        pass



    def after_loop(self):
        pass


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/disk_healthy_monitoring.py --uut_ip 10.0.0.28 --cloud_env qa1 --dry_run --debug_middleware\
         --disable_clean_logcat_log """)

    test = DiskHealthMonitor(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)