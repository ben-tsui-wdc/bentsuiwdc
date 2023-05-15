# -*- coding: utf-8 -*-
""" Maximum user limitation test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.restAPI import RestAPI
from kdp_scripts.test_utils.kdp_test_utils import gen_nasAdmin_client, init_session_for_2nd_user


class MaximumUserLimitationTest(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Maximum user limitation test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5843'

    def declare(self):
        self.rest_clients = []
        self.user_ids = []
        self.nas_clients = []
        self.total_2nd_user = 300
        self.template_2nd_user_email = 'wdcautotw+qawdc.limit{}@gmail.com'
        self.template_2nd_user_password = 'Auto1234'
        self.template_2nd_user_local_username = 'user{}'
        self.template_2nd_user_local_password = 'Test1234'
        self.template_2nd_user_space = 'user{}'
        #  control args
        #  2nd user only, need to notice there is one owner already in device
        self.not_attach_user = False
        self.attach_user_start_num = 1
        self.attach_user_end_num = 300
        self.not_wait_user_sync = False
        self.not_login_check = False
        self.login_user_start_num = 1
        self.login_user_end_num = 300
        self.login_user_fail_start = 300
        self.not_failing_attach_user_test = True
        self.not_enable_local_access = False
        self.enable_user_start_num = 1
        self.enable_user_end_num = 10
        self.enable_user_fail_start = 10

    def init(self):
        assert self.login_user_fail_start <= self.login_user_end_num, 'login_user_fail_start is too large'
        assert self.enable_user_fail_start <= self.enable_user_end_num, 'enable_user_fail_start is too large'

    def test(self):
        self.attach_users_test()
        if not self.not_enable_local_access:
            self.enable_local_access_test()

    def attach_users_test(self):
        self.log.info("Generating client instances")
        for i in xrange(1, self.total_2nd_user+1):
            post_log_name = 'User{}'.format(i)
            rest_client = RestAPI(
                uut_ip=self.env.uut_ip,
                env=self.env.cloud_env,
                username=self.template_2nd_user_email.format(i),
                password=self.template_2nd_user_password,
                log_name='RestAPI-{}'.format(post_log_name),
                init_session=False,
                stream_log_level=self.env.stream_log_level,
                env_inst=self.uut_owner.environment,  # just share the env object
                cloud_inst=self.uut_owner.cloud  # just share the cloud object
            )
            self.rest_clients.append(rest_client)
            nasadmin_client = gen_nasAdmin_client(
                inst=self,
                rest_client=rest_client,
                local_name=self.template_2nd_user_local_username.format(i),
                local_password=self.template_2nd_user_local_password,
                log_name='NasAdminClient-{}'.format(post_log_name),
                uac_limiter=self.nasadmin.uac_limiter  # share limiter for prevent 429 issue
            )
            self.nas_clients.append(nasadmin_client)

        if not self.not_attach_user:
            self.log.info("Attach users via cloud call - success set part")
            for idx, client in enumerate(self.rest_clients, 1):
                if self.attach_user_start_num <= idx < self.login_user_fail_start:
                    init_session_for_2nd_user(inst=self, user_2nd_inst=client)

        if not self.not_wait_user_sync:
            # +1 for owner
            self.ssh_client.wait_for_total_user_space_reach(to_number=self.login_user_fail_start)

        if not self.not_login_check:
            failed_to_login = []

            self.log.info('Log in owner user - success set part')
            for retry_num in xrange(1, 16):
                try:
                    self.nasadmin.login_owner()
                    self.log.info('Owner user is sync')
                    break
                except Exception as e:
                    if retry_num < 15:
                        self.log.info('Owner user seems not sync yet')
                        self.log.info('#{} waiting owner user sync to nasAdmin'.format(retry_num))
                        time.sleep(15)
                    else:
                        self.log.error('Owner user is still not sync to nasAdmin')
                        failed_to_login.append('owner')

            self.log.info('Log in 2nd users - success set part')
            for idx, rest_client in enumerate(self.rest_clients):
                user_idx = idx + 1
                if self.login_user_start_num <= user_idx < self.login_user_fail_start:
                    for retry_num in xrange(1, 16):
                        try:
                            resp = self.nas_clients[idx].login_with_cloud_token(cloud_token=rest_client.get_id_token())
                            self.log.info('{}th user is sync'.format(user_idx))
                            self.user_ids.append(resp['userID'])
                            break
                        except Exception as e:
                            self.log.info('Got an error: {}'.format(e))
                            if retry_num < 15:
                                self.log.info('{}th user seems not sync yet'.format(user_idx))
                                self.log.info('#{} waiting {}th user sync to nasAdmin'.format(retry_num, user_idx))
                                time.sleep(15)
                            else:
                                self.log.error('{}th user is still not sync to nasAdmin'.format(user_idx))
                                failed_to_login.append(user_idx)
                                self.user_ids.append(None)
                if failed_to_login:
                    if self.not_failing_attach_user_test:
                        self.log.error('Failed to login users: {}'.format(failed_to_login))
                    else:
                        raise self.err.TestFailure('Failed to login users: {}'.format(failed_to_login))

        if not self.not_attach_user:
            self.log.info("Attach users via cloud call - fail set part")
            #  attach them later in case of nasAdmin sync them first
            for idx, client in enumerate(self.rest_clients, 1):
                if self.login_user_fail_start <= idx <= self.attach_user_end_num:
                    init_session_for_2nd_user(inst=self, user_2nd_inst=client)

        if not self.not_wait_user_sync:
            self.ssh_client.wait_for_total_user_space_reach(to_number=self.total_2nd_user+1)

        if not self.not_login_check:
            success_to_login = []
            self.log.info('Log in 2nd users - fail set part')
            for idx, rest_client in enumerate(self.rest_clients):
                user_idx = idx + 1
                if self.login_user_fail_start <= user_idx <= self.attach_user_end_num:
                    try:
                        self.nas_clients[idx].login_with_cloud_token(cloud_token=rest_client.get_id_token())
                        self.log.error('{}th user is sync'.format(user_idx))
                        success_to_login.append(user_idx)
                    except Exception as e:
                        self.log.info('Got an error: {}'.format(e))
                        self.log.info('{}th user is failed as expect.'.format(user_idx))

            if success_to_login:
                if self.not_failing_attach_user_test:
                    self.log.error('Unexpected users are success to login: {}'.format(success_to_login))
                else:
                    raise self.err.TestFailure('Unexpected users are success to login: {}'.format(success_to_login))

    def enable_local_access_test(self):
        fail_users = []
        self.log.info('Enabling local access to owner user')
        token = self.nasadmin.login_owner()
        try:
            self.nasadmin.update_user(token['userID'], localAccess=True, username='owner', password='password')
        except Exception as e:
            self.log.error('Got an error on enabling owner access: {}'.format(e))
            fail_users.append('owner')

        for idx, n in enumerate(self.nas_clients, 1):
            if self.enable_user_start_num <= idx <= self.enable_user_end_num:
                self.log.info('Enabling local access to {}th user'.format(idx))
                try:
                    n.update_user(
                        self.user_ids[idx - 1], localAccess=True, username=n.local_name, password=n.local_password,
                        spaceName=self.template_2nd_user_space.format(idx))
                except Exception as e:
                    if idx >= self.enable_user_fail_start:
                        self.log.info('Got an error as expected: {}'.format(e))
                    else:
                        self.log.error('Got an error: {}'.format(e))
                        fail_users.append(idx)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Maximum user limitation test ***
        """)
    parser.add_argument(
        '-t2u', '--total_2nd_user', help='Total number of 2nd user', type=int, metavar='NUM', default=300)
    parser.add_argument(
        '-t2ue', '--template_2nd_user_email', help='Template for 2nd user email', metavar='TMP',
        default='wdcautotw+qawdc.limit{}@gmail.com')
    parser.add_argument(
        '-t2up', '--template_2nd_user_password', help='Template for 2nd user password', metavar='TMP',
        default='Auto1234')
    parser.add_argument(
        '-t2ulu', '--template_2nd_user_local_username', help='Template for 2nd user local username', metavar='TMP',
        default='user{}')
    parser.add_argument(
        '-t2ulp', '--template_2nd_user_local_password', help='Template for 2nd user local password', metavar='TMP',
        default='Test1234')
    parser.add_argument('-nau', '--not_attach_user', help='Do not attach 2nd user', action='store_true', default=False)
    parser.add_argument(
        '-ausn', '--attach_user_start_num', help='Start number of 2nd user for attachment', type=int, metavar='NUM',
        default=1)
    parser.add_argument(
        '-auen', '--attach_user_end_num', help='End number of 2nd user for attachment', type=int, metavar='NUM',
        default=300)
    parser.add_argument('-nwus', '--not_wait_user_sync', help='Do not wait for 2nd user sync up', action='store_true',
        default=False)
    parser.add_argument('-nlc', '--not_login_check', help='Do not run login checks', action='store_true', default=False)
    parser.add_argument(
        '-lusn', '--login_user_start_num', help='Start number of 2nd user for login check', type=int, metavar='NUM',
        default=1)
    parser.add_argument(
        '-luen', '--login_user_end_num', help='End number of 2nd user for login check', type=int, metavar='NUM',
        default=300)
    parser.add_argument(
        '-lufs', '--login_user_fail_start', help='Start number of 2nd user for failing on login check', type=int,
        metavar='NUM', default=300)
    parser.add_argument('-nfaut', '--not_failing_attach_user_test', help='Do not stop test on failing attach user test',
        action='store_true', default=False)
    parser.add_argument('-nela', '--not_enable_local_access', help='Do not run enable local access test',
        action='store_true', default=False)
    parser.add_argument(
        '-eusn', '--enable_user_start_num', help='Start number of 2nd user for enabling local access', type=int,
        metavar='NUM', default=1)
    parser.add_argument(
        '-euen', '--enable_user_end_num', help='End number of 2nd user for enabling local access', type=int,
        metavar='NUM', default=10)
    parser.add_argument(
        '-eufs', '--enable_user_fail_start', help='Start number of 2nd user for failing on enabling local access', type=int,
        metavar='NUM', default=10)

    test = MaximumUserLimitationTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
