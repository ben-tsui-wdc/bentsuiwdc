# -*- coding: utf-8 -*-
"""functional test for daily.
"""

# std modules
import sys
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
# Sub-tests
# "test_class_list" is created by __init__.py in functional_tests.
from functional_tests import test_class_list


class functional_tests(IntegrationTest):

    TEST_SUITE = 'functional_tests'
    TEST_NAME = 'functional_tests'

    def declare(self):
        self.test_cases = 'all'

    def init(self):
        for item in test_class_list:
            if self.test_cases == "all":
                break
            else:
                if item.__name__ not in self.test_cases:
                    test_class_list.remove(item)

        if self.env.debug_middleware:
            print '---  test_class_list imported successfully in functional_testsuite.py ---'
            print test_class_list
            print '---  test_class_list imported successfully in functional_testsuite.py ---'

        self.integration.add_testcases(testcases=test_class_list)


if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** functional_tests on Kamino Android ***
        Examples: ./run.sh # functional_tests/functional_testsuite --uut_ip 10.92.224.71 --dry_run --debug_middleware\
        """)
    parser.add_argument('--test_cases', help='Put the testcase name here if you want to specify, for example:RAIDconversion,multiRW, otherwise all testcases will be executed.', default='all')

    test = functional_tests(parser)

    if test.main():
        sys.exit(0)
    sys.exit(1)
