# -*- coding: utf-8 -*-
""" A test sample for test group.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
# test cases
from simple_case import SimpleTest
from simple_fail_case import SimpleFaileTest


class TestGroupTest(IntegrationTest):

    TEST_SUITE = 'TestGroupTest'
    TEST_NAME = 'TestGroupTest'

    def init(self):
        self.integration.add_testcases(testcases=[
            (SimpleTest, {'TEST_NAME': 'Test 1', 'my_var': 1}, [ # PASSED
                self.testgroup.PassGroup(['Pass_A'])
            ]),
            (SimpleFaileTest, {'TEST_NAME': 'Test 2', 'my_var': 2}, [ # FAILED
                self.testgroup.FailedGroup(['Error_A'])
            ]),
            (self.dummy_case.KaminoDummyCase, {'TEST_NAME': 'Test 3'}, [ # PASSED
                self.testgroup.PassGroup(['Pass_A'])
            ]),
            (self.dummy_case.KaminoDummyCase, {'TEST_NAME': 'Test 4'}, [ # FAILED by Test 2
                self.testgroup.FailedGroup(['Error_A'])
            ]),
            (self.dummy_case.KaminoDummyCase, {'TEST_NAME': 'Test 5'}, [ # PASSED by Test 1
                self.testgroup.PassGroup(['Pass_A']), self.testgroup.FailedGroup(['Error_A'])
            ]),
            (self.dummy_case.KaminoDummyCase, {'TEST_NAME': 'Test 6'}, [ # FAILED by Test 2
                self.testgroup.PassGroup(['Error_A']), self.testgroup.FailedGroup(['Error_A'])
            ]),
            (self.dummy_case.KaminoDummyCase, {'TEST_NAME': 'Test 7'}, [ # NOTEXECUTED by Test 2
                self.testgroup.ErrorGroup(['Error_A'])
            ]),
            (self.dummy_case.KaminoDummyCase, {'TEST_NAME': 'Test 8'}, [ # SKIPPED by Test 2
                self.testgroup.SkipGroup(['Error_A'])
            ]),
            (self.dummy_case.KaminoDummyCase, {'TEST_NAME': 'Test 9'}, [ # PASSED because there is no error in group.
                self.testgroup.SkipGroup(['Pass_A'])
            ])
        ])


if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** Simple Test on Kamino Android ***
        Examples: ./run.sh middleware/examples/test_group_test.py --uut_ip 10.136.137.159\
        """)

    test = TestGroupTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
