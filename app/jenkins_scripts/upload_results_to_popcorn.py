# -*- coding: utf-8 -*-
""" Tool to upload test results to popcorn.
"""
# std modules
import csv
import json
import random
import time
from argparse import ArgumentParser

# platform modules
from platform_libraries.popcorn import PopcornReport, PopcornSuite, PopcornTest, upload_popcorn_report_to_server

       
def gen_popcorn_report(total_pass=0, total_fail=0, project=None, version=None, fwbuild=None, test_type=None,
        environment=None, user=None, os_name=None, os_version=None, test_suite=None, component=None,
        platform=None, test_name=None, test_id=None, priority=None, jira_issue_key=None, error_msg='',
        end_time=None, test_interval=10, test_duration=10*60, build_url=None, report_name=None,
        build=None):
    """
    tests require: name, testId, result, component, start, end 
    suites require: name, passRate, component, platform, start, end
    """
    pr = PopcornReport(
        project=project, version=version, fwbuild=fwbuild, test_type=test_type, environment=environment,
        user=user, os_name=os_name, os_version=os_version, build_url=build_url, name=report_name,
        build=build, component=component
    )
    ps = PopcornSuite(name=test_suite, component=component, platform=platform, test_type=test_type)
    pr.add_suite(ps)

    endtime_random_offset = 1000 * random.uniform(-1, 1)
    if end_time:
        end = int(round(end_time * 1000) + endtime_random_offset)
    else:
        end = int(round(time.time() * 1000) + endtime_random_offset)

    tcs = []
    trs = [1 for _ in xrange(total_pass)] + [0 for _ in xrange(total_fail)]
    random.shuffle(trs) # Random ordering.
    for r in trs:
        start = end - int(round(test_duration * 1000 * random.uniform(0.8, 1.2))) # +- 20%
        pt = PopcornTest(
            name=test_name, test_id=test_id, result='PASSED' if r else 'FAILED', component=component, priority=priority,
            jira_issue_key=None if r else jira_issue_key, test_type=test_type, error='' if r else error_msg,
            start=start, end=end
        )
        tcs.append(pt)
        end = start - test_interval * 1000

    for pt in reversed(tcs): # Sort by start time.
        ps.add_test(pt)

    return summarize_popcorn_report(pr)

def gen_popcorn_report_by_json(tc_json_string, project=None, version=None, fwbuild=None, test_type=None, environment=None,
        user=None, os_name=None, os_version=None, test_suite=None, component=None, platform=None, end_time=None, test_interval=10,
        build_url=None, report_name=None, build=None):
    """
    tests require: name, testId, result, component, start, end 
    suites require: name, passRate, component, platform, start, end

    Only accept pass case.
    jdata = [{
        'test_name': 'STRING',
        'test_id': 'STRING',
        'priority': 'STRING',
        'test_duration': 0,
        'total': 0
    }]
    """
    pr = PopcornReport(
        project=project, version=version, fwbuild=fwbuild, test_type=test_type, environment=environment,
        user=user, os_name=os_name, os_version=os_version, build_url=build_url, name=report_name,
        build=build, component=component
    )
    ps = PopcornSuite(name=test_suite, component=component, platform=platform, test_type=test_type)
    pr.add_suite(ps)

    if end_time:
        end = int(round(end_time * 1000))
    else:
        end = int(round(time.time() * 1000))

    jdata = json.loads(tc_json_string)

    tcss = []
    for d in jdata: # gen tc object firset, then handle exec time.
        tcs = []
        for idx in xrange(d['total']):
            pt = PopcornTest(
                name=d['test_name'], test_id=d['test_id'], result='PASSED', component=component, priority=d.get('priority'),
                jira_issue_key=None, test_type=test_type, error=''
            )
            pt.test_duration = int(round(d.get('test_duration', 300) * 1000 * random.uniform(0.8, 1.2))) # +- 20%, save time here.
            tcs.append(pt)

        random.shuffle(tcs) # Random ordering.
        tcss.append(tcs)

    tcss = tcss[::-1] # handing from end
    tc_cycles = []
    while True: # split up tcs and save to test cycle
        tc_cycle = []
        for tcs in tcss: # pick one by one for each tcs
            if tcs:
                tc_cycle.append(tcs.pop())
        if not tc_cycle: break
        tc_cycles.append(tc_cycle)

    random.shuffle(tc_cycles) # Random ordering.

    for tc_cycle in tc_cycles: # update exec time.
        for pt in tc_cycle:
            pt['start'] = end - pt.test_duration
            pt['end'] = end
            end = pt['start'] - test_interval * 1000 # new end time for next pt
            ps.add_test(pt)

    ps['tests'] = ps['tests'][::-1] # Sort by start time.
    return summarize_popcorn_report(pr)

def summarize_popcorn_report(pr):
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
            if not test_start or test_start > test['start']:
                test_start = test['start']
            if not suite_start or suite_start > test['start']:
                suite_start = test['start']
            if not test_end or test_end < test['end']:
                test_end = test['end']
            if not suite_end or suite_end < test['end']:
                suite_end = test['end']
            if test['result'] == 'PASSED':
                test_pass += 1
                suite_pass += 1
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

def gen_popcorn_report_from_json(path):
    with open(path, 'r') as f:
        return json.loads(f.read())

def export_to_csv(pr, cvs_file):
    with open(cvs_file, 'a') as csvfile: # Open CSV file
        writer = csv.DictWriter(csvfile, 
            fieldnames=[
                'report_name', 'test_suite', 'project', 'environment', 'component', 'test_name', 'test_id', 'platform',
                'version', 'fwbuild', 'build', 'duration', 'result',])
        writer.writeheader()
        for ps in pr['suites']:
            for pt in ps['tests']:
                writer.writerow({
                    'report_name': ps['name'], 'test_suite': ps['name'], 'project': pr['project'],
                    'environment': pr['environment'], 'component': pr['component'], 'test_name': pt['name'],
                    'test_id': pt['testId'], 'platform': ps['platform'], 'version': pr['version'],
                    'fwbuild': pr['fwBuild'], 'build': pr['build'], 'duration': pt['end']-pt['start'],
                    'result': pt['result']
                })


if __name__ == '__main__':

    parser = ArgumentParser("""\
        Tool to upload test results to popcorn.

    e.g.
    ./run.sh jenkins_scripts/upload_results_to_popcorn.py -jf a.json -s CORE_FWK_STABILITY_UI
    ./run.sh jenkins_scripts/upload_results_to_popcorn.py -bu http://10.92.234.110:8080/job/mobile_ibi_stability_tests/job/fixed_sets_runner/job/ibi_softap_onboading_test_python_runner -rn Stability -s CORE_FWK_STABILITY_UI -ts "UI stability" -pj ibi -e qa -c "PLATFORM" -tn "Admin SoftAP On-boarding Test" -ti KAM-35953,KAM-24688,KAM-24051,KAM-26994,KAM-26996 -plm ibi -v 4.6.0 -f 7.6.0-115 -b 1694 -td 1800 -tp 5
    ./run.sh jenkins_scripts/upload_results_to_popcorn.py -bu http://10.92.234.110:8080/job/mobile_ibi_stability_tests/job/fixed_sets_runner/job/ibi_admin_onboarding_test_python_runner -rn Stability -s CORE_FWK_STABILITY_UI -ts "UI stability" -pj ibi -e qa -c "PLATFORM" -tn "Admin BT On-boarding Test" -ti KAM-35954 -plm ibi -v 4.6.0 -f 7.6.0-115 -b 1694 -td 900  -tp 5
    ./run.sh jenkins_scripts/upload_results_to_popcorn.py -bu http://10.92.234.110:8080/job/mobile_ibi_stability_tests/job/fixed_sets_runner/job/ibi_foreground_auto_backup_test_python_runner -rn Stability -s CORE_FWK_STABILITY_UI -ts "UI stability" -pj ibi -e qa -c "PLATFORM" -tn "Auto backup Test" -ti KAM-35955 -plm ibi -v 4.6.0 -f 7.6.0-115 -b 1694 -td 1200 -tp 5
    ./run.sh jenkins_scripts/upload_results_to_popcorn.py -bu http://10.92.234.110:8080/job/mobile_ibi_stability_tests/job/fixed_sets_runner/job/web_admin_onboarding_test_python_runner -rn Stability -s CORE_FWK_STABILITY_UI -ts "UI stability" -pj MCH -e qa -c "PLATFORM" -tn "Admin Web On-boarding Test" -ti KAM-31434 -plm MCH -v 4.6.0 -f 7.6.0-115 -b None -td 900 -tp 5
    ./run.sh jenkins_scripts/upload_results_to_popcorn.py -bu http://10.92.234.110:8080/job/mobile_ibi_stability_tests/job/fixed_sets_runner/job/mch_admin_onboarding_test_python_runner -rn Stability -s CORE_FWK_STABILITY_UI -ts "UI stability" -pj MCH -e qa -c "PLATFORM" -tn "Admin mobile app On-boarding Test" -ti KAM-35957 -plm MCH -v 4.6.0 -f 7.6.0-115 -b 1692 -td 900 -tp 5
    ./run.sh jenkins_scripts/upload_results_to_popcorn.py -bu http://10.92.234.110:8080/job/mobile_ibi_stability_tests/job/fixed_sets_runner/job/mch_foreground_auto_backup_test_python_runner -rn Stability -s CORE_FWK_STABILITY_UI -ts "UI stability" -pj MCH -e qa -c "PLATFORM" -tn "Auto backup Test" -ti KAM-35956 -plm MCH -v 4.6.0 -f 7.6.0-115 -b 1692 -td 1200 -tp 5
    ./run.sh jenkins_scripts/upload_results_to_popcorn.py -rn Stability -s PLATFORM -ts "GZA stability" -pj Godzilla -e qa -c "PLATFORM" -tn "USB indexing test - intel module - HFS+" -ti GZA-5482 -plm Godzilla -v ExternalBeta0605 -f 5.00.279 -b None -td 300 -tf 2 -tp 3 -csv results.csv
    """)
    parser.add_argument('-jf', '--json-file', help='Popcorn json file to update', metavar='PATH', default=None)
    parser.add_argument('-js', '--tc-json-string', help='Pass test case json string to update', metavar='STRING', default=None)
    parser.add_argument('-bu', '--build-url', help='URL of jenkins build', metavar='URL', default=None)
    parser.add_argument('-tp', '--total-pass', help='Total pass number to update', type=int, metavar='PASS', default=0)
    parser.add_argument('-tf', '--total-fail', help='Total fail number to update', type=int, metavar='FAIL', default=0)
    parser.add_argument('-s', '--source', help='Source of test report. e.g. PLATFORM', metavar='SRC', default=None)
    parser.add_argument('-pj', '--project', help='Project of test report. e.g. ibi/MCH/godzilla', metavar='PROJECT', default=None)
    parser.add_argument('-v', '--version', help='Version of test report. e.g. 4.5.0', metavar='VERSION', default=None)
    parser.add_argument('-f', '--fwbuild', help='fwbuild of test report. e.g. 7.5.0-100', metavar='fwbuild', default=None)
    parser.add_argument('-tt', '--test-type', help='Test type of test report. e.g. Functional/Performance/Localization', metavar='TYPE', default='Functional')
    parser.add_argument('-e', '--environment', help='Environment of test report. e.g. dev/qa/prod', metavar='ENV', default=None)
    parser.add_argument('-u', '--user', help='Test user of test report. e.g. user@a.com', metavar='USER', default=None)
    parser.add_argument('-on', '--os-name', help='Test OS name of test report. e.g. "Linux + Python"', metavar='OS', default=None)
    parser.add_argument('-ov', '--os-version', help='Test OS version of test report. e.g. 2.7', metavar='VERSION', default=None)
    parser.add_argument('-ts', '--test-suite', help='Test suite name of test report.', metavar='SUITE', default=None)
    parser.add_argument('-c', '--component', help='Test component name of test report.', metavar='COMPONENT', default=None)
    parser.add_argument('-plm', '--platform', help='Test platform name of test report.', metavar='PLATFROM', default=None)
    parser.add_argument('-tn', '--test-name', help='Test name of test report.', metavar='NAME', default=None)
    parser.add_argument('-ti', '--test-id', help='Test ID of test report. e.g. IBIX-1234,IBIX-5678', metavar='ID', default=None)
    parser.add_argument('-pr', '--priority', help='Test priority of test report.', metavar='PRIORITY', default=None)
    parser.add_argument('-jik', '--jira-issue-key', help='Jira issue keys of test report. e.g. IBIX-1234,IBIX-5678', metavar='KEYS', default=None)
    parser.add_argument('-em', '--error-msg', help='Error message of test report.', metavar='MSG', default='')
    parser.add_argument('-et', '--end-time', help='End time (machine time) of test report. Default time is update time', type=int, metavar='TIME', default=0)
    parser.add_argument('-tit', '--test-interval', help='Interval time in secs of test cases', type=int, metavar='TIME', default=10)
    parser.add_argument('-td', '--test-duration', help='Duration time in secs of test cases', type=int, metavar='TIME', default=10*60)
    parser.add_argument('-rn', '--report-name', help='Report name of test report.', metavar='NAME', default=None)
    parser.add_argument('-b', '--build', help='Client build number of test report.', metavar='BUILD', default=None)
    parser.add_argument('-csv', '--export-csv', help='Specify path export to CSV file', metavar='PATH', default=None)

    parser = parser.parse_args()

    if parser.json_file:
        pr = gen_popcorn_report_from_json(parser.json_file)
    elif parser.tc_json_string:
        pr = gen_popcorn_report_by_json(parser.tc_json_string, project=parser.project,
            version=parser.version, fwbuild=parser.fwbuild, test_type=parser.test_type,
            environment=parser.environment, user=parser.user, os_name=parser.os_name,
            os_version=parser.os_version, test_suite=parser.test_suite, component=parser.component,
            platform=parser.platform, end_time=parser.end_time, test_interval=parser.test_interval,
            build_url=parser.build_url, report_name=parser.report_name, build=parser.build)
    else:
        pr = gen_popcorn_report(total_pass=parser.total_pass, total_fail=parser.total_fail, project=parser.project,
            version=parser.version, fwbuild=parser.fwbuild, test_type=parser.test_type,
            environment=parser.environment, user=parser.user, os_name=parser.os_name,
            os_version=parser.os_version, test_suite=parser.test_suite, component=parser.component,
            platform=parser.platform, test_name=parser.test_name, test_id=parser.test_id,
            priority=parser.priority, jira_issue_key=parser.jira_issue_key, error_msg=parser.error_msg,
            end_time=parser.end_time, test_interval=parser.test_interval, test_duration=parser.test_duration,
            build_url=parser.build_url, report_name=parser.report_name, build=parser.build
        )
    if parser.export_csv:
        export_to_csv(pr=pr, cvs_file=parser.export_csv)
    else:
        upload_popcorn_report_to_server(data=pr, source=parser.source)
