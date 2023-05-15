# -*- coding: utf-8 -*-
""" A test with run test behavior of template.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class TestStepLoggingSample(TestCase):

    TEST_SUITE = 'Test Step Logging Sample'
    TEST_NAME = 'Test Step Logging Sample'

    def init(self):
        self.log.info('Run init step.')
        self.log.test_step('Run init step.')

    def before_test(self):
        self.log.info('Run before_test step.')
        self.log.test_step('Run before_test step.')

    def test(self):
        self.log.info('Run before_test step.')
        self.log.test_step("Run test step!")
        if self.test_normal_error: raise RuntimeError('error at test()')
        if self.test_test_error: raise self.err.TestError('error at test()')

    def after_test(self):
        self.log.info('Run after_test step.')
        self.log.test_step('Run after_test step.')
        if self.after_test_normal_error: raise RuntimeError('error at after_test()')
        if self.after_test_test_error: raise self.err.TestError('error at after_test()')

    def before_loop(self):
        self.log.info('Run before_loop step.')
        self.log.test_step('Run before_loop step.')

    def after_loop(self):
        self.log.info('Run after_loop step.')
        self.log.test_step('Run after_loop step.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Simple Test on Kamino Android ***
        Examples: ./run.sh middleware/examples/test_step_logging_sample.py --uut_ip 10.136.137.159\
        """)
    # Test Arguments
    parser.add_argument('-tne', '--test_normal_error', help='Raise RuntimeError at test()', action='store_true', default=False)
    parser.add_argument('-tte', '--test_test_error', help='Raise TestError at test()', action='store_true', default=False)
    parser.add_argument('-atne', '--after_test_normal_error', help='Raise RuntimeError at after_test()', action='store_true', default=False)
    parser.add_argument('-atte', '--after_test_test_error', help='Raise TestError at after_test()', action='store_true', default=False)

    test = TestStepLoggingSample(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
