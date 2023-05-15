# -*- coding: utf-8 -*-
""" Test for 1st Access case (KAM-21038, KAM-21151).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# platform modules
from middleware.sub_test import SubTest
from platform_libraries.compare import local_md5sum, md5sum_with_iter


class SingleFisrtAccessTest(SubTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Single_1st_Access'

    def declare(self):
        self.auth_by_header = True
        self.share_filed = 'shared_file'

    def init(self):
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']
        self.access_token = self.share[self.share_filed]['access_token']
        if self.share[self.share_filed].get('status'):
            raise self.err.StopTest('File is already in cache')
        self.share[self.share_filed]['status'] = None

    def test(self):
        resp = self.test_single_1st_access(self.cache_url, self.access_token, self.share_filed, auth_by_header=self.auth_by_header)
        self.verify_content(source_file=self.share[self.share_filed]['file_name'], response_obj=resp)

    def test_access(self, cache_url, access_token, status_codes, close_after_ckeck=False, auth_by_header=True):
        resp = self.uut_owner.get_content_from_cache(cache_url, access_token, auth_by_header=auth_by_header)
        self.log.info('* Status Code: {}'.format(resp.status_code))

        if resp.status_code not in status_codes:
            self.log.error('Status Code should be {}, but it is {}'.format(status_codes, resp.status_code))
            self.uut_owner.log_response(response=resp, logger=self.log.error)
            raise self.err.TestFailure('API reponse is not expected')

        if close_after_ckeck:
            resp.close()

        return resp

    def test_single_1st_access(self, cache_url, access_token, share_filed, status_codes=[200], auth_by_header=True):
        resp = self.test_access(cache_url, access_token, status_codes, auth_by_header=auth_by_header)
        # Record test file is caching
        self.share[share_filed]['status'] = 'caching'
        return resp

    def verify_content(self, source_file, response_obj):
        cache_md5 = md5sum_with_iter(response_obj.iter_content, trace_logging=self.log)
        self.log.info('MD5 of cache file: {}'.format(cache_md5))
        source_md5 = local_md5sum(source_file)
        self.log.info('MD5 of source file: {}'.format(source_md5))

        if cache_md5 != source_md5:
            self.log.info('Verify md5sum: FAILED.')
            raise self.err.TestFailure('Content md5sum is incorrect.')
        self.log.info('Verify md5sum: PASSED.')
