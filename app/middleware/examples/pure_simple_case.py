# -*- coding: utf-8 -*-
""" A test with run core test behavior of template.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import CoreInputArgumentParser
from middleware.core.test_case import TestCase


class SimpleTest(TestCase):

    TEST_SUITE = 'SimpleTests'
    TEST_NAME = 'SimpleTest'

    def init(self):
        self.some_var = 'some_var'
        self.log.warning('Run init step.')

    def before_test(self):
        self.log.warning('Run before_test step.')

    def test(self):
        self.log.warning("Run test step! I have {0} and {1}".format(self.some_var, self.my_var))

    def after_test(self):
        self.log.warning('Run after_test step.')

    def before_loop(self):
        self.log.warning('Run before_loop step.')

    def after_loop(self):
        self.log.warning('Run after_loop step.')


if __name__ == '__main__':
    parser = CoreInputArgumentParser("""\
        *** Simple Test ***
        Examples: ./run.sh middleware/examples/pure_simple_case.py --uut_ip 10.136.137.159\
        """)
    # Test Arguments
    parser.add_argument('-mv', '--my_var', help='An additional variable.', type=int, default=1000)

    test = SimpleTest(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
