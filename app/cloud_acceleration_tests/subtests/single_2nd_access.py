# -*- coding: utf-8 -*-
""" Test for 2nd access case. (KAM-21086, KAM-21152).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import time
# test case
from cloud_acceleration_tests.subtests.single_1st_access import SingleFisrtAccessTest
# 3rd party modules
import requests


class SingleSecondAccessTest(SingleFisrtAccessTest):

    TEST_SUITE = 'Cloud_Acceleration_Tests'
    TEST_NAME = 'Single_2nd_Access'

    def declare(self):
        self.auth_by_header = True
        self.share_filed = 'shared_file'
        self.wait_time = None #60*5 # Timeout to wait for cahcing file in seconds.

    def init(self):
        # Check test file is shared.
        if self.share_filed not in self.share:
            raise self.err.StopTest('No shared file information')
        self.cache_url = self.share[self.share_filed]['cache_url']
        self.access_token = self.share[self.share_filed]['access_token']
        # Check test file is caching.
        if self.share[self.share_filed].get('status') != 'caching':
            raise self.err.StopTest('File is not caching')

    def test(self):
        self.test_single_2nd_access(
            cache_url=self.cache_url, access_token=self.access_token, share_filed=self.share_filed, wait_time=self.wait_time,
            auth_by_header=self.auth_by_header)
        idx = 0 # For monitor 104 Connection broken issue.
        while True:
            try:
                resp = self.test_access_redirect_url(
                    redirect_url=self.share[self.share_filed]['redirect_url'], share_filed=self.share_filed)
                self.verify_content(source_file=self.share[self.share_filed]['file_name'], response_obj=resp)
            except requests.exceptions.ChunkedEncodingError, e:
                idx+=1
                self.log.warning('Catch exception: {}'.format(e))
                if idx == 6: # Retry 5 times
                    raise
                time.sleep(10)
                self.log.warning('Retry#{} access S3...'.format(idx))
            else:
                break

    def test_single_2nd_access(self, cache_url, access_token, share_filed, wait_time, retry_delay=30, auth_by_header=True):
        nas_proxy_prefix = self.uut_owner.environment.get_external_uri()

        while True:
            if wait_time and self.timing.is_timeout(timeout=wait_time):
                raise self.err.TestFailure('Timeout {}s to wait for caching.'.format(wait_time))

            # Send test reuqest.
            resp = self.uut_owner.get_content_from_cache(cache_url, access_token, auth_by_header=auth_by_header)
            self.log.info('* Status Code: {}'.format(resp.status_code))

            # Verify status code of API reponse, and we excpet reponse 303 redirect to S3.
            if resp.status_code == 200:
                self.log.info('Sleep {}s to wiat for caching complete.'.format(retry_delay))
                resp.close()
                time.sleep(retry_delay)
                continue
            elif resp.status_code == 303:
                redirect_url = resp.headers.get('Location')
                self.log.info('* Location Header: {}'.format(redirect_url))

                if redirect_url.startswith(nas_proxy_prefix):
                    self.log.info('Redirect to NAS')
                    resp.close()
                    continue
                else:
                    self.log.info('Redirect to S3')
                    break
            else:
                self.log.error('Status Code should be 200 or 303, but it is {}'.format(resp.status_code))
                self.uut_owner.log_response(response=resp, logger=self.log.error)
                self.logging_nas_response()
                raise self.err.TestFailure('API reponse is not expected')

        # Record test file is already cached
        self.share[share_filed]['redirect_url'] = redirect_url
        self.share[share_filed]['status'] = 'cached'
        return resp

    def test_access_redirect_url(self, redirect_url, share_filed):
        resp = self.uut_owner.send_request(
            method='GET',
            url=redirect_url,
            allow_redirects=False,
            stream=True
        )
        if resp.status_code != 200:
            self.log.error('Status Code should be 200, but it is {}'.format(resp.status_code))
            self.uut_owner.log_response(response=resp, logger=self.log.error)
            raise self.err.TestFailure('API reponse is not expected')

        # Update record.
        etag = resp.headers.get('ETag')
        self.log.info('* ETag Header: {}'.format(etag))
        self.share[share_filed]['etag'] = etag
        return resp

    def logging_nas_response(self):
        """ Use to log file content reponse from NAS and via proxy. """
        share_info = self.share[self.share_filed]

        # Logging response via proxy
        resp = self.uut_owner.bearer_request(
            method='GET',
            url=share_info['proxy_url']+share_info['file_content_post_url'],
            allow_redirects=False,
            stream=True
        )
        self.log.warning('File content response via proxy:')
        self.uut_owner.log_response(response=resp, logger=self.log.warning, show_content=False)
        resp.close()

        # Logging response from NAS
        resp = self.uut_owner.bearer_request(
            method='GET',
            url='http://{}{}'.format(self.uut_owner.uut_ip, share_info['file_content_post_url']),
            allow_redirects=False,
            stream=True
        )
        self.log.warning('File content response from NAS:')
        self.uut_owner.log_response(response=resp, logger=self.log.warning, show_content=False)
        resp.close()
