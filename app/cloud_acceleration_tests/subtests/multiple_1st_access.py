# -*- coding: utf-8 -*-
""" Test for Multiple 1st access case (KAM-21039).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import threading
# platform modules
from platform_libraries.test_thread import MultipleThreadExecutor
# test case
from cloud_acceleration_tests.subtests.single_1st_access import SingleFisrtAccessTest


class MultipleFisrtAccessTest(SingleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Multiple_1st_Access'

    def test(self):
        # Start multiple access
        self.test_multiple_access(target=self.first_access_for_multiple_thread)

    def first_access_for_multiple_thread(self):
        resp = self.test_single_1st_access(self.cache_url, self.access_token, self.share_filed, status_codes=[200, 303],
            auth_by_header=self.auth_by_header)
        if resp.status_code == 303: # Just pass it if this thread request too slow.
            self.log.warning('It seems this thread request is too slow, please check response')
            self.uut_owner.log_response(response=resp, logger=self.log.warning)
            return
        self.verify_content(source_file=self.share[self.share_filed]['file_name'], response_obj=resp)

    def test_multiple_access(self, group=None, target=None, name=None, args=None, kwargs=None):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.add_threads_by_func(number_of_thread=2, group=group, target=target, name=name, args=args, kwargs=kwargs)
        mte.run_threads()
