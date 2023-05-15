# -*- coding: utf-8 -*-
""" NasAdmin (KDP) API libraries
"""

___author___ = 'Estvan Huang <Estvan.Huang@wdc.com>'

# std modules
import json
import time
from datetime import datetime
# platform modules
import common_utils
from platform_libraries.http_client import HTTPRequester
# 3rd modules
import requests


@common_utils.logger()
class NasAdminClient(HTTPRequester):

    NAS_BASE = '/nas/'
    AUTH = NAS_BASE + 'v2/auth'
    AUTHV3 = NAS_BASE + 'v3/auth'
    OWNER = NAS_BASE + 'v2/owner'
    SPACES = NAS_BASE + 'v2/spaces'
    USERS = NAS_BASE + 'v2/users'
    DEVICE = NAS_BASE + 'v2/device'
    NETWORK = NAS_BASE + 'v2/network'
    STORAGE = NAS_BASE + 'v2/storage'
    VALIDATION = NAS_BASE + 'v2/validation'
    SYSTEM = NAS_BASE + 'v2/system'

    def __init__(self, ip, rest_client=None, local_name="owner", local_password="password",
            root_log='KAT', log_name=None, stream_log_level=None, uac_limiter=None):
        """
        rest_client:
            Used for login with cloud token. If owner enable local access, rest_client is not required.
        local_password:
            For getting token when rest_client is not provided.
        """
        self.init_logger(root_log=root_log, log_name=log_name, stream_log_level=stream_log_level)
        self.user_id = None
        self.set_ip(ip)
        self.rest_client = rest_client
        self.local_name = local_name
        self.local_password = local_password
        self.token_expire_time = 60 * 5
        self.refresh_reserve_secs = 60 * 2
        self._user_access_token = None
        self.user_refresh_token = None
        self.token_start_time = None
        self.hiddenToken = False
        self.uac_limiter = uac_limiter if uac_limiter else UnAuthCallLimiter()
        super(NasAdminClient, self).__init__(log_inst=self.log, debug_response=True)

    @property
    def user_access_token(self):
        if self._user_access_token:
            time_passed = (datetime.now() - self.token_start_time).seconds
            if time_passed < (self.token_expire_time - self.refresh_reserve_secs):
                self.log.debug('Use existed token, it will be expired in {} secs'.
                               format(self.token_expire_time - time_passed))
                return self._user_access_token
            else:
                self.log.info('Token will be expired soon, renew it.')
                # TODO: use refresh token if we need

        if self.rest_client: # use cloud token as default
            self.login_with_cloud_token(self.rest_client.get_id_token())
        elif self.local_name and self.local_password:
            self.login_with_local_password(self.local_name, self.local_password)
        else:
            raise RuntimeError("No information for getting user token")

        return self._user_access_token

    @user_access_token.setter
    def access_token(self, value):
        self._user_access_token = value

    def set_rest_client(self, rest_client):
        self.log.info('set rest_client')
        self.rest_client = rest_client
        return self

    def set_ip(self, ip):
        self.ip = ip
        self.set_base_url('http://' + ip)
        return self

    def set_base_url(self, base_url):
        self.base_url = base_url
        return self

    def update_token(self, token_response):
        self._user_access_token = token_response['access']
        self.user_refresh_token = token_response['refresh']
        self.token_start_time = datetime.now()
        self.user_id = token_response.get('userID')
        return token_response

    def update_device_ip(self, ip):
        self.log.info('Current IP: {} now change to IP: {}...'.format(self.ip, ip))
        self.set_ip(ip)

    def hide_access_token(self):
        if self.hiddenToken:
            self.log.debug('Access token is hidden')
            return
        self.log.debug('Hiding access token')
        self.enable_limiter()
        self.hiddenToken = True

    def reveal_access_token(self):
        if not self.hiddenToken:
            self.log.debug('Access token is not hidden')
            return
        self.log.debug('Revealing access token')
        self.disable_limiter()
        self.hiddenToken = False

    def enable_limiter(self):
        self.before_send_request = self.uac_limiter.check_and_delay

    def disable_limiter(self):
        self.before_send_request = None

    def unauth_json_request(self, method, url, set_corid=True, **kwargs):
        """ Send request without user access token. """
        try:
            self.enable_limiter()
            headers = {
                'Content-Type': 'application/json'
            }
            if 'headers' in kwargs and kwargs['headers']:
                headers.update(kwargs['headers'])
            kwargs['headers'] = headers
            return self.json_request(method, url, set_corid, **kwargs)
        finally:
            self.disable_limiter()

    # Access Endpoints

    def login_with_cloud_token(self, cloud_token):
        self.log.info('Getting token with cloud token')
        resp_dict = self._login_nasAdmin(
            data=json.dumps({
                "passcodeType": "cloudToken",
                "passcode": cloud_token
            })
        )
        return self.update_token(resp_dict)

    def login_with_local_password(self, username=None, password=None):
        # Enable local access is required
        self.log.info('Getting token with local password')
        if not username:
            username = self.local_name
        if not password:
            password = self.local_password
        resp_dict = self._login_nasAdmin(
            data=json.dumps({
                "passcodeType": "localPassword",
                "username": username,
                "passcode": password
            })
        )
        return self.update_token(resp_dict)

    def _login_nasAdmin(self, data, headers=None):
        self.log.info('Login nasAdmin with {}'.format(data))
        resp = self.unauth_json_request(
            method='POST', url=self.base_url + self.AUTHV3, data=data, headers=headers)
        if resp.status_code != 200:
            self.error('Failed to login user', resp)
        return resp.json()

    def login_owner(self):
        if self.rest_client: # use cloud token as default
            return self.login_with_cloud_token(self.rest_client.owner_access_token)
        elif self.local_name and self.local_password:
            return self.login_with_local_password(self.local_name, self.local_password)
        else:
            self.log.warning('No data for logging owner')

    def refresh_token(self, refresh_token=None):
        return self._refresh_token(data=json.dumps({
            "refresh": refresh_token if refresh_token else self.user_refresh_token
        }))

    def _refresh_token(self, data, headers=None):
        self.log.info('Refreshing user token with {}'.format(data))
        resp = self.user_request(
            method='PUT', url=self.base_url + self.AUTH, data=data, headers=headers)
        if resp.status_code != 200:
            self.error('Failed to refresh user token', resp)
        return self.update_token(resp.json())

    def get_public_key(self):
        self.log.info('Getting public key')
        resp = self.unauth_json_request(
            method='GET', url=self.base_url + self.AUTH + '/public-key'
        )
        if resp.status_code != 200:
            self.error('Failed to public key', resp)
        return resp.json()

    def user_request(self, method, url, set_corid=True, **kwargs):
        """ Send request with user access token. """
        headers = {
            'Content-Type': 'application/json'
        }
        if not self.hiddenToken:
            headers['Authorization'] = self.user_access_token
        if 'headers' in kwargs and kwargs['headers']:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        return self.json_request(method, url, set_corid, **kwargs)

    def wait_for_nasAdmin_works(self, timeout=60*5, wait_more_seconds=False):
        self.log.debug('Wait for nasAdmin works...')
        start_time = time.time()
        while (timeout > time.time() - start_time):
            if not self.is_nasAdmin_working():
                self.log.info('nasAdmin is not ready yet...')
                time.sleep(5)
            else:
                self.log.info('nasAdmin is ready')
                if wait_more_seconds:
                    self.log.info('Wait 20 sec to let device ready')
                    time.sleep(20)
                return True
        self.log.info("nasAdmin does't work")
        return False

    def wait_for_owner_attached(self, timeout=60*5, wait_more_seconds=False):
        self.log.debug('Wait for owner attached...')
        start_time = time.time()
        while (timeout > time.time() - start_time):
            if not self.is_owner_attached():
                self.log.info('Owner is not attached yet...')
                time.sleep(5)
            else:
                self.log.info('Owner is attached')
                if wait_more_seconds:
                    self.log.info('Wait 20 sec to let device sync')
                    time.sleep(20)
                return True
        self.log.info("Owner isn't attached")
        return False

    def can_access_nasAdmin(self, return_resp=False):
        try:
            resp = self.get_device()
            assert 'ready' in resp
        except Exception as e:
            self.log.warning('Cannot access nasAdmin')
            if return_resp:
                return
            return False
        if return_resp:
            return resp
        return True

    def is_nasAdmin_working(self, provide_resp=None):
        call_resp = provide_resp
        if not call_resp:
            call_resp = self.get_device()
        return True if call_resp.get('ready', None) else False

    def is_owner_attached_restsdk(self):
        if not self.rest_client:
            self.log.info("No rest_client is provided")
            return False
        return True if self.rest_client.get_device().json().get('firstUserAttached', None) else False

    def is_owner_attached(self, provide_resp=None):
        call_resp = provide_resp
        if not call_resp:
            call_resp = self.get_device()
        return True if call_resp.get('ownerAttached', None) else False

    # Owner Endpoints

    def get_owner(self):
        self.log.info('Getting owner')
        resp = self.user_request(method='GET', url=self.base_url + self.OWNER)
        if resp.status_code != 200:
            self.error('Failed to get owner', resp)
        return resp.json()

    # Space Endpoints

    def get_spaces(self):
        self.log.info('Getting all spaces')
        resp = self.user_request(method='GET', url=self.base_url + self.SPACES)
        if resp.status_code != 200:
            self.error('Failed to get all spaces', resp)
        return resp.json()

    def get_space(self, space_id):
        self.log.info('Getting a space with ' + space_id)
        resp = self.user_request(method='GET', url="{}{}/{}".format(self.base_url, self.SPACES, space_id))
        if resp.status_code != 200:
            self.error('Failed to get a space with ' + space_id, resp)
        return resp.json()

    def create_space(self, name, allUsers=False, localPublic=False, timeMachine=False):
        self.log.info('Creating a space: ' + name)
        resp = self.user_request(
            method='POST', url=self.base_url + self.SPACES,
            data=json.dumps({
                "name": name,
                "allUsers": allUsers,
                "localPublic": localPublic,
                "timeMachine": timeMachine
            }))
        if resp.status_code != 200:
            self.error('Failed to create space: ' + name, resp)
        return resp.json()

    def update_space(self, space_id, name=None, allUsers=None, localPublic=None, timeMachine=None):
        self.log.info('Updating a space: ' + space_id)
        payload = {}
        if name is not None:
            payload['name'] = name
        if allUsers is not None:
            payload['allUsers'] = allUsers
        if localPublic is not None:
            payload['localPublic'] = localPublic
        if timeMachine is not None:
            payload['timeMachine'] = timeMachine
        resp = self.user_request(
            method='PATCH', url="{}{}/{}".format(self.base_url, self.SPACES, space_id),
            data=json.dumps(payload))
        if resp.status_code != 200:
            self.error('Failed to update space: ' + space_id, resp)
        return resp.json()

    def delete_spaces(self, space_id):
        self.log.info('Deleting a space with ' + space_id)
        resp = self.user_request(method='DELETE', url="{}{}/{}".format(self.base_url, self.SPACES, space_id))
        if resp.status_code != 200:
            self.error('Failed to delete a space with ' + space_id, resp)

    def get_user_perms_for_space(self, space_id):
        self.log.info('Getting a user permission with ' + space_id)
        resp = self.user_request(method='GET', url="{}{}/{}/permissions".format(self.base_url, self.SPACES, space_id))
        if resp.status_code != 200:
            self.error('Failed to get user permission with ' + space_id, resp)
        return resp.json()

    def update_space_perm(self, space_id, user_id, permission):
        self.log.info('Updating permission: ' + permission + ' for ' + user_id + ' to space: ' + space_id)
        resp = self.user_request(
            method='PUT', url="{}{}/{}/permissions/{}".format(self.base_url, self.SPACES, space_id, user_id),
            data=json.dumps({
                'permission': permission # "read", "readWrite" or "noAccess"
            }))
        if resp.status_code != 200:
            self.error('Failed to update permission', resp)
        return resp.json()

    # User Endpoints

    def get_users(self):
        self.log.info('Getting all users')
        resp = self.user_request(method='GET', url=self.base_url + self.USERS)
        if resp.status_code != 200:
            self.error('Failed to get all users', resp)
        return resp.json()

    def get_user(self, user_id):
        self.log.info('Getting a user with ' + user_id)
        resp = self.user_request(method='GET', url="{}{}/{}".format(self.base_url, self.USERS, user_id))
        if resp.status_code != 200:
            self.error('Failed to get a user with ' + user_id, resp)
        return resp.json()

    def update_user(self, user_id, localAccess=None, username=None, password=None, spaceName=None, description=None):
        self.log.info('Updating a user: ' + user_id)
        payload = {}
        if localAccess is not None:
            payload['localAccess'] = localAccess
        if username is not None:
            payload['username'] = username
        if password is not None:
            payload['password'] = password
        if spaceName is not None:
            payload['spaceName'] = spaceName
        if description is not None:
            payload['description'] = description
        return self._update_user(user_id, data=json.dumps(payload))

    def _update_user(self, user_id, data, headers=None):
        self.log.info('Update user by ID:{} with {}'.format(user_id, data))
        resp = self.user_request(
            method='PATCH', url="{}{}/{}".format(self.base_url, self.USERS, user_id), data=data, headers=headers)
        if resp.status_code != 200:
            self.error('Failed to update user', response=resp)
        if 'password' in data:  # idle 1 sec for NSA-856
            time.sleep(1)
        return resp.json()

    def get_space_perms_for_user(self, user_id):
        self.log.info('Getting a space permission with ' + user_id)
        resp = self.user_request(method='GET', url="{}{}/{}/permissions".format(self.base_url, self.USERS, user_id))
        if resp.status_code != 200:
            self.error('Failed to get space permission with ' + user_id, resp)
        return resp.json()

    def enable_local_access(self, username=None, password=None):
        self.log.info('Enabling local access to current user')
        if not self.user_id:
            raise AssertionError('No user ID, please call this method after login')
        if username is None:
            username = self.local_name
        if password is None:
            password = self.local_password
        self.update_user(user_id=self.user_id, localAccess=True, username=username, password=password)

    def disable_local_access(self, keep_username=False, keep_password=False):
        self.log.info('Disabling local access to current user')
        if not self.user_id:
            raise AssertionError('No user ID, please call this method after login')
        input = {'user_id': self.user_id, 'localAccess': False, 'username': '', 'password': ''}
        if keep_username:
            input.pop('username')
        if keep_password:
            input.pop('password')
        self.update_user(**input)

    # Device Endpoints

    def get_device(self):
        self.log.info('Getting device information')
        resp = self.unauth_json_request(method='GET', url=self.base_url + self.DEVICE)
        if resp.status_code != 200:
            self.error('Failed to get device information')
        return resp.json()

    # Network Endpoints

    def get_network_connection(self):
        self.log.info('Getting network connection')
        resp = self.user_request(method='GET', url=self.base_url + self.NETWORK + '/internet')
        if resp.status_code != 200:
            self.error('Failed to get network connection')
        return resp.json()

    # Storage Endpoints

    def get_volumes(self):
        self.log.info('Getting volumes')
        resp = self.user_request(method='GET', url=self.base_url + self.STORAGE + '/volumes')
        if resp.status_code != 200:
            self.error('Failed to get volumes')
        return resp.json()

    def get_drives_info(self):
        self.log.info('Getting drives info')
        resp = self.user_request(method='GET', url=self.base_url + self.STORAGE + '/drives/info')
        if resp.status_code != 200:
            self.error('Failed to get drives info')
        return resp.json()

    # Validation Endpoints

    def get_validation_info(self):
        self.log.info('Getting validation info')
        resp = self.user_request(method='GET', url=self.base_url + self.VALIDATION)
        if resp.status_code != 200:
            self.error('Failed to get validation info', response=resp)
        return resp.json()

    # System Endpoints

    def init_system_test(self):
        self.log.info('Initiate a new system test')
        resp = self.user_request(method='POST', url=self.base_url + self.SYSTEM + '/test')
        if resp.status_code != 200:
            self.error('Failed to init system test')

    def get_system_test(self):
        self.log.info('Getting system test')
        resp = self.user_request(method='GET', url=self.base_url + self.SYSTEM + '/test')
        if resp.status_code != 200:
            self.error('Failed to get system test')
        return resp.json()

    def get_system_process(self):
        self.log.info('Getting system process')
        resp = self.user_request(method='GET', url=self.base_url + self.SYSTEM + '/status/process')
        if resp.status_code != 200:
            self.error('Failed to get system process')
        return resp.json()

    def get_system_status(self):
        self.log.info('Getting system status')
        resp = self.user_request(method='GET', url=self.base_url + self.SYSTEM + '/status')
        if resp.status_code != 200: # may got 50X status while disk is sleeping
            self.error('Failed to get system status')
        return resp.json()

    def write_client_logs(self, level, message, private=None):
        payload = {}
        if level is not None: # "debug", "error" or "info"
            payload['level'] = level
        if private is not None: # boolean
            payload['private'] = private
        if message is not None:
            payload['message'] = message
        self._write_client_logs(data=json.dumps(payload))

    def _write_client_logs(self, data, headers=None):
        self.log.info('Writing client logs with {}'.format(data))
        resp = self.user_request(
            method='POST', url=self.base_url + self.SYSTEM + '/clientLogs', data=data, headers=headers)
        if resp.status_code != 200:
            self.error('Failed to write client logs', response=resp)

    def system_reset(self, rtype, raid_mode=None):
        payload = {}
        if rtype is not None:  # "eraseSettings", "eraseAllData"
            payload['type'] = rtype
        if raid_mode is not None:  # "default", "jbod", "span", "mirror"
            payload['raidMode'] = raid_mode
        self._system_reset(data=json.dumps(payload), no_fail_retry=True)

    def _system_reset(self, data, headers=None, no_fail_retry=False):
        self.log.info('Initiating system reset with {}'.format(data))
        try:
            resp = self.user_request(
                method='POST', url=self.base_url + self.SYSTEM + '/reset', data=data, headers=headers,
                retry_times=0 if no_fail_retry else None
            )
            if resp.status_code != 202:
                self.error('Failed to initiate system reset', response=resp)
        except requests.exceptions.ConnectionError as e:
            if 'Connection aborted.' not in str(e):
                self.error('Failed to initiate system reset', response=resp)
            self.log.info('Expected response from the reset call')


@common_utils.logger()
class UnAuthCallLimiter(object):

    def __init__(self):
        self.enabled = True
        self.max_calls = 10  # the limit is 20, but take 10 for buffer in case of other calls without auth.
        self.per_secs = 60
        self.start_time = None
        self.current_count = 0

    def increase_count(self):
        if not self.start_time or time.time() > self.start_time + self.per_secs:
            #  reset values if not init yet or timeout
            self.start_time = time.time()
            self.current_count = 0
        self.current_count += 1
        return self.current_count

    def check_and_delay(self):
        try:
            if not self.enabled:
                return
            if self.increase_count() > self.max_calls:
                delay_secs = abs(self.per_secs - (time.time() - self.start_time))
                self.log.info('Delay {} secs for unauthorized call limitation'.format(delay_secs))
                time.sleep(delay_secs)
        except Exception as e:
            self.log.warning('Got an error: {}'.format(e))


if __name__ == '__main__':
    from platform_libraries.restAPI import RestAPI
    import logging
    ip = '10.200.140.96'
    rest_client = RestAPI(uut_ip=ip + ":8001", env="qa1", username="wdcautotw+qawdc.rnd.media@gmail.com",
                password="Auto1234", init_session=False, stream_log_level=logging.DEBUG)
    rest_client.update_device_id()
    nasadmin_client = NasAdminClient(ip, rest_client=rest_client)

    owner = nasadmin_client.get_owner()
    
    nasadmin_client.log.info('Creating local spaces')
    nasadmin_client.create_space(name="space1", allUsers=True, localPublic=False)
    nasadmin_client.create_space(name="space2", allUsers=False, localPublic=True)
    nasadmin_client.create_space(name="space3", allUsers=False, localPublic=False)
    for space in nasadmin_client.get_spaces():
        if space['userID'] or space['systemName']:
            continue
        nasadmin_client.log.info(space)
        nasadmin_client.get_space(space['id'])
        nasadmin_client.delete_spaces(space['id'])
    nasadmin_client.log.info(nasadmin_client.get_spaces())

    nasadmin_client.log.info('Creating local spaces for different usage')
    space = nasadmin_client.create_space(name="space_private", allUsers=False, localPublic=False)
    nasadmin_client.update_space(space['id'], name="new")
    nasadmin_client.log.info(nasadmin_client.get_space(space['id']))
    nasadmin_client.update_space(space['id'], allUsers=True)
    nasadmin_client.log.info(nasadmin_client.get_space(space['id']))
    nasadmin_client.update_space(space['id'], localPublic=True)
    nasadmin_client.log.info(nasadmin_client.get_space(space['id']))
    nasadmin_client.update_space(space['id'], allUsers=False, localPublic=False)
    nasadmin_client.log.info(nasadmin_client.get_space(space['id']))

    nasadmin_client.log.info('Enabling local access for owner and change info')
    nasadmin_client.update_user(owner['id'], localAccess=True, username='owner', password='password',
        spaceName='OwnerSpace', description='Owner User')
    nasadmin_client.log.info(nasadmin_client.get_user(owner['id']))

    nasadmin_client.log.info(nasadmin_client.get_space_perms_for_user(owner['id']))
    nasadmin_client.log.info(nasadmin_client.get_user_perms_for_space(space['id']))

    nasadmin_client.log.info('Changing perms for the private local space')
    nasadmin_client.update_space_perm(space['id'], owner['id'], 'read')
    nasadmin_client.log.info(nasadmin_client.get_user_perms_for_space(space['id']))
    nasadmin_client.update_space_perm(space['id'], owner['id'], 'readWrite')
    nasadmin_client.log.info(nasadmin_client.get_user_perms_for_space(space['id']))
    nasadmin_client.update_space_perm(space['id'], owner['id'], 'noAccess')
    nasadmin_client.log.info(nasadmin_client.get_user_perms_for_space(space['id']))

    nasadmin_client.log.info('Enabling time machine backup for owner user to the private local space')
    nasadmin_client.update_space(space['id'], timeMachine=True)
    
    nasadmin_client.delete_spaces(space['id'])
