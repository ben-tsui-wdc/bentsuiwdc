# -*- coding: utf-8 -*-
""" Test for API: GET /v1/mediaTimeGroups (KAM-20437, KAM-20434, KAM-20435, KAM-20436).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
from datetime import datetime
from pprint import pformat
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
# 3rd party modules
from dateutil.relativedelta import relativedelta


class GetMediaTimeGroupsTest(GodzillaTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Get Media Time Groups Test'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1748'
    PRIORITY = 'Blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.end_time = None
        self.unit = None
        self.mime_groups = None

    def init(self):
        if not all([self.end_time, self.unit, self.mime_groups]):
            raise self.err.StopTest('Need end_time and unit and mime_groups')

        # Check data format and convert to datetime object.
        try:
            self.dt_end_time = datetime.strptime(self.end_time, '%Y-%m-%dT%H:%M:%SZ')
        except:
            self.dt_end_time = datetime.strptime(self.end_time, '%Y-%m-%dT%H:%M:%S.%fZ')

    def test(self):
        groups = self.uut_owner.get_media_time_groups(
            end_time=self.end_time, unit=self.unit, mime_groups=self.mime_groups, limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(groups)))
        self.verify_result(groups)

    def verify_result(self, groups):
        # check min time and max time of all groups are in specified the range.
        for group in groups:
            try:
                self.verify_time_group(min_time=group['minTime'], max_time=group['maxTime'], unit=self.unit)
            except KeyError, e:
                self.log.error('Reponse is not in the expected format: \n{}'.format(pformat(group)))
                raise self.err.TestFailure('Field not found: {}'.format(e))

    def verify_time_group(self, min_time, max_time, unit):
        self.log.info('Verify {0} - {1} is in the range: {2}'.format(min_time, max_time, unit))
        dt_min_time = datetime.strptime(min_time, '%Y-%m-%dT%H:%M:%SZ')
        dt_max_time = datetime.strptime(max_time, '%Y-%m-%dT%H:%M:%S.%fZ')
        diff = dt_max_time - dt_min_time
        diff_sec = diff.total_seconds()
        if unit == 'year': 
            if not (dt_min_time + relativedelta(years=1) >= dt_max_time):
                raise self.err.TestFailure('Max time is not correct')
            if diff_sec > 366*24*60*60: raise self.err.TestFailure('Min time is not correct')
        elif unit == 'month':
            if not (dt_min_time + relativedelta(months=1) >= dt_max_time):
                raise self.err.TestFailure('Max time is not correct')
            if diff_sec > 31*24*60*60: raise self.err.TestFailure('Min time is not correct')
        elif unit == 'day':
            if not (dt_min_time + relativedelta(days=1) >= dt_max_time):
                raise self.err.TestFailure('Max time is not correct')
            if diff_sec > 24*60*60: raise self.err.TestFailure('Min time is not correct')
        elif unit == 'hour':
            if not (dt_min_time + relativedelta(hours=1) >= dt_max_time):
                raise self.err.TestFailure('Max time is not correct')
            if diff_sec > 60*60: raise self.err.TestFailure('Min time is not correct')
        self.log.info('Time range is correct.')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Get_Media_Time_Groups_Test test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/get_media_time_groups.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-et', '--end_time', help='End time of range to search', metavar='TIME')
    parser.add_argument('-unit', '--unit', help='The duration to include for each group', metavar='UNIT')
    parser.add_argument('-mg', '--mime_groups', help='The group of the MIME type to include.', metavar='TYPE')

    test = GetMediaTimeGroupsTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
