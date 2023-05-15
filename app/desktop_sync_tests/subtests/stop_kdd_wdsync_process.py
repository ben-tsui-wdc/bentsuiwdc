# -*- coding: utf-8 -*-
""" Test for desktop sync tool: stop kdd and wdsync process (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import time
# platform modules
from middleware.test_case import TestCase


class StopKddWdsyncProcess(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'Stop_KDD_WDSync_Process'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']

    def test(self):
        self.log.info("Stopping KDD and WDSync process")
        self.ds_obj.stop_kdd_wdsync_process()
        time.sleep(10)  # wait for kdd and wdsync process to stop
        kdd_process, wdsync_process = self.ds_obj.check_kdd_wdsync_process()
        if kdd_process or wdsync_process:
            raise self.err.TestFailure("KDD and WDSync process is not stopped successfully!")
        else:
            self.log.info("Stop KDD and WDSYnc process passed")


