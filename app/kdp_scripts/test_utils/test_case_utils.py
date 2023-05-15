# -*- coding: utf-8 -*-
""" Test Utils for test case
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import time
# platform modules
from kdp_scripts.test_utils.kdp_test_utils import attach_2nd_user, gen_nasAdmin_client
# 3rd library
import requests

# nasAdmin test for 2nd user

def nsa_declare_2nd_user(self):
    self.username_2nd = 'wdcautotw+qawdc.rnd30@gmail.com'
    self.password_2nd = 'Auto1234'
    self.local_username_2nd = 'user_2nd'
    self.local_password_2nd = 'Test1234'
    self.detach_2nd_user = False
    self.rest_2nd = None
    self.nasadmin_2nd = None

def nsa_after_test_user(self, wait_for_user_detached=False):
    if self.detach_2nd_user and self.rest_2nd:
        self.rest_2nd.detach_user_from_device()
        if wait_for_user_detached:
            nsa_wait_for_2nd_user_detach(self)

def nsa_wait_for_2nd_user_detach(self, retry_times=12, interval=15):
    if not self.nasadmin_2nd or not self.rest_2nd:
        self.log.info('Missing client instances')
        return
    for idx in xrange(retry_times):
        try:
            self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.get_id_token())
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                self.nasadmin_2nd.log.info('User is detached')
                return
            self.nasadmin_2nd.log.warning('Got an error: {}'.format(e))
        if idx == 11:
            raise RuntimeError('User is still attached')
        else:
            self.nasadmin_2nd.log.info('User is still attached, check again after {} secs'.format(interval))
            time.sleep(interval)

def nsa_add_argument_2nd_user(parser):
    parser.add_argument('-u2', '--username_2nd', help='username for 2nd user', default='wdcautotw+qawdc.rnd30@gmail.com')
    parser.add_argument('-p2', '--password_2nd', help='password for 2nd user', default='Auto1234')
    parser.add_argument('-lu2', '--local_username_2nd', help='Local username for 2nd user', default='user_2nd')
    parser.add_argument('-lp2', '--local_password_2nd', help='Local password for 2nd user', default='Test1234')
    parser.add_argument('-d2u', '--detach_2nd_user', help='detach 2nd user at end of test',
                        action='store_true', default=False)

def nsa_init_2nd_user(self, post_log_name='2ndUser', init_session=True):
    self.rest_2nd = attach_2nd_user(
        inst=self, username=self.username_2nd, password=self.password_2nd,
        log_name='RestAPI-{}'.format(post_log_name), init_session=init_session)
    self.log.debug('Registering RestSDK client for updating IP')
    self.utils.register_util_to_update_ip(util_inst=self.rest_2nd, update_method='update_device_ip')
    self.nasadmin_2nd = gen_nasAdmin_client(
        inst=self, rest_client=self.rest_2nd, local_name=self.local_username_2nd, local_password=self.local_password_2nd,
        log_name='NasAdminClient-{}'.format(post_log_name))
    self.log.debug('Registering nasAdmin client for updating IP')
    self.utils.register_util_to_update_ip(util_inst=self.nasadmin_2nd, update_method='update_device_ip')
    if init_session:
        for idx in xrange(1, 9):
            if idx > 1: self.log.info('#{} waiting 2nd user sync to nasAdmin'.format(idx))
            time.sleep(15)
            try:
                self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.get_id_token())
                self.log.info('2nd user is sync')
                return
            except Exception as e:
                self.log.info('Got an error: {}'.format(e))
                self.log.info('2nd user seems not sync yet')

def nsa_update_device_ip(self, ip):
    self.rest_2nd.update_device_ip(ip)
    self.nasadmin_2nd.update_device_ip(ip)
