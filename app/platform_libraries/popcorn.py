# -*- coding: utf-8 -*-
""" Modules for Popcorn report system.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

#std modules
import platform
import json
import sys
import random
import string
# 3rd party modules
import requests
# middleware modules
from middleware.error import get_junit_msg_key_from

#
# Popcorn Item Area
#
TEST_TYPES = ['Functional', 'Performance', 'Localization']
ENVIRONMENTS = ['dev', 'qa', 'prod']
RESULTS = ['PASSED', 'FAILED', 'SKIPPED']
PRIORITYS = ['blocker', 'critical', 'major', 'minor']


class PopcornReport(dict):

    def __init__(self, project, version, component, build='None', fwbuild='', pass_rate=None, start=None, end=None, test_type='functional', 
            environment='', user='', os_name='', os_version='', build_url=None, name=None):
        '''
        if test_type and not is_test_type(test_type):
            raise TypeError('test_type only accpet {0}, but give {1}'.format(TEST_TYPES,test_type))
        if environment and not is_environment(environment):
            raise TypeError('environment only accpet {0}}, but give {1}'.format(ENVIRONMENTS, environment))
        '''
        self.update({
            "project": project, # Required, str.
            "version": version, # Required, str.
            "build": build, # Required, str.
            "component": component, # Required, str.
            "fwBuild": fwbuild, # Required, str.
            "overallPassRate": pass_rate, # Required, float.
            "start": start, # Required, long.
            "end": end, # Required, long.
            "testType": test_type, # str (functional/performance/stability).
            "environment": environment, # str (dev/qa/prod).
            "suites": [],
            "name": name,
            "executionSummary": {
                "user": user,
                "osName": os_name,
                "osVersion": os_version,
                "buildUrl": build_url
            }
        })

    def add_suite(self, suite):
        if isinstance(suite, PopcornSuite):
            self['suites'].append(suite)
        else:
            raise TypeError('Expect PopcornSuite object, but give {}'.format(type(suite)))

class PopcornSuite(dict):

    def __init__(self, name, component, platform, pass_rate=None, start=None, end=None, test_type=''):
        '''
        if test_type and not is_test_type(test_type):
            raise TypeError('test_type only accpet {0}, but give {1}'.format(TEST_TYPES, test_type))
        '''
        self.update({
            "name": name, # Required, str.
            "passRate": pass_rate, # Required, float.
            "component": component, # Required, str.
            "platform": platform, # Required, str.
            "start": start, # long.
            "end": end, # long.
            "testType": test_type, # str (functional/performance/stability).
            "tests": []
        })

    def add_test(self, test):
        if test:
            if isinstance(test, PopcornTest):
                if '429 Client Error' in test.get('error'):
                    print 'Skip the test results with 429 too many request error'
                else:
                    self['tests'].append(test)
            else:
                raise TypeError('Expect PopcornTest object, but give {}'.format(type(test)))
        else:
            print 'The test parameter is empty, skip to append the test case result steps ...'

class PopcornTest(dict):

    # Additional attrs for record test time.
    TEST_START_TIME = 0
    TEST_END_TIME = 0

    def __init__(self, name, test_id, result, component, priority=None, start=None, end=None, jira_issue_key='', error='', test_type=''):
        if result and not is_result(result):
            raise TypeError('result only accpet {0}, but give {1}'.format(RESULTS, result))
        '''
        if priority and not is_priority(priority):
            raise TypeError('priority only accpet {0}, but give {1}'.format(PRIORITYS, priority))
        if test_type and not is_test_type(test_type):
            raise TypeError('test_type only accpet {0}, but give {1}'.format(TEST_TYPES, test_type))
        '''
        self.update({
            "name": name, # Required, str.
            "testId": test_id, # Required, str.
            "result": result, # Required, str (PASSED/FAILED/SKIPPED).
            "component": component, # Required, str.
            "priority": priority, # Required, str (blocker/critical/major/minor).
            "jiraIssueKey": jira_issue_key, # Only required if test failed, str.
            "error": error, # str.
            "testType": test_type, # str (functional/performance/UI).
            "start": start, # long.
            "end": end, # long.
        })


#
# Popcorn Kits For Framework Area
#
def gen_popcorn_test(testcase):
    """ Generate Popcorn test oject for current test result.
    """
    # Recognize result value.
    error_filed = get_junit_msg_key_from(testcase.data.test_result)
    if testcase.data.test_result.TEST_PASS:
        result = 'PASSED'
    else:
        if error_filed and 'skipped' in error_filed:
            result = 'SKIPPED'
        else:
            result = 'FAILED'
    if not testcase.timing.start_time: testcase.timing.start_time = 0
    if not testcase.timing.end_time: testcase.timing.end_time = 0
    S_TIME = int(round(testcase.timing.start_time * 1000))
    E_TIME = int(round(testcase.timing.end_time * 1000))
    # Create object.
    pt = PopcornTest(
        name=testcase.TEST_NAME, test_id=testcase.TEST_JIRA_ID,
        result=result,
        component=testcase.COMPONENT, priority=testcase.PRIORITY,
        jira_issue_key=testcase.ISSUE_JIRA_ID, test_type=testcase.TEST_TYPE,
        error=testcase.data.test_result[error_filed] if error_filed else '',
        start=S_TIME, end=E_TIME
    )
    # Update time.
    pt.TEST_START_TIME = S_TIME
    pt.TEST_END_TIME = E_TIME
    return pt

def gen_popcorn_report(testcase, test_results, skip_error=False):
    # Set execution environment as OS info if it's empty.
    if not testcase.OS_NAME:
        testcase.OS_NAME = '{} + Python'.format(platform.system())
    if not testcase.OS_VERSION:
        testcase.OS_VERSION = '{} + {}'.format(platform.release(), sys.version.split()[0])
    # Change values for report format.
    environment = testcase.ENVIROMENT
    ver = testcase.VERSION
    if testcase.ENVIROMENT:
        if 'dev' in environment: environment = 'dev'
        if 'qa' in environment: environment = 'qa'
    if testcase.VERSION:
        if '7.3.0' in ver: ver = '4.3.0'
        if '7.3.1' in ver: ver = '4.3.1'
        if '7.4.0' in ver: ver = '4.4.0'
        if '7.5.0' in ver: ver = '4.5.0'
        if '7.6.0' in ver: ver = '4.6.0'
        if '7.7.0' in ver: ver = '4.7.0'
        if '7.8.0' in ver: ver = '4.8.0'
        if '7.9.0' in ver: ver = '4.9.0'
        if '7.9.2' in ver: ver = '4.9.2'
        if '7.10.0' in ver: ver = '4.10.0'
        if '7.11.0' in ver: ver = '4.11.0'
        if '7.12.0' in ver: ver = '4.12.0'
        if '7.13.0' in ver: ver = '4.13.0'
        if '7.14.0' in ver: ver = '4.14.0'
        if '7.15.0' in ver: ver = '4.15.0'
        if '7.16.0' in ver: ver = '4.16.0'
        if '7.17.0' in ver: ver = '4.17.0'
        if '7.18.0' in ver: ver = '4.18.0'
    '''
    if testcase.PROJECT.lower() == 'godzilla':
        FW_BUILD = testcase.FW_BUILD
    elif testcase.PROJECT == 'ibi' or testcase.PROJECT == 'MCH': #Still need to fix if pv argument has provided
        FW_BUILD = testcase.VERSION+'-'+testcase.BUILD
    else:
        print 'testcase.PROJECT is :{}, no FW_BUILD provided ...'.format(testcase.PROJECT)
    '''
    pr = PopcornReport(
        project=testcase.PROJECT, version=ver, fwbuild=testcase.FW_BUILD, component=testcase.COMPONENT,
        test_type=testcase.TEST_TYPE, environment=environment,
        user=testcase.USER, os_name=testcase.OS_NAME, os_version=testcase.OS_VERSION,
        build_url=testcase.BUILD_URL, name=testcase.REPORT_NAME
    )
    ps = PopcornSuite(
        name=testcase.TEST_SUITE, component=testcase.COMPONENT, platform=testcase.PLATFORM,
        test_type=testcase.TEST_TYPE)
    pr.add_suite(ps)
    for test_result in test_results:
        if skip_error:
            if test_result.POPCORN_RESULT['result'] == 'FAILED':
                continue
        if test_result.POPCORN_RESULT:
            ps.add_test(test_result.POPCORN_RESULT)

    # Update pass rate and test time.
    test_start = None
    test_end = None
    test_pass = 0
    test_fail = 0
    for suite in pr['suites']:
        suite_start = None
        suite_end = None
        suite_pass = 0
        suite_fail = 0
        for test in suite['tests']:
            if not test_start or test_start > test.TEST_START_TIME:
                test_start = test.TEST_START_TIME
            if not suite_start or suite_start > test.TEST_START_TIME:
                suite_start = test.TEST_START_TIME
            if not test_end or test_end < test.TEST_START_TIME:
                test_end = test.TEST_END_TIME
            if not suite_end or suite_end < test.TEST_START_TIME:
                suite_end = test.TEST_END_TIME
            if test['result'] == 'PASSED':
                test_pass += 1
                suite_pass += 1
            elif test['result'] == 'SKIPPED':
                pass # Do nothing.
            else:
                test_fail += 1
                suite_fail += 1
        suite['start'] = suite_start
        suite['end'] = suite_end
        suite['passRate'] = float(suite_pass) / (suite_pass + suite_fail) if suite_pass + suite_fail > 0 else 0.0
    pr['start'] = test_start
    pr['end'] = test_end
    pr['overallPassRate'] = float(test_pass) / (test_pass + test_fail) if test_pass + test_fail > 0 else 0.0

    return pr

def upload_popcorn_report_to_server(data, popcorn_address='popcorn.wdc.com', source='PLATFORM'):
    url = 'https://{0}/api/reports/automation?source={1}'.format(popcorn_address, source)
    headers = {'Content-Type': 'application/json',
                'X-POPCORN-KEY': randomString(),
                'X-POPCORN-BUILD-URL': data['executionSummary']['buildUrl']}

    response = requests.post(url=url, data=json.dumps(data), headers=headers)
    if not response.status_code == 200:
        print 'Upload popcorn json report to popcorn server failed !!!, response code:{0}, error log:{1}'.format(response.status_code, response.content)

def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

#
# Popcorn Kits Area
#
def is_test_type(v):
    return v.lower() in [word.lower() for word in TEST_TYPES]

def is_environment(v):
    return v.lower() in [word.lower() for word in ENVIRONMENTS]

def is_result(v):
    return v in RESULTS

def is_priority(v):
    return v.lower() in [word.lower() for word in PRIORITYS]
