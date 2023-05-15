# -*- coding: utf-8 -*-
""" Test for simulate auto backup
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from kdp_scripts.stability_tests.auto_backup import AutoBackup as KDPAutoBackup


class AutoBackup(TestCase, KDPAutoBackup):

    TEST_SUITE = 'Stability Tests'
    TEST_NAME = 'Auto backup Test'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-35955'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Auto back test for Kamino ***
        """)

    parser.add_argument('-fu', '--file_url', help='Source file URL', metavar='URL')
    parser.add_argument('-lp', '--local_path', help='Local path to uplaod', metavar='PATH', default='local')

    test = AutoBackup(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
