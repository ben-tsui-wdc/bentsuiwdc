# -*- coding: utf-8 -*-
""" A test with run KDP test behavior of template.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class KDPSimpleTest(KDPTestCase):

    TEST_SUITE = 'SimpleTests'
    TEST_NAME = 'SimpleTest'

    def init(self):
        self.some_var = 'some_var'
        print 'Run init step.'

    def before_test(self):
        print 'Run before_test step.'

    def test(self):
        print "Run test step! I have {0} and {1}".format(self.some_var, self.my_var)

    def after_test(self):
        print 'Run after_test step.'

    def before_loop(self):
        print 'Run before_loop step.'

    def after_loop(self):
        print 'Run after_loop step.'


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Simple Test on KDP ***
        Examples: ./run.sh middleware/examples/kdpsimple_case.py --uut_ip 10.136.137.159\
        """)
    # Test Arguments
    parser.add_argument('-mv', '--my_var', help='An additional variable.', type=int, default=1000)

    test = KDPSimpleTest(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
