
# -*- coding: utf-8 -*-
# std modules
import os
import re
from argparse import ArgumentParser


# Parameters
parser = ArgumentParser(""" A tool to parse UI automation logs. """)
parser.add_argument('-lp', '--log_path', help='UI automation log', metavar='PATH', required=True)
parser.add_argument('-af', '--accept-failures', help='Results accept a number of failures', metavar='NUM', type=int, default=0)


# Classes
class IterationResult:

    def __init__(self,):
        self.total_str = None
        self.failure_str = None
        self.total_itr = 0
        self.total_fail = 0
        self.total_skip = 0

    def set_total_str(self, log_str):
        self.total_str = log_str
        self.total_itr, self.total_fail, self.total_skip = re.findall(r'\d+', s)

    def set_failure_str(self, log_str):
        if not self.set_failure_str:
            self.failure_str = log_str
        else:
            print(f'Multiple failures string: {log_str}')

    def is_fail(self):
        if self.failure_str or self.total_fail > accept_failures:
            return True
        return False

# Init vars
log_path = parser.log_path
accept_failures = parser.accept_failures

test_results = []
TOTAL_ITR = 0
TOTAL_PASS = 0


# Parse log and summarize.
with open(log_path, "r") as f:
    test_result = None
    for line in f:
        if line.start_with('Total tests run:'):
            test_result = IterationResult()
            test_result.set_total_str(line)
            test_results.append(test_result)
        elif line.start_with('Configuration Failures:'):
            if not test_result:
                print(f'Unexpected line: {line}')
            test_result.set_failure_str(line)

TOTAL_ITR = len(test_results)
for test_result in test_results:
    if not test_result.is_fail():
        TOTAL_PASS += 1


# Print out
f.write(f'TOTAL_ITR={TOTAL_ITR}')
f.write(f'TOTAL_PASS={TOTAL_PASS}')

with open("build.properties", "a") as f:
    f.write(f'TOTAL_ITR={TOTAL_ITR}')
    f.write(f'TOTAL_PASS={TOTAL_PASS}')

