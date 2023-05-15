# -*- coding: utf-8 -*-
""" Test for desktop sync tool: start kdd and wdsync process (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import time
# platform modules
from middleware.test_case import TestCase


class StartKDDWDSyncProcess(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'Start_KDD_WDSync_Process'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']

    def test(self):
        self.log.info("Starting KDD and WDSync process")
        self.ds_obj.start_kdd_wdsync_process()
        time.sleep(10)  # wait for kdd and wdsync process to start
        kdd_process, wdsync_process = self.ds_obj.check_kdd_wdsync_process()
        if not kdd_process:
            self.log.error("KDD process is not started!")

        if not wdsync_process:
            self.log.error("WDSync process is not started!")

        if not kdd_process or not wdsync_process:
            raise self.err.TestFailure("KDD and WDSync process is not started successfully!")
        else:
            self.log.info("Start KDD and WDSync process passed")


