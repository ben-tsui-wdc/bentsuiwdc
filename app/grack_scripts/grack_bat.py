# -*- coding: utf-8 -*-
""" GRack BAT test.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GrackIntegrationTestArgument
from middleware.grack_integration_test import GrackIntegrationTest

# test cases
from grack_scripts.create_single_raid import CreateRAID
from grack_scripts.delete_raid import DeleteRAID
from grack_scripts.add_hot_spare import AddHotSpare
from grack_scripts.grow_raid import GrowRAID
from grack_scripts.shrink_raid import ShrinkRAID
from grack_scripts.mount_raid import MountRAID
from grack_scripts.add_workspace import AddWorkSpace

class GRack_BAT(GrackIntegrationTest):

    TEST_SUITE = 'GRack_BAT'
    TEST_NAME = 'GRack_BAT'

    def init(self):
        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            self.integration.add_testcases(testcases=[
                (DeleteRAID, {'create_raid': True}),
                (CreateRAID, {'delete_raid': True}),
                MountRAID,
                AddHotSpare,
                AddWorkSpace,
                GrowRAID,
                ShrinkRAID
            ])

if __name__ == '__main__':
    parser = GrackIntegrationTestArgument("""\
        *** Integration Test on Grack Platform ***
        Examples: ./run.sh grack_scripts/grack_bat.py --uut_ip 10.92.234.16\
        """)

    # Test Arguments
    parser.add_argument('--version_check', help='firmware version to compare')
    parser.add_argument('--single_run', help='Run single case for Yoda BAT')

    test = GRack_BAT(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
