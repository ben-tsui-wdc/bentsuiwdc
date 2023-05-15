# -*- coding: utf-8 -*-
""" Test for Access with DUT offline case. (KAM-21085, KAM-21088).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

import time
# platform modules
from middleware.sub_test import SubTest


class SingleOfflineAccessTest(SubTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Single_Offline_Access'

    def declare(self):
        self.share_filed = 'shared_file'
        self.power_switch_port = None

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']
        self.access_token = self.share[self.share_filed]['access_token']
        if not self.power_switch:
            raise self.err.StopTest('Need to enable power_switch')
        # Try to get power_switch_port from self.env.UUT if it isn't supplied.
        if self.power_switch_port is None:
            self.power_switch_port = self.env.UUT.get('powerSwitch', {}).get('port')
        if not self.power_switch_port:
            raise self.err.StopTest('Need to power_switch_port')

    def test(self):
        # TODO: Rewrite me after KAM-21149 fix.
        wiat_time = 60*1
        self.log.info('Power off DUT.')
        self.power_switch.power_off(self.power_switch_port)
        #self.log.info('Wait {}s...'.format(wiat_time)) # Too fast to request cache may return 500 error.
        #time.sleep(wiat_time)
        try:
            # 1st fist access return 500.
            print '1st'*20
            self.test_single_offline_access(self.cache_url, self.access_token, status_codes=[500, 503])
            print '2nd'*20
            self.test_single_offline_access(self.cache_url, self.access_token)
        finally:
            self.log.info('Power on DUT.')
            self.power_switch.power_on(self.power_switch_port)
            self.adb.wait_for_device_boot_completed()
            #self.log.info('Wait {}s...'.format(wiat_time)) # Wiat device for syncing to ED, or may return
                                                           # 404 error at the fellowing test.
            #time.sleep(wiat_time)
            while 1:
                try:
                    # 1st fist access return 500.
                    self.test_single_offline_access(self.cache_url, self.access_token, status_codes=[200])
                    print 'PASS'*20
                    break
                except:
                    time.sleep(10)

    def test_single_offline_access(self, cache_url, access_token, status_codes=[503]):
        resp = self.uut_owner.get_content_from_cache(cache_url, access_token)
        self.log.info('* Status Code: {}'.format(resp.status_code))
        if resp.status_code not in status_codes:
            self.log.error('Status Code should be {}, but it is {}'.format(status_codes, resp.status_code))
            self.uut_owner.log_response(response=resp, logger=self.log.error)
            raise self.err.TestFailure('API reponse is not expected')
        return resp
