# -*- coding: utf-8 -*-
""" Test case to check rate limitation on nasAdmin.
"""
# std modules
import sys
import time
import random
import requests
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class CheckNasAdminRateLimitation(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'Check NasAdmin Rate Limitation'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-6852'
    PRIORITY = 'Major'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.limitations = {
            'authRateLimiter': (20, 60), # authRateLimiter: 20 requests per 1 minute
            'baseRateLimiter': (2000, 10*60), # baseRateLimiter: 2000 requests per 10 minutes
            'generalRateLimiter': (4000, 10*60) # generalRateLimiter: 4000 requests per 10 minutes
        }

    def test(self):
        # test authRateLimiter
        start_1 = time.time()
        self.log.info('Testing for authRateLimiter: {} requests/{} sec'.format(*self.limitations['authRateLimiter']))
        ret1 = self.checkAuthRateLimiter()
        if ret1:
            self.log.info('Sleep {} secs...'.format(self.limitations['authRateLimiter'][1]))
            while time.time() - start_1 < self.limitations['authRateLimiter'][1]:
                time.sleep(1)
            self.log.info('Testing for authRateLimiter: {} requests/{} sec'.format(*self.limitations['authRateLimiter']))
            ret1 =  self.checkAuthRateLimiter()

        # test baseRateLimiter
        start_2 = time.time()
        self.log.info('Testing for baseRateLimiter: {} requests/{} sec'.format(*self.limitations['baseRateLimiter']))
        ret2 = self.checkBaseRateLimiter()

        # test generalRateLimiter
        start_3 = time.time()
        self.log.info('Testing for generalRateLimiter: {} requests/{} sec'.format(*self.limitations['generalRateLimiter']))
        ret3 = self.checkGeneralRateLimiter()

        if ret2:
            self.log.info('Sleep {} secs...'.format(self.limitations['baseRateLimiter'][1]))
            while time.time() - start_2 < self.limitations['baseRateLimiter'][1]:
                time.sleep(1)
            self.log.info('Testing for baseRateLimiter: {} requests/{} sec'.format(*self.limitations['baseRateLimiter']))
            ret2 = self.checkBaseRateLimiter()

        if ret3:
            self.log.info('Sleep {} secs...'.format(self.limitations['generalRateLimiter'][1]))
            while time.time() - start_3 < self.limitations['generalRateLimiter'][1]:
                time.sleep(1)
            self.log.info('Testing for generalRateLimiter: {} requests/{} sec'.format(*self.limitations['generalRateLimiter']))
            ret3 = self.checkGeneralRateLimiter()

        assert ret1 == ret2 == ret3 == True, "Limiation is not exepected"

    def print_process(self, now, max):
        sys.stdout.write('\r{0}/{1}'.format(now, max))

    def checkAuthRateLimiter(self):
        self.log.info('Reach the limation...')
        for idx in xrange(1, self.limitations['authRateLimiter'][0]+1):
            resp = requests.request(method='POST', url='http://{}/nas/v1/auth'.format(self.env.uut_ip), data={"username":"admin","password":"QWEASDZXC"})
            self.print_process(idx, self.limitations['authRateLimiter'][0])
            if resp.status_code == 429:
                self.log.error("No.{} | /nas/v1/auth | {} | {}/{}".format(
                    idx, resp.status_code, resp.headers['X-Ratelimit-Remaining'], resp.headers['X-Ratelimit-Limit']))
                return False
        self.log.info('Access one more time...')
        resp = requests.request(method='POST', url='http://{}/nas/v1/auth'.format(self.env.uut_ip), data={"username":"admin","password":"QWEASDZXC"})
        if resp.status_code != 429:
            self.log.error("No.{} | /nas/v1/auth | {} | {}/{}".format(
                self.limitations['authRateLimiter'][0]+1, resp.status_code, resp.headers['X-Ratelimit-Remaining'], resp.headers['X-Ratelimit-Limit']))
            return False
        return True

    def checkBaseRateLimiter(self):
        self.log.info('Reach the limation...')
        for idx in xrange(1, self.limitations['baseRateLimiter'][0]+1):
            resp = requests.request(method='GET', url='http://{}'.format(self.env.uut_ip))
            self.print_process(idx, self.limitations['baseRateLimiter'][0])
            if resp.status_code == 429:
                self.log.error("No.{} | / | {} | {}/{}".format(
                    idx, resp.status_code, resp.headers['X-Ratelimit-Remaining'], resp.headers['X-Ratelimit-Limit']))
                return False
        self.log.info('Access one more time...')
        resp = requests.request(method='GET', url='http://{}'.format(self.env.uut_ip))
        if resp.status_code != 429:
            self.log.error("No.{} | /n | {} | {}/{}".format(
                self.limitations['baseRateLimiter'][0]+1, resp.status_code, resp.headers['X-Ratelimit-Remaining'], resp.headers['X-Ratelimit-Limit']))
            return False
        return True

    def checkGeneralRateLimiter(self):
        endpints = [('GET', '/nas/v1/auth'), ('PUT', '/nas/v1/auth'), ('DELETE', '/nas/v1/auth'), ('GET', '/nas/v1/locale'), 
        ('GET', '/nas/v1/api'), ('GET', '/web/'), ('GET', '/cgi-bin/'), ('GET', '/xml/')]

        self.log.info('Reach the limation...')
        for idx in xrange(1, self.limitations['generalRateLimiter'][0]+1):
            m, u = random.choice(endpints)
            resp = requests.request(method=m, url='http://{}{}'.format(self.env.uut_ip, u))
            self.print_process(idx, self.limitations['generalRateLimiter'][0])
            if resp.status_code == 429:
                self.log.error("No.{} | {} | {} | {}/{}".format(
                    idx, u, resp.status_code, resp.headers['X-Ratelimit-Remaining'], resp.headers['X-Ratelimit-Limit']))
                return False
        self.log.info('Access one more time...')
        ret = True
        for m, u in endpints:
            resp = requests.request(method=m, url='http://{}{}'.format(self.env.uut_ip, u))
            if resp.status_code != 429:
                self.log.error("{} | {} | {}/{}".format(
                    u, resp.status_code, resp.headers['X-Ratelimit-Remaining'], resp.headers['X-Ratelimit-Limit']))
                ret = False
        return ret

if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Check rate limitation on nasAdmin ***
        """)

    if CheckNasAdminRateLimitation(parser).main():
        sys.exit(0)
    sys.exit(1)
