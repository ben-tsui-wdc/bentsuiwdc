# -*- coding: utf-8 -*-
""" Test for Multiple 2nd Access case. (KAM-21171).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import time
import threading
# test case
from cloud_acceleration_tests.subtests.multiple_1st_access import MultipleFisrtAccessTest
from cloud_acceleration_tests.subtests.single_2nd_access import SingleSecondAccessTest


class MultipleSecondAccessTest(SingleSecondAccessTest, MultipleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Multiple_2nd_Access'

    def test(self):
        # Start multiple access
        self.test_multiple_access(target=super(MultipleSecondAccessTest, self).test)
