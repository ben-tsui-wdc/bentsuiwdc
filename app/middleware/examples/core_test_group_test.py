# -*- coding: utf-8 -*-
""" A test sample for test group.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import CoreIntegrationTestArgument
from middleware.core.integration_test import IntegrationTest


class CoreTestGroupTest(IntegrationTest):

    TEST_SUITE = 'CoreTestGroupTest'
    TEST_NAME = 'CoreTestGroupTest'

    def init(self):
        self.integration.add_testcases(testcases=[
            (self.dummy_case.DummyCase, {'TEST_NAME': 'Test 1'}, [ # PASSED
                self.testgroup.PassGroup(['Pass_A'])
            ]),
            (self.dummy_case.FailureCase, {'TEST_NAME': 'Test 2'}, [ # FAILED at __init__
                self.testgroup.FailedGroup(['Error_A'])
            ]),
            (self.dummy_case.DummyCase, {'TEST_NAME': 'Test 3'}, [ # PASSED
                self.testgroup.PassGroup(['Pass_A'])
            ]),
            (self.dummy_case.DummyCase, {'TEST_NAME': 'Test 4'}, [ # FAILED by Test 2
                self.testgroup.FailedGroup(['Error_A'])
            ]),
            (self.dummy_case.DummyCase, {'TEST_NAME': 'Test 5'}, [ # PASSED by Test 1
                self.testgroup.PassGroup(['Pass_A']), self.testgroup.FailedGroup(['Error_A'])
            ]),
            (self.dummy_case.DummyCase, {'TEST_NAME': 'Test 6'}, [ # FAILED by Test 2
                self.testgroup.PassGroup(['Error_A']), self.testgroup.FailedGroup(['Error_A'])
            ]),
            (self.dummy_case.DummyCase, {'TEST_NAME': 'Test 7'}, [ # NOTEXECUTED by Test 2
                self.testgroup.ErrorGroup(['Error_A'])
            ]),
            (self.dummy_case.DummyCase, {'TEST_NAME': 'Test 8'}, [ # SKIPPED by Test 2
                self.testgroup.SkipGroup(['Error_A'])
            ]),
            (self.dummy_case.DummyCase, {'TEST_NAME': 'Test 9'}, [ # PASSED because there is no error in group.
                self.testgroup.SkipGroup(['Pass_A'])
            ])
        ])


if __name__ == '__main__':
    parser = CoreIntegrationTestArgument("""\
        *** Simple Test on Kamino Android ***
        Examples: ./run.sh middleware/examples/core_test_group_test.py --uut_ip 10.136.137.159\
        """)

    test = CoreTestGroupTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
