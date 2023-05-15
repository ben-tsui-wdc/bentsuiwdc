# -*- coding: utf-8 -*-
# std modules
import os
import re
from argparse import ArgumentParser


print_log = print

# Classes
class IterationResult:

    def __init__(self, accept_failures=0, debug=False):
        self.name = None
        self.total_str = None
        self.failure_str = None
        self.total_itr = 0
        self.total_fail = 0
        self.total_skip = 0
        self.accept_failures = accept_failures
        self.debug = debug

    def set_total_str(self, log_str):
        if self.debug: print_log(f'DEBUG: {log_str.strip(os.linesep)}')
        self.total_str = log_str
        self.total_itr, self.total_fail, self.total_skip = [int(s) for s in re.findall(r'\d+', log_str)]

    def set_failure_str(self, log_str):
        if self.debug: print_log(f'DEBUG: {log_str.strip(os.linesep)}')
        if not self.failure_str:
            self.failure_str = log_str
        else:
            print_log(f'Multiple failures string: {log_str.strip(os.linesep)}')

    def is_fail(self):
        if self.debug: print_log(f'DEBUG: failure_str: {True if self.failure_str else False} total_fail: {self.total_fail} accept_failures: {self.accept_failures}')
        if self.failure_str or self.total_fail > self.accept_failures:
            return True
        return False

def read_log_and_summarize(log_path, accept_failures=0, debug=False, suite_name=None):
    with open(log_path, encoding="ISO-8859-1") as f:
        return parse_strs_and_summarize(f, accept_failures, debug, suite_name)

def parse_strs_and_summarize(log_str_itr, accept_failures=0, debug=False, suite_name=None):
    test_cycle_results = []
    sub_test_results = []
    total_itr = 0
    total_pass = 0

    # Parse log and summarize.
    read_test_result = None
    for line in log_str_itr: # read line by line.
        # hit test result boundary
        if line.startswith('='*47):
            if not read_test_result: # boundary start
                read_test_result = IterationResult(accept_failures, debug)
            else: # boundary end
                if not suite_name or (suite_name and read_test_result.name.startswith(suite_name)):
                    test_cycle_results.append(read_test_result)
                else:
                    sub_test_results.append(read_test_result)
                read_test_result = None
            continue
        elif not read_test_result: continue # Only read lines in test result boundary

        # First line is test name
        if not read_test_result.name:
            read_test_result.name = line.strip()
            continue

        if line.startswith('Total tests run:'):
            read_test_result.set_total_str(line)
        elif line.startswith('Configuration Failures:'):
            if not read_test_result:
                print_log(f'Unexpected line: {line.strip(os.linesep)}')
            read_test_result.set_failure_str(line)

    total_itr = len(test_cycle_results)
    for test_result in test_cycle_results:
        if not test_result.is_fail():
            total_pass += 1

    # calculate for each sub test
    sub_tests = {}
    for test_result in sub_test_results:
        if test_result.name not in sub_tests: # default data format
            sub_tests[test_result.name] = {'total_itr': 0, 'total_pass': 0}
        sub_tests[test_result.name]['total_itr'] += 1
        if not test_result.is_fail():
            sub_tests[test_result.name]['total_pass'] += 1

    return total_itr, total_pass, sub_tests

def print_out(total_itr, total_pass, sub_tests, properties_path='./build.properties'):
    # Print out
    print_log(f'TOTAL_ITR={total_itr}')
    print_log(f'TOTAL_PASS={total_pass}')
    print_log(f'Sub tests: {sub_tests}')

    first_new_line = '\n' if os.path.exists(properties_path) and os.stat(properties_path).st_size else ''
    with open(properties_path, "a") as f:
        f.write(f'{first_new_line}TOTAL_ITR={total_itr}\n')
        f.write(f'TOTAL_PASS={total_pass}\n')


if __name__ == '__main__':
    # Parameters
    parser = ArgumentParser(""" A tool to parse UI automation logs. """)
    parser.add_argument('-lp', '--log_path', help='UI automation log', metavar='PATH', required=True)
    parser.add_argument('-af', '--accept-failures', help='Results accept a number of failures', metavar='NUM', type=int, default=0)
    parser.add_argument('-pp', '--properties-path', help='Jenkins properties file to write result', metavar='PATH', default='./build.properties')
    parser.add_argument('-d', '--debug', help='Print debug message', action='store_true', default=False)
    parser.add_argument('-sn', '--suite-name', help='Suite name (integration suite) to find the summary line in multiple suites cases', metavar='SUITENAME', default=None)
    input_args = parser.parse_args()

    # Init vars
    log_path = input_args.log_path
    accept_failures = input_args.accept_failures
    properties_path = input_args.properties_path
    debug = input_args.debug
    suite_name = input_args.suite_name

    total_itr, total_pass, sub_tests = read_log_and_summarize(log_path, accept_failures, debug, suite_name)
    print_out(total_itr, total_pass, sub_tests, properties_path)

