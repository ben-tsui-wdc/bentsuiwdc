# @ Author: Kurt Jensen <kurt.jensen@wdc.com>, Ben Tsui <ben.tsui@wdc.com>, Estvan Huang <Estvan.Huangi@wdc.com>

# std modules
import json
import os
import sys
import time
import urllib
from datetime import datetime
from itertools import count
from uuid import uuid4

# 3rd party modules
import requests
from pprint import pformat

# platform modules
import common_utils
from constants import GlobalConfigService as GCS
from platform_libraries.cloud_api import CloudAPI
from platform_libraries.cloud_environment import RestEnvironment
from platform_libraries.http_client import HTTPRequester
from platform_libraries.constants import Kamino 
from platform_libraries.pyutils import partial_read_in_chunks, read_in_chunks, retry


class ItemParser(object):

    @staticmethod
    def only_id(item):
        return item.get('id')

    @staticmethod
    def only_name(item):
        return item.get('name')

    @staticmethod
    def id_and_name(item):
        return {'id': item.get('id'), 'name': item.get('name')}


@common_utils.logger()
class RestAPI(HTTPRequester):

    _ids = count(0)
    # Owner Information Area 
    _owner_id_token = None
    owner_refresh_token = None
    owner_token_time = None
    owner_username = None
    owner_password = None

    @property
    def owner_access_token(self):
        def do_refresh_owner_token():
            response = self._do_refresh_token(RestAPI.owner_refresh_token)
            self.log.debug('Refresh Owner ID token complete')
            RestAPI._owner_id_token = response['id_token']
            RestAPI.owner_token_time = datetime.now()
            self.log.debug('Refreshed Owner ID token: {}'.format(RestAPI._owner_id_token))
            return RestAPI._owner_id_token

        self.log.debug('Getting ID token of owner: {}'.format(RestAPI.owner_username))
        if RestAPI.owner_token_time:
            return self.get_existing_id_token(
                RestAPI.owner_token_time, RestAPI._owner_id_token, refresh_token_func=do_refresh_owner_token)

        # Get a new token.
        response = self._get_id_token(RestAPI.owner_username, RestAPI.owner_password)
        self.log.info('Get new Owner ID token complete')
        RestAPI._owner_id_token = response['id_token']
        #RestAPI.owner_access_token = response['access_token']
        RestAPI.owner_refresh_token = response['refresh_token']
        self.log.debug('Owner ID token: {}'.format(RestAPI._owner_id_token))
        #self.log.debug('Owner Access token: {}'.format(RestAPI.owner_access_token))
        self.log.debug('Owner Refresh token: {}'.format(RestAPI.owner_refresh_token))
        # If first user attached to device set owner access token
        RestAPI.owner_token_time = datetime.now()
        return RestAPI._owner_id_token

    @owner_access_token.setter
    def owner_access_token(self, value):
        self._owner_id_token = value


    def __init__(self, uut_ip=None, port=None, env=None, username=None, password=None, id_token=None, root_log='KAT', log_name=None, debug=False,
            debug_request=True, debug_response=True, retry_attach_user=True, init_session=True, env_version=None, client_settings=None,
            stream_log_level=None, url_prefix=None, client_id=None, env_inst=None, cloud_inst=None):
        self.init_logger(root_log=root_log, log_name=log_name, stream_log_level=stream_log_level)
        super(RestAPI, self).__init__(log_inst=self.log, buildin_debug=debug, debug_request=debug_request, debug_response=debug_response)
        self.id = self._ids.next()
        self.uut_ip = uut_ip
        self.port = port
        self.update_url_prefix(url_prefix=url_prefix)
        self.guid = None
        self.env = env
        self.environment = env_inst if env_inst else RestEnvironment(env, client_id=client_id, http_requester=self)
        self.username = username
        self.password = password
        self.id_token = id_token
        self.access_token = None
        self.refresh_token = None
        self.id_token_time = None
        # Auth0 token expired time is 86400 secs (24 hours)
        # set the expired time to 23 hours and try to refresh token before it's expired
        self.id_token_expired_time = 23 * 60 * 60
        self.device_id = None
        self.retry_attach_user = retry_attach_user
        self.cloud = cloud_inst if cloud_inst else CloudAPI(env=env, log_inst=self.log)
        self.cache_user_data = {}
        if self.id == 0:
            if not RestAPI.owner_username and self.username:
                self.log.debug('Set RestAPI.owner_username: {}'.format(self.username))
                RestAPI.owner_username = self.username
            if not RestAPI.owner_password and self.password:
                self.log.debug('Set RestAPI.owner_password: {}'.format(self.password))
                RestAPI.owner_password = self.password
        # Need to update servie url before executing ANY REST call.
        self.environment.update_service_urls(client_settings, env_version)
        self.update_device_ip()
        if init_session: self.init_session(env_version=env_version, client_settings=client_settings)


    def update_device_id(self, env_version=None, client_settings=None):
        if not client_settings:
            client_settings = {}
        if 'device_id' not in client_settings and self.url_prefix:
            client_settings['device_id'] = retry(func=self.get_local_code_and_security_code,
                retry_lambda=lambda x: not x[0], delay=10, max_retry=60, log=self.log.warning, without_auth=True)[0]

    def init_session(self, env_version=None, client_settings=None, with_cloud_connected=True):
        """
            Create user and get user token, then attach user to device. 
            :param client_settings: A set of parameters of get_configuration() in dict.
            :param with_cloud_connected: Wait for device is connect to cloud service.
        """
        self.init_variables()
        get_user = self.cloud.get_user_info_from_cloud(email=self.username)
        if not get_user:
            self.create_user(self.username, self.password)
        else:
            self.log.debug('User: {0} exist, user info:{1}'.format(self.username, get_user))
        self.update_device_id(env_version, client_settings)
        # Wait for connection after URL updated.
        if with_cloud_connected: self.wait_until_cloud_connected(as_admin=True)
        if self.retry_attach_user: # retry 20 times.
            retry(func=self.attach_user_to_device, delay=10, max_retry=20, log=self.log.warning)
        else:
            self.attach_user_to_device()

    def set_adb_client(self, adb_client):
        self.log.debug('Set adb_client: {} into REST API user'.format(adb_client))
        self._adb_client = adb_client

    def has_adb_client(self):
        return hasattr(self, '_adb_client') and self._adb_client

    def set_ssh_client(self, ssh_client):
        self.log.debug('Set ssh_client: {} into REST API user'.format(ssh_client))
        self._ssh_client = ssh_client

    def has_ssh_client(self):
        return hasattr(self, '_ssh_client') and self._ssh_client

    def is_owner(self):
        return self.username == self.owner_username

    def init_variables(self, id_token=None, access_token=None, refresh_token=None, id_token_time=None, device_id=None):
        self.id_token = id_token
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.id_token_time = id_token_time
        self.device_id = device_id

    def update_url_prefix(self, url_prefix=None):
        if url_prefix:
            self.url_prefix = url_prefix
        else:
            self.log.debug('latest self.uut_ip: {}'.format(self.uut_ip))
            self.log.debug('latest self.port: {}'.format(self.port))
            self.url_prefix = 'http://{}'.format(self.uut_ip) if self.uut_ip else None
            if self.url_prefix and self.port and int(self.port) != 80:
                self.url_prefix = '{}:{}'.format(self.url_prefix, self.port)

    def update_device_ip(self, ip=None, port=None):
        '''
        device_ip: device ip/url, which is WITHOUT port
        port: restsdk port
        url_prefix: device ip/url + port
        '''
        if ip:
            self.log.warning('Current IP: {} now change to IP: {}...'.format(self.uut_ip, ip))
            self.uut_ip = ip
        if port:
            self.log.warning("The uut_restsdk_port ({}) is specified by manual.".format(port))
            self.port = port
        elif self.port:
            self.log.debug("No change port to RestSDK")
        else:
            self.update_url_prefix('http://{}'.format(self.uut_ip))  # update by IP for detect port
            self.port = self.detect_restsdk_port()
        self.update_url_prefix()

    def detect_restsdk_port(self):
        if self.has_ssh_client():
            self.log.warning('Acquire restsdk_port by ssh_client...') 
            return self._ssh_client.get_restsdk_httpPort()
        else:
            self.log.info("The 'RestAPI' object has no attribute 'ssh_client' to acquire restsdk_port. Try different port to see if it works.")
            original_url_prefix = self.url_prefix
            try:
                for port in ['80', '8001']:
                    self.url_prefix = original_url_prefix  + ':{}'.format(port)  # This self.url_prefix here is temporary.
                    self.log.info('Try device url port: {} ...'.format(self.url_prefix))
                    if self.can_access_restsdk():
                        self.log.info('Access RestSDK successfully')
                        return port
                self.log.warning("Cannot find usable restsdk port, use default port '80'.")
                return 80
            finally:
                self.url_prefix = original_url_prefix

    def get_current_restsdk_port(self):
        domain = self.url_prefix.split('//')[-1].split('/')[0]
        if ':' in domain:
            return domain.split(':')[-1]
        return 80

    def create_user(self, username, password, first_name='automation', last_name='tw'):
        """
            Create a user on the cloud

            :param username: The name of new user
            :param password: The password of new user
        """
        self.log.info('Creating user:{}'.format(username))

        response = self.json_request(
            method='POST',
            url='{}/authservice/v1/auth0'.format(self.environment.get_auth_service_sign_up()),
            data=json.dumps({
                'client_id': self.environment.get_client_id(),
                'email': username,
                'password': password,
                'connection': 'Username-Password-Authentication',
                'user_metadata': {'first_name': first_name, 'last_name': last_name}
            })
        )

        if response.status_code == 200:
            self.log.info('User: {} is created successfully'.format(username))
        elif response.status_code == 400:
            response = response.json()
            # Add error_description condition for dev1 new auth changes
            if response.get('code') == 'user_exists' or response.get('error_description') == 'Username already exists':
                self.log.info('User: {} is already exist'.format(username))
            else:
                self.log.error(response)
                self.error('Failed to create user.')
        else:
            self.error('Failed to create user.', response)

    def delete_user(self, username=None, password=None):
        self.log.info('Deleting user: {}'.format(username if username else self.username))
        try: 
            if username:
                access_token = self._get_id_token(username, password)['id_token']
            else:
                access_token = self.get_id_token()
        except requests.exceptions.HTTPError as e:
            if getattr(e, 'response', None) is not None and 'invalid_user_password' in e.response.content:
                self.log.info('User seems not exitst, please check.')
                return
            raise
        response = self.json_request(
            method='DELETE',
            url='{}/authservice/v1/auth0/user/{}/erase'.format(
                self.environment.get_auth_service_sign_up(), self.get_user_id(token=access_token, escape=False)),
            headers={
                'Authorization': 'Bearer {0}'.format(access_token)
            }
        )
        if response.status_code == 200:
            self.log.info('Delete user successfully')
        else:
            self.error('Failed to delete user.', response)
        
    def _get_id_token(self, username, password):
        """
            Get id token of the user attached to device

            :return: ID token in String format. ex. '3931eb3d-7ee2-4257-988f-3aeb7f6d520d'
        """
        self.log.debug('ID token not exist, trying to get a new token')
        response = self.json_request( # Not a json request.
            method='POST',
            url='{}/oauth/ro'.format(self.environment.get_auth_service()),
            #headers={'Content-Type': 'application/x-www-form-urlencoded'}, # Overwrite header.
            data=json.dumps({
                'client_id': self.environment.get_client_id(),
                'username': username,
                'password': password,
                'connection': 'Username-Password-Authentication',
                'device': '1234',
                'scope': 'openid offline_access',
                'grant_type': 'password'
            })
        )

        if response.status_code != 200:
            self.error('Failed to get ID token.', response)
        return response.json()

    def get_existing_id_token(self, id_token_time, existing_id_token, refresh_token_func=None):
        if not self.reduce_log: self.log.debug('ID token already exist, checking the expire time')
        current_time = datetime.now()
        time_passed = (current_time - id_token_time).seconds
        # Token isn't timeout.
        if time_passed < self.id_token_expired_time:
            if not self.reduce_log: 
                self.log.debug('Use existed ID token, it will be expired in {} seconds'.
                    format(self.id_token_expired_time - time_passed))
                self.log.debug('ID token: {}'.format(existing_id_token))
            return existing_id_token
        # Refresh token.
        self.log.info('ID token expired, refresh the ID token')
        return refresh_token_func() if refresh_token_func else self.do_refresh_token()

    def get_id_token(self):
        if not self.reduce_log: self.log.debug('Getting ID token of user: {}'.format(self.username))
        if self.id_token_time:
            return self.get_existing_id_token(self.id_token_time, self.id_token)

        # Get a new token.
        response = self._get_id_token(self.username, self.password)
        self.log.info('Get new ID token complete')
        self.id_token = response['id_token']
        self.access_token = response['access_token']
        self.refresh_token = response['refresh_token']
        self.id_token_expired_time = int(response['expires_in']) - 600  # The unit is second. Minus 600 seconds is for buffer.
        self.log.debug('ID token: {}'.format(self.id_token))
        self.log.debug('Access token: {}'.format(self.access_token))
        self.log.debug('Refresh token: {}'.format(self.refresh_token))
        self.log.debug('ID token expired time: {}     (which is "expires_in" minus 600 seoncds for buffer.)'.format(self.id_token_expired_time))
        # If first user attached to device set owner access token
        if self.id == 0:
            self.owner_access_token = self.id_token
        self.id_token_time = datetime.now()
        return self.id_token

    def get_fresh_id_token(self):
        self.id_token_time = None
        return self.get_id_token()

    def get_access_token(self):
        """
            Get access token of the user attached to device

            :return: Access token in String format. ex. '3931eb3d-7ee2-4257-988f-3aeb7f6d520d'
        """

        # Access token will not be expired now, and we'll get and save it while creating restAPI instance,
        # so just return it. Update date: 2016/12/14
        return self.access_token

    def _do_refresh_token(self, refresh_token):
        """
            Use refresh token as parameter to get the new ID token

            :return: Access token in String format. ex. '3931eb3d-7ee2-4257-988f-3aeb7f6d520d'
        """
        self.log.debug('Refreshing the ID token')
        response = self.json_request(
            method='POST',
            url='{}/delegation'.format(self.environment.get_auth_service()),
            data=json.dumps({'client_id': self.environment.get_client_id(),
                'target': '',
                'refresh_token': refresh_token,
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'scope': 'openid',
                'api_type': 'app'
            })
        )
        if response.status_code != 200:
            self.error('Failed to get ID token.', response)
        return response.json()

    def do_refresh_token(self):
        """
            Use refresh token as parameter to get the new ID token

            :return: Access token in String format. ex. '3931eb3d-7ee2-4257-988f-3aeb7f6d520d'
        """
        response = self._do_refresh_token(self.refresh_token)
        self.log.debug('Refresh ID token complete')
        self.id_token = response['id_token']
        self.id_token_time = datetime.now()
        self.log.debug('Refreshed ID token: {}'.format(self.id_token))
        return self.id_token

    def get_user_id(self, token=None, escape=False):
        """
            Get the user id by access token

            :return: A user id in String format. ex. 'auth0|0456808ec30156dbcafdb963bb'
        """
        self.log.debug('Getting User ID')
        resp = self.get_cloud_user(token)
        user_id = resp['user_id']
        self.log.debug('User ID: {}'.format(user_id))
        if escape:
            return user_id.replace('auth0|', 'auth0\|')
        return user_id

    def get_cloud_user(self, token=None, cache=True):
        """ Get user information with the given user token from Auth0 server. """
        self.log.debug('Getting Cloud User')
        if not token:
            token = self.get_id_token()

        # Get from cache user data
        if cache and token in self.cache_user_data:
            return self.cache_user_data[token]

        response = self.json_request(
            method='GET',
            url='{}/userinfo'.format(self.environment.get_auth_service()),
            headers={'Authorization': 'Bearer {0}'.format(token)}
        )
        if response.status_code != 200:
            self.error('Failed to execute get user with token from cloud server.', response)

        # Cache user data
        self.cache_user_data[token] = response.json()
        return self.cache_user_data[token]

    def get_cloud_user_old(self, token=None, cache=True):
        """ Get user information with the given user token from Auth0 server. """
        self.log.debug('Getting Cloud User')
        if not token:
            token = self.get_id_token()

        # Get from cache user data
        if cache and token in self.cache_user_data:
            return self.cache_user_data[token]

        response = self.json_request(
            method='POST',
            url='{}/tokeninfo'.format(self.environment.get_auth_service()),
            data=json.dumps({'id_token': token})
        )
        if response.status_code != 200:
            self.error('Failed to execute get user with token from cloud server.', response)

        # Cache user data
        self.cache_user_data[token] = response.json()
        return self.cache_user_data[token]

    def get_data_id_list(self, type='folder', parent_id='root', data_name=None, page_token='', timeout=120):
        """
            API "Search Files By Parent", the document link:
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#search-files-by-parents

            Get and return all the folder/file ID under a user folder

            :param type: Input 'folder' or 'file' to get the id list. Default is 'folder'.
            :param parent_id: The parent ID to search within.
                              A not present value will retrieve the root node the matches the name.
                              The value of root retrieves the file in the user's root that matches the name.
            :param data_name: If specified, only the ID of specified data will be returned in String format,
                              otherwise all the folder/file IDs will be returned in key-value pairs.
            :param page_token: Specify which page to search, there's 1000 data for each page
            :return: Return an ID in String format(if data_name is not None),
                     or a dict with key=folder/file name, val=folder/file id, and pageToken for 1000+ files.
                     ex. {'folder1': '1wVgTYcKeH43kA6ED9c2vzFaBdWGAr55BWqWsBLI'},
                         'T3VXTjlWUGowVWE3ZFcySEpKSl8yTWYtMmg1TG4yc3Q3blVqSW1KRQ'
        """
        self.log.debug('Getting data ID')

        result = self.bearer_request(
            method='GET',
            url='{}/sdk/v2/filesSearch/parents'.format(self.url_prefix),
            params={
                'limit': 1000,
                'pageToken': page_token,
                'ids': parent_id
            },
            timeout=timeout
        )

        if result.status_code != 200:
            self.error('Get folder ID failed, status code:{0}, error log:{1}'.
                       format(result.status_code, result.content))
        else:
            if data_name:
                data_list = ''
            else:
                data_list = dict()

            data_info = result.json()
            if 'files' in data_info:
                for temp_dict in data_info['files']:
                    if all(k in temp_dict for k in ('name', 'id', 'mimeType')):
                        try:
                            if data_name:
                                if str(temp_dict['name']) == str(data_name):
                                    if type == 'folder' and str(temp_dict['mimeType']) != 'application/x.wd.dir':
                                        continue
                                    else:
                                        data_list = str(temp_dict['id'])
                                        break
                                else:
                                    continue
                            else:
                                if type == 'folder' and str(temp_dict['mimeType']) != 'application/x.wd.dir':
                                    continue
                                else:
                                    data_list[str(temp_dict['name'])] = str(temp_dict['id'])
                        except Exception as err:
                            self.log.warning(err)


            if not data_list:
                if data_name:
                    self.error('Cannot find specified {0}: {1}'.format(type, data_name))
                else:
                    self.error('There are no {} exist'.format(type))

            if data_name:
                return data_list
            else:
                page_token = ''
                if 'pageToken' in data_info:
                    page_token = data_info['pageToken']

                return data_list, page_token

    def search_file_by_parent(self, parent_id='root', page_token=None, limit=1000, fields=None, timeout=120):
        """
            Get and return all the folder/file ID under a user folder.

            :param limit: Specify maximum number of data to return.
            Other parameters please refer to get_data_id_list().
            :return: Return a list of dict data and next page token. Example:
                    [{'cTime': '2017-02-22T08:29:30.918Z',
                                'childCount': 2302,
                                'eTag': '"Ag"',
                                'hidden': 'none',
                                'id': 'pCmfhKzazB3Rp5OEnYz1KW7qvMoJU5LTRHLd1V6O',
                                'mTime': '2017-02-22T08:29:30.918Z',
                                'mimeType': 'application/x.wd.dir',
                                'name': 'Transcend',
                                'parentID': 'IspbjrB0WusGNpncgZzHb0MCjOPW8Wq_0L9THEY5',
                                'privatelyShared': False,
                                'publiclyShared': False,
                                'storageType': 'local'}],
                    'S3pTY0ljVlBMejFCRldrMG5BWmNXelVQQzZPdy1SUUc5eDNXdjVTQw'
        """
        self.log.debug('Searching file by parent_id: {}'.format(parent_id))

        result = self.bearer_request(
            method='GET',
            url='{}/sdk/v2/filesSearch/parents'.format(self.url_prefix),
            params={
                'limit': limit,
                'pageToken': page_token,
                'ids': parent_id,
                'fields': fields
            },
            timeout=timeout
        )

        if result.status_code != 200:
            self.error("Search file by parent failed, status code:{0}, error log:{1}".
                format(result.status_code, result.content))
        json_result = result.json()
        return json_result.get('files', []), json_result.get('pageToken', '')

    def wait_for_restsdk_works(self, timeout=60*5, wait_more_seconds=True):
        self.log.debug('Wait for REST SDK works...')
        start_time = time.time()
        while (timeout > time.time() - start_time):
            if not self.is_restsdk_working():
                self.log.info('REST SDK is not ready yet...')
                time.sleep(5)
            else:
                self.log.info('REST SDK is ready')
                if wait_more_seconds:
                    self.log.info('Wait 20 sec to let device ready')
                    time.sleep(20)
                return True
        self.log.info("REST SDK does't work")
        return False

    def can_access_restsdk(self):
        try:
            response = self.get_device(without_auth=True)
            if response.status_code != 200:
                return False
            if 'ready' not in response.json():
                return False
        except Exception, e:
            return False
        return True

    def is_restsdk_working(self):
        try:
            response = self.get_device(without_auth=True)
            return response.json().get('ready')
        except Exception, e:
            #self.log.exception(e)
            return False
        if response.status_code != 200:
            return False
        return True

    def get_device(self, without_auth=False, fields=None):
        # Current RSDK design: Need user token to get device info. https://csbu.atlassian.net/browse/RSDK-95
        # So we ignore paramater "without_auth" for now.
        requester = self.bearer_request
        return requester(
            method='GET',
            url="{0}/sdk/v1/device{1}".format(
                self.url_prefix,
                '?fields={}'.format(fields) if fields else ''
            )
        )

    def get_local_code_and_security_code(self, without_auth=False):
        """
            Get local code and security code

            :return: Device ID, Security Code, Local Code in String format.
                     ex. '694e6d3f-2757-4c08-8a03-968634df9310', 'SI98FT20',
                     '9U4N7I0LoCTZoI/nSrZt6eWOp+lOl6WsLGdpATniKxxdCuc4UtdnVTReHkl++4tX08jVmcOAFIT2hSiTv4ZaAA=='
        """
        self.log.debug('Getting local code and security code')
        r = None
        result = self.get_device(without_auth)  # Get device info by REST call over uut_ip
        if result.status_code == 200:
            self.log.debug('Get local code and security code successfully')
            r = result.json()
        else:
            if self.has_adb_client():  # Get device info by REST call over adb
                temp = self._adb_client.executeShellCommand('curl localhost/sdk/v1/device')[0]
                r = json.loads(temp)
            # elif  # Need to implement "Get device info by serial client"
        if r:
            self.log.info('Response: \n{}'.format(pformat(r)))
            device_id = r.get('id')
            security_code = r.get('securityCode')
            local_code = r.get('localCode')
            time = r.get('boot').get('time')
            self.log.info('Device ID: {}'.format(device_id))
            self.log.info('Security code: {}'.format(security_code))
            self.log.info('Local code: {}'.format(local_code))
            self.log.info('Data Time: {}'.format(time))
            if not self.device_id:
                self.device_id = device_id

            return device_id, security_code, local_code, time
        else:
            self.error('Failed to get local code and security code, status code: {0}, error message: {1}'.
                       format(result.status_code, result.content))

    def get_device_info(self, as_owner=True, as_admin=False, feature_version='v1'):
        """
            Get the Device based on deviceId

            Returns: deviceId, modelId, mac, name, cloudConnected in String format.
        """
        self.log.debug('Getting Device Info')
        device_id = self.get_local_code_and_security_code(without_auth=True)[0]

        if as_admin:
            request_inst = self.admin_bearer_request
        elif as_owner: # For the user who is not owner, he/she may cannot get information because not approved.
            request_inst = self.owner_bearer_request
        else:
            request_inst = self.bearer_request

        response = request_inst(
            method='GET',
            url="{0}/device/{1}/device/{2}".format(self.environment.get_device_service(), feature_version, device_id),
        )
        if response.status_code == 200:
            self.log.info('Get device info successfully')
            return response.json().get('data')
        else:
            self.error('Failed to get device info', response)

    def wait_until_cloud_connected(self, timeout=60*5, as_admin=False):

        if self.environment.get_env_name() == 'prod': # Workaround solution for admin token cannot be used on prod
            self.log.warning('Env is {}, skipped "wait_until_cloud_connected" check ...'.format(self.environment.get_env_name()))
            return

        self.log.info('Wait until device connected cloud in {} sec...'.format(timeout))
        start_time = current_time = time.time()
        ping_result = None
        while current_time <= start_time+timeout:
            try:
                data = self.get_device_info(as_admin=as_admin)
                flag = data.get('cloudConnected')
                self.log.info('=> cloudConnected: {}'.format(flag))
                if flag:
                    return
            except requests.exceptions.HTTPError as e:
                pass
            current_time = time.time()
            if self.has_adb_client():
                try:
                    ping_result = self._adb_client.executeShellCommand('busybox ping www.google.com -c 3 || echo ping test finished')[0]
                except Exception as e:
                    self.log.info("This is for debug. Don't raise Exception.")
            self.log.warning('wait 15 sec, and retry again...')
            time.sleep(15)
        if self.has_adb_client():
            self.log.warning('If cloudConnected=False\nTry to {}'.format(ping_result))
        raise RuntimeError("Device doesn't connect to cloud after {} sec...".format(timeout))

    def attach_user_to_device(self):
        """
            Attach user with SecurityCode
        """
        self.log.debug('Attaching user to device')
        # if not owner
        if self.id > 0:
            invitation_id = self.invite_users_to_attach_to_device(self.username).get('invitationId')
            self.attach_user_to_device_with_code(invitation_id=invitation_id)
        else:
            self._attach_user_to_device_with_localcode()

    def wait_for_owner_permissions(self, delay=30, max_retry=10, permissions=None):
        self.log.debug('Wait for owner permissions...')
        if not permissions:
            permissions = ["GetUsers", "GetDevice", "AppManagement", "WriteDevice", "CreateFileGroup", "CreateRootFile"]

        def retry_func():
            resp = self.get_user_permission(user_id=self.get_user_id(token=self.owner_access_token))
            owner_perms = [item['value'] for item in resp['devicePerms']]
            self.log.info('Owner permission: {}'.format(owner_perms))
            intersections = set(permissions).intersection(owner_perms)
            if len(intersections) != len(permissions):
                return False
            return True

        retry(
            func=retry_func,
            excepts=(Exception), retry_lambda=lambda x: not x, delay=delay, max_retry=max_retry, log=self.log.warning
        )

    def attach_user_to_device_with_code(self, security_code=None, invitation_id=None):
        user_id = self.get_user_id()
        if invitation_id:
            payload = {
                'invitationId': invitation_id
            }
        elif security_code:
            payload = {
                'securityCode': security_code
            }
        else:
            device_id, security_code, local_code, time = self.get_local_code_and_security_code()
            payload = {
                'securityCode': security_code
            }
        self.log.debug('Attach device with {}'.format(payload))
        # Attach by security code
        result = self.bearer_request(
            method='POST',
            url='{0}/device/v2/user/{1}/device'.format(self.environment.get_device_service(), user_id),
            data=json.dumps(payload)
        )
        self.log.debug('Response: \n{}'.format(pformat(result.json())))

        if result.status_code == 200:
            if result.json().get('data').get('status') == 'PENDING_APPROVAL' and self.id > 0:
                self.log.info('User: {} is waiting for approval.'.format(self.username))
            else:
                self.log.info('User: {} is attached to device successfully'.format(self.username))
            self.guid = result.json().get('data').get('guid')
            return result.json().get('data')
        elif result.status_code == 409 and result.json().get('error').get('message') == 'User already attached to device':
            self.log.info('User was already attached to device: {0}'.format(self.username))
        else:
            self.error('Attach user to device failed, status code: {0}, error message: {1}'.
                       format(result.status_code, result.content))

    def _attach_user_to_device_with_localcode(self):
        user_id = self.get_user_id()

        # Retry for network issue.
        device_id, security_code, local_code, time = retry(func=self.get_local_code_and_security_code,
            retry_lambda=lambda x: not x[2], delay=10, max_retry=180, log=self.log.warning)
        # Attach by local code
        response = self.bearer_request(
            method='POST',
            url='{0}/device/v2/device/{1}/user?forceOwner=true'.format(self.environment.get_device_service(), device_id),
            data=json.dumps({
                "localCode": local_code,
                "userId": user_id
            })
        )
        response_dict = response.json()
        self.log.debug('Response: \n{}'.format(pformat(response_dict)))

        if response.status_code == 200:
            if response_dict.get('data').get('status') == 'PENDING_APPROVAL' and self.id > 0:
                self.log.info('User: {} is waiting for approval.'.format(self.username))
            elif self.is_owner() and not response_dict.get('data').get('adminFlag'):
                self.error('The adminFlag of device owner is not True.', response)
            elif not self.is_owner() and response_dict.get('data').get('adminFlag'):
                self.error('The adminFlag of user is not False.', response)
            else:
                self.log.info('User: {} is attached to device successfully'.format(self.username))
            self.guid = response_dict.get('data').get('guid')
            return response_dict.get('data')
        elif response.status_code == 409 and response_dict.get('error').get('message') == 'Owner is already attached to device':
            self.log.info('Owner was already attached to device: {0}. Maybe it\'s not the same user account?'.format(self.username))
        else:
            self.error('Attach user to device failed.', response)

    def detach_user_from_device(self, user_id=None, id_token=None):
        '''
        According to the cloud REST API document
        http://build-docs.wdmv.wdc.com/docs/cloud.html#delete-v1-device-deviceid-user-userid, 
        the rule is as follows:
        1. Owner can never be detached.
        2. If you are an owner, you can detach any user other than owner self.
        3. if you are a non-owner, you can only detach yourself.
        '''
        if not user_id:
            user_id = self.get_user_id()
        if not id_token:
            id_token = self.get_id_token()

        device_id, security_code, local_code, time = self.get_local_code_and_security_code()
        if self.id == 0: # Deatch device owner.
            url = '{0}/device/v1/device/{1}/user'.format(self.environment.get_device_service(), device_id)
        else:
            url = '{0}/device/v1/device/{1}/user/{2}'.format(self.environment.get_device_service(), device_id, user_id)
        response = self.bearer_request(method='DELETE', url=url)

        if response.status_code == 200 and response.json().get('data') == 'deleted':
            self.log.info('{} is detached from device successfully'.format(self.username))
        elif response.status_code == 401:
            self.error('{0} -> Token verification failed while detaching user because of unauthorization.'.format(self.username))
        elif response.status_code == 409:
            self.log.info('{0} was already detached from device: {0}'.format(self.username))
        else:
            self.error('Failed to detach {0} from device.'.format(self.username), response)
        return response.status_code

    def invite_users_to_attach_to_device(self, user_mail):
        """
            Send invitation for the secondary user to attach to the device
        """
        self.log.info('Sending the invitation to user {}...'.format(user_mail))
        device_id, security_code, local_code, time = self.get_local_code_and_security_code()

        url = '{0}/device/v1/device/{1}/invitation'.format(self.environment.get_device_service(), device_id)
        response = self.owner_bearer_request(
            method='POST',
            url=url,
            data = json.dumps({"emailList": [user_mail]})
        )
        if response.status_code == 200:
            resp = response.json()
            if resp: return resp.get('data').pop()
        else:
            self.error('Failed to send invitation, status code:{0}, error message: {1}'.
                format(response.status_code, response.content))

    def _owner_approve_attach(self):
        """
            Approve attached users with status "PENDING_APPROVAL"
        """
        self.log.info('Owner is approving the attach request...')
        access_token = self.owner_access_token

        url = '{0}/device/v2/device/attach/{1}'.format(self.environment.get_device_service(), self.guid)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {0}'.format(access_token)}
        data = {'status': 'APPROVED'}

        result = requests.post(url, headers=headers, data=json.dumps(data))
        if result.status_code == 200:
            self.log.info('User: {} is successfully attached to device'.format(self.username))
        elif result.status_code == 409:
            self.log.info('User is already approved, status code: {0}, error message: {1}'.
                          format(result.status_code, result.content))
        else:
            self.error('Failed to approve user, status code: {0}, error message: {1}'.
                       format(result.status_code, result.content))

    def _owner_approve_attach_by_status(self):
        self.log.info('Owner is approving the attach request...')
        self.get_id_token()
        user_id = self.get_user_id()
        device_id, security_code, local_code, time = self.get_local_code_and_security_code()
        response = self.owner_bearer_request(
            method='PUT',
            url='{0}/device/v1/device/{1}/user/{2}'.format(self.environment.get_device_service(), device_id, user_id),
            data=json.dumps({
                "status": "APPROVED"
            })
        )
        if response.status_code == 200:
            self.log.info('User: {} is successfully attached to device'.format(self.username))
        elif response.status_code == 409:
            self.log.info('User is already approved, status code: {0}, error message: {1}'.
                          format(response.status_code, response.content))
        else:
            self.error('Failed to approve user.', response)

    def _owner_approve_attach_by_reuqest_id(self, request_id):
        self.log.info('Owner is approving the attach request by reuqest ID...')
        response = self.owner_bearer_request(
            method='POST',
            url='{0}/device/v2/device/attach/{1}'.format(self.environment.get_device_service(), request_id),
            data=json.dumps({
                "status": "APPROVED"
            })
        )
        if response.status_code == 200:
            self.log.info('User: {} is successfully attached to device'.format(self.username))
        elif response.status_code == 409:
            self.log.info('User is already approved, status code: {0}, error message: {1}'.
                          format(response.status_code, response.content))
        else:
            self.error('Failed to approve user', response)

    def _get_request_id(self):
        """ Get request ID after user have sended attache request. """
        self.log.info('Gettiing request ID...')
        # It's fine to use owner's token or attached user's token.
        user_id = self.get_user_id()
        device_id, security_code, local_code, time = self.get_local_code_and_security_code()

        response = self.bearer_request(
            method='GET',
            url='{0}/device/v1/device/{1}/user/{2}/requestId'.format(self.environment.get_device_service(), device_id, user_id)
        )
        if response.status_code == 200:
            return response.json().get('data', {}).get('requestId', None)
        else:
            self.error('Failed to get request ID', response)

    def generate_upload_data_info(self, data_name, file_content, parent_folder, parent_id, data_type, generate_file):
        """
            Generate a data binary for uploading folder/file

            :param data_name: The name of folder/file that will be created in device
            :param file_content: The file content in binary format. If specified,
                                 a file will be creates, otherwise a folder will be created.
            :param parent_folder: The place where the folder/file will be created.
                                  Folder will be searched by Name.
                                  Can be 'root' or parent folder name, 'root' means the first layer of the user folder.
            :param parent_id: The place where the folder/file will be created.
                              Folder will be searched by ID.
        """

        self.log.debug('Generating upload {} info'.format(data_type))

        if not parent_id:
            if parent_folder:
                folder_id_list, page_token = self.get_data_id_list()
                if parent_folder in folder_id_list.keys():
                    parent_id = folder_id_list[parent_folder]
                else:
                    self.error('Cannot find specified parent folder: {}'.format(parent_folder))
            else:
                parent_id = 'root'

        with open(os.path.join(os.getcwd(), generate_file), 'wb') as fo:
            fo.write('--foo\n\n')
            command = '{'
            command += '"parentID":"{0}", "name":"{1}"'.format(parent_id, data_name)
            if file_content:
                if '.' in file_content:
                    file_format = file_content.split('.')[1]
                    if file_format == 'jpg':
                        command += ', "mimeType":"image/jpeg"'
                    elif file_format == 'mov' or file_format == 'MOV':
                        command += ', "mimeType":"video/quicktime"'
                    elif file_format == 'mpg' or file_format == 'MPG':
                        command += ', "mimeType":"video/mpeg"'
                    elif file_format == 'mp3':
                        command += ', "mimeType":"audio/mpeg3"'
                    elif file_format == 'mp4':
                        command += ', "mimeType":"video/mp4"'
            else:
                command += ', "mimeType":"application/x.wd.dir"'
            command += '}\n'
            fo.write(command)
            if file_content:
                fo.write('--foo\n\n')
                fo.write('{}\n'.format(file_content))

            fo.write('--foo--\n')

        self.log.debug('Upload {} info generated successfully'.format(data_type))

    def upload_data(self, data_name, file_content=None, parent_folder=None, parent_id=None, suffix=None,
            cleanup=False, timeout=120, resolve_name_conflict=False):
        """
            Create folder or file in user root directory or in it's sub folders

            :param data_name: The name of created file or folder
            :param file_content: The data binary of a file. If specified, a file will be created,
                                 otherwise a folder will be created
            :param parent_folder: If specified, leave parent id as None.
                                  Enter the file name of parent folder.
                                  'None' means folder/file will be created in root directory,
                                  otherwise it will be in specified sub-folder. Default is 'None'
            :param parent_id: If specified, leave parent folder as None.
                              Enter the id of parent folder.
        """
        if file_content:
            data_type = 'file'
            generate_file = 'uploadFile'
        else:
            data_type = 'folder'
            generate_file = 'uploadFolder'

        if suffix:
            generate_file += '-{}'.format(suffix)

        self.log.debug('generated_file:{}'.format(generate_file))
        self.log.debug('Uploading data')
        self.generate_upload_data_info(data_name, file_content, parent_folder, parent_id, data_type, generate_file)
        access_token = self.get_id_token()
        url = '{}/sdk/v2/files'.format(self.url_prefix)
        if resolve_name_conflict:
            url = url + '?resolveNameConflict=1'
        headers = {'Authorization': 'Bearer {}'.format(access_token),
                   'Content-Type': 'multipart/related;boundary=foo'}
        with open(os.path.join(os.getcwd(), generate_file), 'rb') as f:
            data = f.read()
            self.log.debug('Start upload data')
            result = requests.post(url=url, headers=headers, data=data, timeout=timeout)

        if result.status_code == 201:
            self.log.debug('The {0}: {1} is successfully created in NAS directory'.format(data_type, data_name))
        elif result.status_code == 409:
            self.log.debug('The {0} is already exists in the NAS folder'.format(data_type))
        else:
            self.error('The {0} is not created successfully, status code: {1}, error message: {2}'.
                       format(data_type, result.status_code, result.content))

        if cleanup:
            self.log.debug('Cleaning up the generated file: {}'.format(generate_file))
            os.remove(os.path.join(os.getcwd(), generate_file))

        # Location: '/sdk/v2/files/6cJ1JmK3ObY_N3EQlVGH-ASYmPVtOPmo46i5JqGj'
        file_id = result.headers['Location'].rsplit('/').pop()
        return file_id

    def get_file(self, file_id=None, timeout=120):
        """
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#get-file
        """
        self.log.debug('Getting file information')
        response = self.bearer_request(
            method='GET',
            url='{}/sdk/v2/files/{}'.format(self.url_prefix, file_id),
            timeout=timeout
        )
        if response.status_code != 200:
            self.error('Failed to get information of File_ID {0}.'.format(file_id), response)
        return response.content, response.elapsed

    def get_file_content_v3(self, file_id, size=None, temp_size_max=None, download=None,
            cache_control_max_age=None, cache_bust_value=None):
        """ Get file thumbnails. """
        self.log.debug('Getting file content v3')
        params = []
        if size: params.append('size={}'.format(size))
        if temp_size_max: params.append('tempSizeMax={}'.format(temp_size_max))
        if download: params.append('download={}'.format(download))
        if cache_control_max_age: params.append('cacheControlMaxAge={}'.format(cache_control_max_age))
        if cache_bust_value: params.append('cacheBustValue={}'.format(cache_bust_value))
        params_str = '?' + '&'.join(params) if params else ''
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v3/files/{1}/content{2}'.format(self.url_prefix, file_id, params_str),
        )
        if response.status_code != 200:
            self.error('Failed to execute get file content.', response)
        return response

    def get_permission(self, file_id, user_id=None, entity_id=None, entity_type='user'):
        """
            Get the local folder/file permission of a user

            :param file_id: The folder/file id to check permission
            :param user_id: Can be 'user ID', 'somebody', 'anybody', or 'None' to get all the permission info
            :return: A share record in json format
        """
        self.log.debug('Getting file permission')
        access_token = self.get_id_token()
        url = '{}/sdk/v1/filePermsSearch/granting'.format(self.url_prefix)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {}'.format(access_token)}
        params = {'fileID': file_id}
        if user_id:
            params['userID'] = user_id # Is this still available?
        if entity_id:
            params['entityID'] = entity_id
            params['entityType'] = entity_type

        result = requests.get(url, headers=headers, params=params)
        if result.status_code == 200:
            self.log.debug("Get file permission successfully, response:\n{}".format(result.json()))
            return result.json()
        else:
            self.error('Failed to get file permission, status code: {0}, error message: {1}'.
                       format(result.status_code, result.content))

    def set_permission(self, file_id, user_id='anybody', entity_type='user', permission='ReadFile'):
        """
            Set local folder/file permission to a user

            :param file_id: The folder/file id to set permission
            :param user_id: Can be 'user ID', 'somebody' or 'anybody'
            :param permission: Can be 'ReadFile', 'WriteFile', 'ReadFilePerms', or 'WriteFilePerms'
            :return: A share record in json format
        """
        self.log.debug('Setting file permission')
        access_token = self.get_id_token()
        url = '{}/sdk/v1/filePerms'.format(self.url_prefix)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {0}'.format(access_token)}
        data = {'fileID': file_id,
                'entity': {
                    'id': user_id,
                    'type': entity_type
                },
                'value': permission}

        result = requests.post(url, headers=headers, data=json.dumps(data))
        if result.status_code == 201:
            self.log.debug('Set permission: {0} to user: {1} successfully'.format(permission, user_id))
            return result.content
        elif result.status_code == 409:
            self.log.debug('Permission: {0} is already set to user: {1} before'.format(permission, user_id))
        else:
            self.error('Failed to set permission: {0} to user: {1}, status code: {2}, error message: {3}'.
                       format(permission, user_id, result.status_code, result.content))

    def delete_permission(self, permission_id):
        """ Delete the specified file permission.

            :param permission_id: Permission ID to delete.
        """
        self.log.info('Deleting file permission with ID: {}'.format(permission_id))
        response = self.bearer_request(
            method='DELETE',
            url='{}/sdk/v1/filePerms/{}'.format(self.url_prefix, permission_id)
        )
        if response.status_code != 204:
            self.error('Failed to execute deleting file permission', response)
        return response

    def create_shares(self, owner_id, user_id, file_id, timeout=120):
        """
            Creates a permission record and send a call to the Cloud to create a share record

            :param owner_id: The user id of the folder/file owner
            :param user_id: The user id that added permission to the folder/file
            :param file_id: The folder/file id to set permission
            :return: A share id in String format. ex.
        """
        self.log.info('Creating shares record on the cloud')
        device_id = self.get_local_code_and_security_code()[0]
        data = {'ownerId': owner_id,
                'deviceId': device_id}
        self.log.info('The file id is {}'.format(file_id))
        if isinstance(file_id, basestring):
            data['fileIds'] = [file_id]
        else:
            data['fileIds'] = file_id

        if isinstance(user_id, basestring):
            data["userIds"] = [user_id]
        else:
            data["userIds"] = user_id

        response = self.bearer_request(
            method='POST',
            url='{}/v1/shares'.format(self.environment.get_share_service()),
            data=json.dumps(data),
            timeout=timeout
        )

        if response.status_code == 201:
            share_id = response.json()['data']['shareId']
            self.log.info('Shares record is created successfully, share ID: {}'.format(share_id))
            return share_id
        else:
            self.error('Failed to create shares record failedr.', response)

    def get_shares(self, share_id, timeout=120):
        """
            Get the share record on the cloud by share id

            :param share_id: The share id created when the shares record is created
            :return: A share record in json format
        """
        self.log.info('Getting shares info')
        response = self.bearer_request(
            method='GET',
            url='{0}/v1/shares/{1}'.format(self.environment.get_share_service(), share_id),
            timeout=timeout
        )
        if response.status_code == 200:
            self.log.info('Get shares successfully')
            return response.json()
        else:
            self.error('Failed to get shares info.', response)

    def get_installed_apps(self, app_id=''):
        """
            Get installed apps
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#get-apps
        """
        if app_id:
            app_id = '/{}'.format(app_id)
        self.log.info('Getting installed apps')
        response = self.bearer_request(
            method='GET',
            # NOTES: No one use it, please check it again before you use.
            # device_id = self.get_local_code_and_security_code()[0]
            # url='{0}/{1}/sdk/v1/apps'.format(self.environment.get_external_uri(), device_id),
            url = '{}/sdk/v1/apps{}'.format(self.url_prefix, app_id)
        )
        if response.status_code == 200:
            self.log.info('Get installed apps successfully')
            if app_id:
                return response.json()
            else:
                return response.json().get('apps')
        else:
            self.error('Failed to get installed app list.', response)

    def install_app(self, app_id, app_url=None, retry_times=None):
        """
            Install app to device
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#install-app
        """
        self.log.info('Installing app({})...'.format(app_id))
        response = self.bearer_request(
            method='PUT',
            # NOTES: No one use it, please check it again before you use.
            # device_id = self.get_local_code_and_security_code()[0]
            # url='{0}/{1}/sdk/v1/apps/{2}'.format(self.environment.get_external_uri(), device_id, app_id),
            url='{0}/sdk/v1/apps/{1}'.format(self.url_prefix, app_id),
            params={'downloadURL': app_url},
            retry_times=retry_times
        )
        if response.status_code == 204:
            self.log.info('Please wait, the app({0}) is still under installing, status code: {1}'.format(app_id, response.status_code))
        elif response.status_code == 409:
            self.log.info('Please wait, the app({0}) is still under installing, status code: {1}'.format(app_id, response.status_code))
        elif response.status_code >= 500:
            if retry_times == 0:
                self.log.warning('Status code {0} happening on install app({1}), and do not retry has been set,'
                    'do not do anything'.format(response.status_code, app_id))
            if retry_times is not 0:
                self.log.warning('Status code {0} happening on install app({1}), '
                    'retry to send install request again for {2} times'.format(response.status_code, app_id, retry_times))
        else:
            self.error('Failed to install app({}).'.format(app_id), response)
        return response.status_code

    def uninstall_app(self, app_id, retry_times=None):
        """
            Uninstall an ondevice app
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#uninstall-app
        """
        self.log.info('Uninstalling app({})...'.format(app_id))
        response = self.bearer_request(
            method='DELETE',
            # NOTES: No one use it, please check it again before you use.
            # device_id = self.get_local_code_and_security_code()[0]
            # url='{0}/{1}/sdk/v1/apps/{2}'.format(self.environment.get_external_uri(), device_id, app_id)
            url='{0}/sdk/v1/apps/{1}'.format(self.url_prefix, app_id),
            retry_times=retry_times
        )
        if response.status_code == 204:
            self.log.info('The app({0}) is uninstalled successfully, status code: {1}'.format(app_id, response.status_code))
        elif response.status_code == 404:
            self.log.info('The app({0}) is not found on device. status code: {1}'.format(app_id, response.status_code))
        elif response.status_code >= 500:
            if retry_times == 0:
                self.log.warning('Status code {0} happening on uninstall app({1}), and do not retry has been set,'
                    'do not do anything'.format(response.status_code, app_id))
            if retry_times is not 0:
                self.log.warning('Status code {0} happening on uninstall app({1}), '
                    'retry to send uninstall request again for {2} times'.format(response.status_code, app_id, retry_times))
        else:
            self.error('Failed to delete app({}).'.format(app_id), response)
        return response.status_code

    def create_file_copy(self, data_id, dest_parent_id=''):
        """
            API "Create File Copy", the document link:
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#create-file-copy

            Copies/syncs an entire file tree from id, which is a root.
            The copy recurses into children, and creates a directory at the root.

            :param data_id: The source folder/file ID
            :return: A copy ID, use for "get file copy" method to check copy progress
        """
        self.log.info("Creating file copy")
        id_token = self.get_id_token()

        url = '{}/sdk/v2/files/{}/copy'.format(self.url_prefix, data_id)
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer {0}'.format(id_token)}
        data = json.dumps({'destinationParentID':dest_parent_id})
        result = requests.post(url, headers=headers, data=data)
        if result.status_code == 201:
            self.log.info('Create file copy successfully!')
            location = result.headers['Location']
            copy_id = location.split('/fileCopies/')[1]
            self.log.info('Copy ID: {}'.format(copy_id))
            return copy_id
        else:
            self.error('Create file copy failed, status code:{0}, error log:{1}'.
                       format(result.status_code, result.content))

    def create_file_copy_v2(self, source_ids='', target_id=''):
        """
            https://github.com/wdc-csbu/restsdk/blob/403a32cabc40cbb0303bcc7d2dc655cab683a45f/doc/http/06.3.file_copy.md
            Notice that the source_ids has to be a list.
        """
        self.log.info("Creating file copy")
        if not target_id:
            data_list, page_token = self.search_file_by_parent(parent_id='')
            self.log.info("List top level: {}".format(str(data_list)))
            for item in data_list:
                if item['storageType'] == 'filesystem' and item['name'] == self.get_user_id() :
                    target_id = item['id']
                    break
        response = self.bearer_request(
            method='POST',
            url='{}/sdk/v2/fileCopies'.format(self.url_prefix),
            data = json.dumps({'sourceIDs':source_ids, 'targetID':target_id})
        )
        if response.status_code == 201:
            self.log.info('Create file copy successfully!')
            location = response.headers['Location']
            copy_id = location.split('/fileCopies/')[1]
            self.log.info('Copy ID: {}'.format(copy_id))
            return copy_id
        else:
            self.error('Create file copy failed, status code:{0}, error log:{1}'.
                       format(response.status_code, response.content))

    def get_file_copy(self, copy_id, api_version='v1', timeout=120):
        """
            API "Get File Copy", the document link:
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#get-file-copy

            Check the copy progress by copy ID

            :param copy_id: The copy ID returned from "create file copy" method
            :return: File copy status in json format. Example:
                     {
                         "status": "done",
                         "name": "ADATA UFD",
                         "elapsedDuration": 36.210581497,
                         "otalBytes": 713630411,
                         "checkedCount": 2,
                         "copiedCount": 6,
                         "runningCopies": None,
                         "rate": 168.77461548105782,
                         "startTime": 2016-11-16T08:35:37Z,
                         'errorCount": 0
                     }
        """
        self.log.info("Getting file copy status")
        id_token = self.get_id_token()

        url = '{}/sdk/{}/fileCopies/{}'.format(self.url_prefix, api_version, copy_id)
        headers = {'Authorization': 'Bearer {0}'.format(id_token)}
        result = requests.get(url, headers=headers, timeout=timeout)
        if result.status_code == 200:
            self.log.info('Get file copy successfully!')
            self.log.debug('Get file copy status:\n{}'.format(result.json()))
            return result.json()
        elif result.status_code == 404:
            self.error('The copy process might be finished or the copy id:{} is incorrect.'.format(copy_id), result)
        else:
            self.error('Get file copy failed', result)

    def search_file_by_parent_and_name(self, name, parent_id='root', timeout=120, no_raise_error=False):
        """
            API "Search File By Parent And Name", the document link:
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#search-a-file-by-parent-and-name

            Searches for a file having the specified parentID and name.


        :param parent_id: The parent ID to search within.
                          A not present value will retrieve the root node the matches the name.
                          The value of root retrieves the file in the user's root that matches the name.
        :param name: The name of the file to search for.
        :return: File information in json format and how many time use for searching. Example:
                 {
                     "mimeType": "application/octet-stream",
                     "name": "wd_monarch.uboot32.fb.dvrboot.exe.bin",
                     "extension": ".bin",
                     "storageType": "local",
                     "mTime": "2016-11-14T13:15:14Z",
                     "eTag": "Ag",
                     "privatelyShared": False,
                     'parentID": "6fnLnjmERI3VdVLc9bMWfmeSWTN-KfpUxVx3z9aP",
                     "hidden": "none",
                     "publiclyShared": False,
                     "id": "0xejlal648iBjC2hrSPXGsrxRWC0x_lxtO_y3oJH",
                     "size": 841256
                 },
                 0:00:00.052704
        """
        # Todo: This method might be able to merge into "get_data_id_list" method?
        self.log.info("Searching file by parent_id:{0} and name: {1}".format(parent_id, name))
        id_token = self.get_id_token()
        url = '{}/sdk/v2/filesSearch/parentAndName'.format(self.url_prefix)
        headers = {'Authorization': 'Bearer {0}'.format(id_token)}
        params = {'parentID': parent_id,
                  'name': name}
        result = requests.get(url, headers=headers, params=params, timeout=timeout)
        if result.status_code == 200:
            self.log.info('Search file by parent and name successfully!')
            self.log.debug('Search time: {}'.format(result.elapsed))
            self.log.debug('Search file by parent and name result:\n{}'.format(result.json()))
            return result.json(), result.elapsed
        else:
            if no_raise_error:
                self.log.warning('No raise error, status code:{0}, error log:{1}'.
                                format(result.status_code, result.content))
                return result
            else:
                self.error("Search file by parent and name failed, status code:{0}, error log:{1}".
                           format(result.status_code, result.content))

    def delete_file(self, data_id, timeout=600, as_owner=False):
        """
            API "Delete file", the document link:
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#delete-file

            Delete file by file ID

            :param data_id: The file/folder ID
            :return: Boolean, elapsed time
        """
        self.log.debug("Deleting data with ID: {}".format(data_id))

        if as_owner: # For the user who is not owner, he/she may cannot get information because not approved.
            request_inst = self.owner_bearer_request
        else:
            request_inst = self.bearer_request

        response = request_inst(
            method='DELETE',
            url='{}/sdk/v2/files/{}'.format(self.url_prefix, data_id),
            timeout=timeout
        )

        if response.status_code == 204:
            self.log.debug('Delete file synchronously successfully!')
            return True, response.elapsed
        elif response.status_code == 202:
            self.log.debug('Delete file asynchronously successfully!')
            return True, response.elapsed
        else:
            self.error('Delete file failed', response)

    def reboot_device(self):
        """
            API "Reboot Device", the document link:
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#update-device

            Reboot Device

            :return: Boolean
        """
        self.log.debug('Rebooting device')
        response = self.bearer_request(
            method='PUT',
            url='{}/sdk/v1/device'.format(self.url_prefix),
            data=json.dumps({
                'boot': {
                    'time': '2000-01-01T00:00:00.000000000Z',
                    'type': 'reboot'
            }})
        )
        if response.status_code not in [204]:
            self.error('Failed to execute reboot API', response)
        self.log.debug('Reboot API executing successfully')
        return True

    def factory_reset(self):
        """
            API "Factory Restore Device", the document link:
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#factory-restore-device
            Warnings: This will delete all user data

            return: Boolean
        """
        self.log.info("Factory Restore Device")
        response = self.bearer_request(
            method='DELETE',
            url='{0}/sdk/v1/device'.format(self.url_prefix)
        )
        if response.status_code not in [204]:
            self.error('Failed to execute factory restore API', response)
        return True

    def get_usb_info(self, usb_name=None):
        """
            Get the first found USB information.

            :param usb_name: Specify USB with device name.
            :return: dict or None. Example:
                    {'cTime': '2017-02-22T06:02:39.973Z',
                     'childCount': 0,
                     'eTag': '"Ag"',
                     'hidden': 'none',
                     'id': '3206-43CF',
                     'mTime': '2017-02-22T06:02:39.973Z',
                     'mimeType': 'application/x.wd.dir',
                     'name': 'Transcend',
                     'parentID': '',
                     'privatelyShared': False,
                     'publiclyShared': False,
                     'storageType': 'usb'}
        """
        self.log.info("Get USB information")
        data_list, page_token = self.search_file_by_parent(parent_id='')
        self.log.info("List top level: {}".format(str(data_list)))
        for item in data_list:
            # Only try TRANSCEND, ADATA and WD My Passport, add more filter rules if we need to support new USB device.
            if item['storageType'] == 'usb' or (not item['storageType'] and item['name'] == 'My Passport'):
                if usb_name:
                    if item['name'] == usb_name:
                        return item
                    continue
                return item
        return None

    def clean_usb_by_rm(self, adb_inst, usb_name=None, timeout=60*60*12, name_list=None):
        """ Delete data in USB disk with specified name list or all. (Use "adb shell rm -rf") 
        Note: rm 50 GB need over 6 hr.
        """
        self.log.info("Delete data in USB disk.")
        usb_info = self.get_usb_info(usb_name=usb_name)
        self.log.info("Ready to delete data in USB disk: {}".format(usb_info))
        if not name_list:
            name_list = ['*']
        # Delete all data with name_list.
        for name in name_list:
            rm_path = '{0}{1}/{2}'.format(Kamino.MOUNT_PATH, usb_info['id'], name)
            adb_inst.executeShellCommand(cmd='rm -rf {}'.format(rm_path), timeout=timeout)

    def gen_file_to_usb(self, adb_inst, name, size, location=None, usb_name=None, timeout=60*5, debug=True):
        """ Create file in USB disk. """
        self.log.info("Create file in USB disk.")
        usb_info = self.get_usb_info(usb_name=usb_name)
        self.log.info("Ready to create file in USB disk: {}".format(usb_info))
        file_path = '{0}{1}/{2}'.format(Kamino.MOUNT_PATH, usb_info['id'], name)
        if debug: adb_inst.executeShellCommand('ls -al {}'.format('{0}{1}/'.format(Kamino.MOUNT_PATH, usb_info['id'])))
        adb_inst.executeShellCommand(cmd='dd if=/dev/urandom of={0} bs={1} count=1'.format(file_path, size), timeout=timeout)
        success, _ = adb_inst.executeShellCommand('"test -f {} && echo y"'.format(file_path))
        if not success:
            return False
        return True

    def get_files_of_usb(self, adb_inst, usb_name=None, max_depth=None):
        """ Create file of USB disk. """
        self.log.info("Get files of USB disk.")
        usb_info = self.get_usb_info(usb_name=usb_name)
        self.log.info("USB disk info: {}".format(usb_info))
        output, _ = adb_inst.executeShellCommand(
            'find {0} -type f {1}'.format(
                #'{0}{1}/'.format(Kamino.MOUNT_PATH, usb_info['id']),
                '{0}*'.format(Kamino.MOUNT_PATH), # hot fix for 2017/7/1 change. Get it from GET /sdk/v1/storage/:id after Steve updated. 
                '-maxdepth {}'.format(max_depth) if max_depth else ''
            )
        )
        files = output.split('\r\n')
        files.pop()
        return files

    def clean_user_root(self, id_list=None):
        """ Delete data in owner's home directory with specified ID list or all. """
        self.log.info("Delete data in owner's home directory.")
        if not id_list: # Get all data in owner's home directory.
            data_list = self._search_data_until_limit(search_method=self.search_file_by_parent, field_keep_keys=['id'])
            id_list = [data['id'] for data in data_list]
        # Delete all data with id_list.
        for data_id in id_list:
            try:
                self.delete_file(data_id=data_id)
            # Hot fixed for "Family" folder can not removed.
            # If this way is not good, we need to filter file list.
            except requests.HTTPError as e:
                if e.response.status_code != 404:
                    raise
            except RuntimeError as e:
                if '404' not in str(e):
                    raise

    def _search_data_until_limit(self, search_method, search_kargs={}, field_keep_keys=None,
            limit=None, data_key='files'):
        """ Get "limit" number of data with search method. Get all if limit is not specified. """
        query_args = search_kargs.copy()
        return_list = []
        residual_num = limit or -1
        while residual_num:
            data_list, next_page_token = search_method(**query_args)
            query_args['page_token'] = next_page_token
            if field_keep_keys: # Lighten data size.
                data_list = [{key: data[key] for key in field_keep_keys} for data in data_list]

            num_of_data = len(data_list)
            if not num_of_data: # no data return
                break
            # Unlimit case always append data.
            if residual_num == -1:
                return_list.extend(data_list)
            # Or append sufficient data to achieve limit number. 
            else:
                if num_of_data > residual_num:
                    decrease_num = residual_num
                else:
                    decrease_num = num_of_data
                residual_num-=decrease_num
                return_list.extend(data_list[:decrease_num])
            if not next_page_token: # no next page
                break
        return return_list

    def clean_user_root_by_rm(self, adb_inst, timeout=60*60*12, name_list=None):
        """ Delete data in owner's home directory with specified name list or all. (Use "adb shell rm -rf") 
        Note: rm 50 GB need over 6 hr.
              Not check with "Family" folder can not removed issue.
        """
        self.log.info("Delete data in owner's home directory.")
        if not name_list:
            name_list = ['*']
        # Delete all data with name_list.
        for name in name_list:
            rm_path = '{0}{1}/{2}'.format(Kamino.USER_ROOT_PATH, self.get_user_id(escape=True), name)
            adb_inst.executeShellCommand(cmd='rm -rf {}'.format(rm_path), timeout=timeout)

    def clean_user_root_by_delete_each(self):
        """ Delete data in owner's home directory by delete each files and each folders. 
        Note: Not check with "Family" folder can not removed issue.
        """
        self.log.info("Delete data in owner's home directory.")
        all_folder_ids = []
        # Handle root parent.
        file_id_list, sub_folder_ids = self.walk_folder(search_parent_id='root')
        self.log.info("Delete files...")
        for file_id in file_id_list:
            self.delete_file(data_id=file_id)
        all_folder_ids.extend(sub_folder_ids)

        # Search sub-folders from top to bottom.
        while sub_folder_ids:
            next_round_ids = []
            for folder_id in sub_folder_ids:
                file_id_list, folder_id_list = self.walk_folder(search_parent_id=folder_id)
                for file_id in file_id_list:
                    self.delete_file(data_id=file_id)
                next_round_ids+=folder_id_list # Collect deeper level sub-folder IDs.
            sub_folder_ids = next_round_ids
            all_folder_ids.extend(sub_folder_ids)
            
        # Delete all folder from bottom to top.
        self.log.info("Delete folders...")
        all_folder_ids.reverse()
        for folder_id in all_folder_ids:
            self.delete_file(data_id=folder_id)

    def walk_folder(self, search_parent_id, scroll_limit=1000, item_parser=ItemParser.only_id):
        """ Just browse all items in specified folder page by page until no next page. """
        file_list = []
        folder_list = []
        next_page_token = None
        while True: # Walk one level.
            # Retry 20 times
            item_list, next_page_token = retry(
                func=self.search_file_by_parent, log=self.log.warning,
                **{'parent_id': search_parent_id, 'page_token': next_page_token, 'limit': scroll_limit}
            )
            for item in item_list:
                parsed_item = item_parser(item) if item_parser else item
                if item['mimeType'] == Kamino.MimeType.FOLDER:
                    folder_list.append(parsed_item)
                else:
                    file_list.append(parsed_item)

            if not next_page_token:
                return file_list, folder_list

    def usb_slurp(self, usb_name=None, folder_name=None, data_id=None, dest_parent_id='', timeout=3600, wait_until_done=True, api_version='v1'):
        """
            Copy entire data of the first found USB to owner's home directory with USB slurp API 
            :param usb_name: Specify USB with device name.
            :param timeout: Maximum wait time.
            :param wait_until_done: Return information after data copy has done.

            For api_version = v2, the data_id and dest_parent_id must to be rootID of data of filesystem.
        """
        self.log.info('Starting USB slurp')
        usb_info = self.get_usb_info(usb_name)
        if not usb_info:
            self.log.error('USB device not found.')
        self.log.info('USB Info: {}'.format(usb_info))
        if api_version == 'v1':
            if not data_id:
                if folder_name:
                    folder_id = self.get_data_id_list(type='folder', parent_id=usb_info['id'], data_name=folder_name)
                    if not folder_id:
                        self.log.error('Folder {} is not found under USB device'.format(folder_name))
                    self.log.warning('Slurp sub Folder ID: {}, folder name: {}'.format(folder_id, folder_name))
                    data_id = folder_id
                else:
                    data_id = usb_info['id']
            self.log.warning("Use [data_id: {}] and [dest_parent_id: {}] to run file copy".format(data_id, dest_parent_id))
            copy_id = self.create_file_copy(data_id=data_id, dest_parent_id=dest_parent_id)
        elif api_version == 'v2':
            copy_id = self.create_file_copy_v2(source_ids=data_id, target_id=dest_parent_id)
        self.log.info('Copy task ID: {}'.format(copy_id))
        if not wait_until_done:
            return copy_id, usb_info, None
        # Wait and monitor the slurp status.
        start_time = current_time = time.time()
        if api_version == 'v1':
            while current_time <= start_time+int(timeout):
                resp = retry( # retry 20 times
                    func=self.get_file_copy, excepts=(Exception), log=self.log.warning,
                    **{'copy_id': copy_id, 'api_version': api_version}
                )
                self.log.info('USB slurp status: {}'.format(resp))
                if not resp: # TODO: Find way to check current status.
                    self.error('Copy task not found')
                elif resp['status'] == 'done':
                    self.log.info('USB slurp is done')
                    return copy_id, usb_info, resp
                elif resp['status'] == 'running':
                    pass
                elif resp['status'] == 'error':
                    self.log.warning('USB Slurp error: {}'.format(resp)) # TODO: Verify this behavior by data comparison test.
                    return copy_id, usb_info, resp
                    #self.error('USB Slurp error: {}'.format(resp))
                else:
                    self.log.warning('Unknown case: {}'.format(resp))
                time.sleep(3)
                current_time = time.time()
            self.error('USB slurp timeout: {0}s. Copy ID: {1}. USB: {2}'.format(timeout, copy_id, usb_info))
        elif api_version == 'v2':
            while current_time <= start_time+int(timeout):
                resp = retry( # retry 20 times
                    func=self.get_file_copy, excepts=(Exception), log=self.log.warning,
                    **{'copy_id': copy_id, 'api_version': api_version}
                )
                self.log.info('USB slurp status: {}'.format(resp))
                if not resp: # TODO: Find way to check current status.
                    self.error('Copy task not found')
                elif resp['status'] == 'completed':
                    self.log.info('USB slurp is done')
                    return copy_id, usb_info, resp
                elif resp['status'] == 'in progress':
                    pass
                else:
                    self.log.warning('Unknown case: {}'.format(resp))
                time.sleep(3)
                current_time = time.time()
            self.error('USB slurp timeout: {0}s. Copy ID: {1}. USB: {2}'.format(timeout, copy_id, usb_info))

    def usb_export(self, usb_name=None, folder_name='', dest_parent_id='', timeout=3600, wait_until_done=True):
            """
                Copy entire data of the first found USB to owner's home directory with USB slurp API 

                :param usb_name: Specify USB with device name.
                :param timeout: Maximum wait time.
                :param wait_until_done: Return information after data copy has done.
            """
            
            self.log.info('Starting USB export')

            if not folder_name:
                self.error('There is no folder_name specified')
            folder_id = self.get_data_id_list(type='folder', parent_id='root', data_name=folder_name)
            if not folder_id:
                self.log.error('Folder {} is not found under target device'.format(folder_name))
            self.log.warning('Export sub Folder ID: {}, folder name: {}'.format(folder_id, folder_name))
            data_id = folder_id

            usb_info = self.get_usb_info(usb_name)
            if not usb_info:
                self.log.error('USB device not found.')
            self.log.info('USB Info: {}'.format(usb_info))

            self.log.info("Use ID: {} to run file copy".format(data_id))
            if not dest_parent_id:
                dest_parent_id = usb_info['id']            
            copy_id = self.create_file_copy(data_id=data_id, dest_parent_id=dest_parent_id)
            
            self.log.info('Copy task ID: {}'.format(copy_id))

            if not wait_until_done:
                return copy_id, usb_info, None

            # Wait and monitor the slurp status.
            start_time = current_time = time.time()
            while current_time <= start_time+int(timeout):
                resp = retry( # retry 20 times
                    func=self.get_file_copy, excepts=(Exception), log=self.log.warning,
                    **{'copy_id': copy_id}
                )
                self.log.info('USB export status: {}'.format(resp))
                if not resp: # TODO: Find way to check current status.
                    self.error('Copy task not found')
                elif resp['status'] == 'done':
                    self.log.info('USB export is done')
                    return copy_id, usb_info, resp
                elif resp['status'] == 'running':
                    pass
                elif resp['status'] == 'error':
                    self.log.warning('USB export error: {}'.format(resp)) # TODO: Verify this behavior by data comparison test.
                    return copy_id, usb_info, resp
                    #self.error('USB Slurp error: {}'.format(resp))
                else:
                    self.log.warning('Unknown case: {}'.format(resp))
                time.sleep(3)
                current_time = time.time()
            self.error('USB export timeout: {0}s. Copy ID: {1}. USB: {2}'.format(timeout, copy_id, usb_info))


    def delete_file_by_name(self, name, parent_id='root'):
        self.log.info('Deleting file by name')
        item, elapsed = self.search_file_by_parent_and_name(name=name, parent_id=parent_id)
        if item:
            self.log.info("Delete item (name={0} mimeType={1}) in directory({2})...".format(
                item['name'], item['mimeType'], parent_id
            ))
            self.delete_file(data_id=item['id'])

    def get_data_by_id(self, data_id):
        self.log.info('Getting data by ID')
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v2/files/{1}'.format(self.url_prefix, data_id)
        )
        if response.status_code != 200:
            self.error('Failed to search file by text', response)
        return response.json()

    def search_file_by_text(self, keyword, fields=None, limit=1000, page_token=None):
        """ Search file by text. 

            :param keyword: A keyword to case insensitive search files by field "name" and field "mimeType".
            :param fields: Specify the response fields of matched files. 
            :param limit: Maximum number of data per response.
            :param page_token: Search data after specify page.
            :return: A list of matched files. Example:
                {'matches': [{'file': {'cTime': '2017-04-24T08:45:28.941Z',
                                       'childCount': 47,
                                       'eTag': '"xiU"',
                                       'hidden': 'none',
                                       'id': 'TKgsmJHarYHmQxz5cYvc4kJSmPW7kBFtkTKae7To',
                                       'mTime': '2017-04-27T13:07:58.85Z',
                                       'mimeType': 'application/x.wd.dir',
                                       'name': 'auth0|58edcc8f08a65c15d640986b',
                                       'parentID': '',
                                       'privatelyShared': False,
                                       'publiclyShared': False,
                                       'storageType': 'local'},
                              'fragments': [{'locations': [{'index': 12, 'length': 8}],
                                             'text': 'application/x.wd.dir'}]}],
                 'pageToken': 'mgo'}
        """
        self.log.info('Searching file by keyword: {}'.format(keyword))
        # Handle arguments and compose URL parameters.
        params = '?q=' + keyword
        if fields: params += '&fields={}'.format(fields)
        if limit: params += '&limit={}'.format(limit)
        if page_token: params += '&pageToken={}'.format(page_token)
        # Send request
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v2/filesSearch/text{1}'.format(self.url_prefix, params)
        )
        if response.status_code != 200:
            self.error('Failed to search file by text', response)
        json_result = response.json()
        return json_result.get('matches', []), json_result.get('pageToken', '')

    def search_audio_file(self, fields=None, limit=1000, page_token=None):
        """ Search audio file order by title(file name). """
        self.log.info('Searching audio file')
        # Handle arguments and compose URL parameters.
        params = []
        if fields: params.append('fields={}'.format(fields))
        if limit: params.append('limit={}'.format(limit))
        if page_token: params.append('pageToken={}'.format(page_token))
        params_str = '?' + '&'.join(params) if params else ''
        # Send request
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v2/filesSearch/audioTitle{1}'.format(self.url_prefix, params_str)
        )
        if response.status_code != 200:
            self.error('Failed to search file by text', response)
        json_result = response.json()
        return json_result.get('files', []), json_result.get('pageToken', '')

    def search_sample_file_by_time(self, start_time, end_time, mime_groups, fields=None, limit=1000):
        """ Search sample media file by time. 

        :param start_time: The inclusive time for the oldest image, ex: 2000-05-09T07:00:45.176Z.
        :param end_time: The inclusive time for the newest image.
        :param mime_groups: The group of the mimeType's to include. This is the RFC type such as image or application.
        """
        self.log.info('Searching smaple file by time')
        # Handle arguments and compose URL parameters.
        params = '?startTime={0}&endTime={1}&mimeGroups={2}'.format(start_time, end_time, mime_groups)
        if fields: params += '&fields={}'.format(fields)
        if limit: params += '&limit={}'.format(limit)
        # Send request
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v2/filesSearch/mediaTimeSample{1}'.format(self.url_prefix, params)
        )
        if response.status_code != 200:
            self.error('Failed to search sample media file by time', response)
        json_result = response.json()
        return json_result.get('files', [])

    def search_file_by_time(self, start_time, end_time, mime_groups, min_width=None, min_height=None, fields=None, limit=1000):
        """ Search media file by time. 

        :param start_time: The inclusive time for the oldest image, ex: 2000-05-09T07:00:45.176Z.
        :param end_time: The inclusive time for the newest image.
        :param mime_groups: The group of the mimeType's to include. This is the RFC type such as image or application.
        :param min_width: Integer. The minimum width of the media.
        :param min_height: Integer. The minimum height of the media.
        """
        self.log.info('Searching smaple file by time')
        # Handle arguments and compose URL parameters.
        params = '?startTime={0}&endTime={1}&mimeGroups={2}'.format(start_time, end_time, mime_groups)
        if min_width: params += '&minWidth={}'.format(min_width)
        if min_height: params += '&minHeight={}'.format(min_height)
        if fields: params += '&fields={}'.format(fields)
        if limit: params += '&limit={}'.format(limit)
        # Send request
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v2/filesSearch/mediaTime{1}'.format(self.url_prefix, params)
        )
        if response.status_code != 200:
            self.error('Failed to search media file by time', response)
        json_result = response.json()
        return json_result.get('files', []), json_result.get('pageToken', '')

    def test_restsdk(self):
        if self.get_uut_info():
            return True
        return False

    def get_uut_info(self):
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v1/device'.format(self.url_prefix)
        )
        if response.status_code != 200:
            self.error('Failed to execute get device info', response)
        return response.json()

    def get_users(self, fields=None, limit=1000):
        """ Get NAS attached users.

        :return: list of users, next page token
        """
        self.log.info('Getting users')
        # Handle arguments and compose URL parameters.
        params = '?limit={}'.format(limit)
        if fields: params += '&fields={}'.format(fields)
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v1/users{1}'.format(self.url_prefix, params)
        )
        if response.status_code != 200:
            self.error('Failed to execute get users.', response)
        resp_dict = response.json()
        return resp_dict.get('users'), resp_dict.get('pageToken')

    def get_user(self, user_id, fields=None):
        """ Get specific NAS attached user.

        :return: list of users, next page token
        """
        self.log.info('Getting user: {}'.format(user_id))
        # Handle arguments and compose URL parameters.
        params = ''
        if fields: params += '?fields={}'.format(fields)
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v1/users/{1}{2}'.format(self.url_prefix, user_id, params)
        )
        if response.status_code != 200:
            self.error('Failed to execute get user by ID.', response)
        return response.json()

    def delete_file_copy(self, copy_id):
        """ Abort file copy. """
        self.log.info("Deleting file copy status")
        response = self.bearer_request(
            method='DELETE',
            url='{0}/sdk/v1/fileCopies/{1}'.format(self.url_prefix, copy_id)
        )
        if response.status_code != 202:
            self.error('Abort file copy failed', response)

    def get_video_stream(self, file_id, container, resolution=None, bit_rate=None, frame_rate=None,
            width=None, height=None, start_offset=None, duration=None, audio_codec=None, video_codec=None,
            check_only=None, stream=True, timeout=None):
        """ Get a transcoded video file stream 
        REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#get-transcoded-video

        :return: request response object
        """
        self.log.info('Getting video stream')
        params = '?container={}'.format(container)
        if resolution: params += '&resolution={}'.format(resolution)
        if bit_rate: params += '&bitRate={}'.format(bit_rate)
        if frame_rate: params += '&frameRate={}'.format(frame_rate)
        if width: params += '&width={}'.format(width)
        if height: params += '&height={}'.format(height)
        if start_offset: params += '&startOffset={}'.format(start_offset)
        if duration: params += '&duration={}'.format(duration)
        if audio_codec: params += '&audioCodec={}'.format(audio_codec)
        if video_codec: params += '&videoCodec={}'.format(video_codec)
        if check_only: params += '&checkOnly={}'.format(check_only)
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v2/files/{1}/video{2}'.format(self.url_prefix, file_id, params),
            stream=stream,
            timeout=timeout
        )
        if response.status_code != 200:
            self.error('Failed to execute get video stream.', response)
        return response

    def get_video_playlist(self, file_id, container, resolution=None, bit_rate=None, frame_rate=None,
            width=None, height=None, start_offset=None, duration=None, segment_duration=None, audio_codec=None,
            video_codec=None, check_only=None):
        """ Get a transcoded video file playlist. 
        REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#get-m3u8-video-playlist

        :return: request response object
        """
        self.log.info('Getting video playlist')
        params = '?container={}'.format(container)
        if resolution: params += '&resolution={}'.format(resolution)
        if bit_rate: params += '&bitRate={}'.format(bit_rate)
        if frame_rate: params += '&frameRate={}'.format(frame_rate)
        if width: params += '&width={}'.format(width)
        if height: params += '&height={}'.format(height)
        if start_offset: params += '&startOffset={}'.format(start_offset)
        if duration: params += '&duration={}'.format(duration)
        if segment_duration: params += '&segmentDuration={}'.format(segment_duration)
        if audio_codec: params += '&audioCodec={}'.format(audio_codec)
        if video_codec: params += '&videoCodec={}'.format(video_codec)
        if check_only: params += '&checkOnly={}'.format(check_only)
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v2/files/{1}/video/playlist{2}'.format(self.url_prefix, file_id, params),
        )
        if response.status_code != 200:
            self.error('Failed to execute get video playlist.', response)
        return response

    def get_media_time_groups(self, end_time, unit, mime_groups, fields=None, limit=None):
        """ Aggregates time information about groups of files.
        REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#get-media-time-groups
        """
        self.log.info('Getting media time groups')
        params = '?endTime={0}&unit={1}&mimeGroups={2}'.format(end_time, unit, mime_groups)
        if fields: params += '&fields={}'.format(fields)
        if limit: params += '&limit={}'.format(limit)
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v1/mediaTimeGroups{1}'.format(self.url_prefix, params)
        )
        if response.status_code != 200:
            self.error('Failed to execute get media time groups.', response)
        return response.json().get('mediaTimeGroups', [])

    def gen_body_metadata(self, parent_id='root', name=None, mime_type=None, m_time=None, c_time=None,
            hidden=None):
        """ Generate body metadata in dict object for upload/patch data. """
        body_part_1 = {}
        if parent_id: body_part_1['parentID'] = parent_id
        if name: body_part_1['name'] = name
        if mime_type: body_part_1['mimeType'] = mime_type # RESTSDK auto detect per content if it not specified.
        if m_time: body_part_1['mTime'] = m_time
        if c_time: body_part_1['cTime'] = c_time
        if hidden: body_part_1['hidden'] = hidden
        return body_part_1

    def gen_creation_body(self, file_content=None, boundary='foo', mime_type=None, parent_folder=None, **kwargs):
        """ Generate request body for creatiing folder/file.

            :param file_content: String. It has memory issue if upload big file.

        REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#create-resumable-file
        """
        # Body (part 1)
        if not kwargs.get('parent_id') and parent_folder: # Upload to specific folder.
            folder_id_list, page_token = self.get_data_id_list() # TODO: Only support 1 level for now.
            if parent_folder not in folder_id_list.keys():
                self.error('Cannot find specified parent folder: {}'.format(parent_folder))
            body_part_1 = self.gen_body_metadata(mime_type=mime_type, parent_id=folder_id_list[parent_folder], **kwargs)
        else: # Upload to user root.
            body_part_1 = self.gen_body_metadata(mime_type=mime_type, **kwargs)
        # Body (part 2)
        if mime_type == Kamino.MimeType.FOLDER:
            body_part_2 = ''
        else: # part 2 for file content
            # '--foo\n\nDATA\n'
            body_part_2 = '--{0}\n\n{1}\n'.format(boundary, file_content if file_content else '')

        # Compose request body
        # '--foo\n\n{"A": "B"}\n--foo--' or '--foo\n\n{"A": "B"}\n--foo\n\nDATA\n--foo--'
        return "--{0}\n\n{1}\n{2}--{0}--".format(boundary, json.dumps(body_part_1), body_part_2)

    def create_file(self, file_name, resolve_name_conflict=False, timeout=120, **kwargs):
        """ Create file in user root directory or in the specified folders (instead upload_date()).

        Other parameters refer to gen_creation_body().
        """
        self.log.info('Create file')
        params_str = ''
        if resolve_name_conflict: params_str = '?resolveNameConflict=1'

        response = self.bearer_request(
            method='POST',
            headers={'Content-Type': 'multipart/related;boundary=foo'},
            url='{0}/sdk/v2/files{1}'.format(self.url_prefix, params_str),
            data=self.gen_creation_body(name=file_name, **kwargs),
            timeout=timeout
        )
        if response.status_code == 201:
            # Location: '/sdk/v2/files/6cJ1JmK3ObY_N3EQlVGH-ASYmPVtOPmo46i5JqGj'
            file_id = response.headers['Location'].rsplit('/').pop()
            return file_id
        elif response.status_code == 409:
            self.log.info('The file is already exists in the NAS')
            return None
        try:
            self.error(response.json()['message'], response)
        except:
            self.error('Failed to execute create files.', response)

    def create_resumable_file(self, file_name, resolve_name_conflict=False, offset=0, done=False, timeout=120, parent_folder=None, **kwargs):
        """ Create resumable file in user root directory or in the specified folders.
        http://build-docs.wdmv.wdc.com/docs/restsdk.html#create-resumable-file
        Other parameters refer to gen_creation_body().
        """
        self.log.debug('Create resumable file')
        params = []
        if resolve_name_conflict: params.append('resolveNameConflict=1')
        if offset: params.append('offset={}'.format(offset))
        if done: params.append('done=true')
        params_str = '?' + '&'.join(params) if params else ''

        response = self.bearer_request(
            method='POST',
            headers={'Content-Type': 'multipart/related;boundary=foo'},
            url='{0}/sdk/v2/files/resumable{1}'.format(self.url_prefix, params_str),
            data=self.gen_creation_body(name=file_name, parent_folder=parent_folder, **kwargs),
            timeout=timeout
        )
        if response.status_code == 201:
            # Location: '/sdk/v2/files/6cJ1JmK3ObY_N3EQlVGH-ASYmPVtOPmo46i5JqGj'
            file_id = response.headers['Location'].rsplit('/').pop()
            return file_id
        elif response.status_code == 409:
            self.log.info('The file is already exists in the NAS')
            return None
        try:
            self.error(response.json()['message'], response)
        except:
            self.error('Failed to execute create resumable files.', response)

    def commit_folder(self, folder_name, **kwargs):
        """ Create folder by resumable way and commit it. """
        self.log.debug('Create remote folder via resumable API')
        kwargs['done'] = True # Create folder in resumable way have to commit it, or API response an error.
        kwargs['mime_type'] = Kamino.MimeType.FOLDER
        return self.create_resumable_file(file_name=folder_name, **kwargs)

    def create_folder(self, folder_name, parent_folder=None, parent_id=None):
        """ Web app use this way """
        self.log.debug('Create remote folder via file API')
        return self.upload_data(folder_name, parent_folder=parent_folder, parent_id=parent_id,
            suffix=uuid4().hex, resolve_name_conflict=True)

    def create_resumable_file_from_existing_file(self, file_id, offset=0, done=False, truncate=False):
        """ REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#create-resumable-file-starting-with-an-existing-file """
        self.log.deubg('Create resumable file from existing file')
        params = []
        if offset: params.append('offset={}'.format(offset))
        if done: params.append('done=true')
        if truncate: params.append('truncate=true')
        params_str = '?' + '&'.join(params) if params else ''

        response = self.bearer_request(
            method='POST',
            url='{0}/sdk/v2/files/{1}/resumable{2}'.format(self.url_prefix, file_id, params_str)
        )
        if response.status_code == 201:
            # Location: '/sdk/v2/files/6cJ1JmK3ObY_N3EQlVGH-ASYmPVtOPmo46i5JqGj/resumable'
            file_id = response.headers['Location'].rsplit('/')[-2]
            return file_id
        try:
            self.error(response.json()['message'], response)
        except:
            self.error('Failed to execute create resumable files from existing file.', response)

    def get_resumable_file(self, file_id, fields=None):
        """ REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#get-resumable-file """
        self.log.info('Getting resumable file with ID: {}'.format(file_id))
        params = '?fields={}'.format(fields) if fields else ''
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v2/files/{1}/resumable{2}'.format(self.url_prefix, file_id, params)
        )
        if response.status_code != 200:
            self.error('Failed to execute get resumable file', response)
        return response.json()

    def get_resumable_file_content(self, file_id, offset=None, length=None, download=False, timeout=120):
        """ REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#get-resumable-file-content """
        self.log.info('Getting resumable file content with ID: {}'.format(file_id))
        params = []
        if offset: params.append('offset={}'.format(offset))
        if length: params.append('length={}'.format(length))
        if download: params.append('download=true')
        params_str = '?' + '&'.join(params) if params else ''

        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v2/files/{1}/resumable/content{2}'.format(self.url_prefix, file_id, params_str),
            timeout=timeout
        )
        if response.status_code != 200:
            self.error('Failed to execute get resumable file content', response)
        return response.content

    def delete_resumable_file(self, file_id):
        """ REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#get-resumable-file-content """
        self.log.info('Deleting resumable file with ID: {}'.format(file_id))
        response = self.bearer_request(
            method='DELETE',
            url='{0}/sdk/v2/files/{1}/resumable'.format(self.url_prefix, file_id)
        )
        if response.status_code not in [202, 204]:
            self.error('Failed to execute deleting resumable file', response)
        return response

    def upload_resumable_file_content(self, file_id, data=None, offset=None, done=False, truncate=False, timeout=120):
        """ REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#update-resumable-file-content """
        if not self.reduce_log: self.log.debug('Uploading resumable file content with ID: {}'.format(file_id))
        params = []
        if offset: params.append('offset={}'.format(offset))
        if done: params.append('done=true')
        if truncate: params.append('truncate=true')
        params_str = '?' + '&'.join(params) if params else ''

        response = self.bearer_request(
            method='PUT',
            url='{0}/sdk/v2/files/{1}/resumable/content{2}'.format(self.url_prefix, file_id, params_str),
            data=data, timeout=timeout
        )
        if response.status_code != 204:
            self.error('Failed to execute uploading resumable file content', response)
        return response

    def upload_file_content(self, file_id, data=None):
        """ REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#update-file-content """
        self.log.info('Uploading file content with ID: {}'.format(file_id))
        response = self.bearer_request(
            method='PUT',
            url='{0}/sdk/v2/files/{1}/content'.format(self.url_prefix, file_id),
            data=data
        )
        if response.status_code != 204:
            self.error('Failed to execute uploading file content', response)
        return response

    def patch_resumable_file(self, file_id, **kwargs):
        """ Patch the specified resumable file.

        Other parameters refer to gen_creation_body(), which only accept:
            "parentID", "mimeType", "name", "mTime", "cTime", "hidden".
        REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#patch-resumable-file 
        """
        self.log.info('Patch resumable file')
        response = self.bearer_request(
            method='POST',
            url='{0}/sdk/v2/files/{1}/resumable/patch'.format(self.url_prefix, file_id),
            data=json.dumps(self.gen_body_metadata(**kwargs))
        )
        if response.status_code != 204:
            self.error('Failed to execute patch resumable files.', response)
        return response

    def patch_file(self, file_id, **kwargs):
        """ Patch the specified file.

        Other parameters refer to gen_creation_body(), which only accept:
            "parentID", "mimeType", "name", "mTime", "cTime", "hidden".
        REF: http://build-docs.wdmv.wdc.com/docs/restsdk.html#patch-file
        """
        self.log.info('Patch file')
        response = self.bearer_request(
            method='POST',
            url='{0}/sdk/v2/files/{1}/patch'.format(self.url_prefix, file_id),
            data=json.dumps(self.gen_body_metadata(**kwargs))
        )
        if response.status_code != 204:
            self.error('Failed to execute patch files.', response)
        return response

    def upload_file(self, file_name, file_object, resolve_name_conflict=False, chunk_size=1024, timeout=120, **kwargs):
        """ Two steps upload a file with generator to reduce memory loading (One chuck).

        :param file_object: A file object or readable object.
        """
        file_id = self.create_resumable_file(file_name, resolve_name_conflict, timeout=timeout, **kwargs)
        if not file_id:
            return None
        self.upload_resumable_file_content(file_id=file_id, data=read_in_chunks(file_object, chunk_size), done=True, timeout=timeout)
        return file_id

    def chuck_upload_file(self, file_object, file_name=None, file_id=None, start_offset=0, raise_error=True,
            resolve_name_conflict=False, upload_chunk_size=1024*1024*2, read_chunk_size=1024*2, timeout=120,
            set_global_timeout=True, parent_folder=None, **kwargs):
        """ Upload a file with generator chuck by chuck. This way is the same as Android APP (chuck size: 2MB).

        :param file_object: A file object or readable object.
        :param file_name: File name of new upload data on box.
        :param file_id: File ID of the existing resumable file.
        :param start_offset: File start offset for uploading. New upload should be 0.
        :param raise_error: Raise ChuckUploadFailed exception when it is True.
        :param upload_chunk_size: Chunk size for uploading. Android APP is 2 MB.
        :param read_chunk_size: Chunk size for read from file to reduce memory loading.
        """
        self.log.debug('Chuck upload file: {} ...'.format(file_name if file_name else file_id))
        # Hot fix for timeout not work for uploading.
        if set_global_timeout:
            self.set_global_timeout(timeout)
        # Estimate file offset.
        file_object.seek(0, 2) # Seek to end of file.
        end_position = file_object.tell()
        file_object.seek(start_offset, 0) # Seek to start_offset.
        upload_offset = end_position - start_offset
        self.log.debug('[Estimate file] start_offset:{}, end_position: {}, upload_offset:{}'.format(start_offset, end_position, upload_offset))

        try:
            if file_name: # Create file record if gieven file name.
                try:
                    try:
                        self.reduce_log = True
                        file_id = self.create_resumable_file(file_name, resolve_name_conflict=resolve_name_conflict, parent_folder=parent_folder, timeout=timeout, **kwargs)
                    finally:
                        self.reduce_log = False
                    if not file_id:
                        return None, None
                except Exception as e:
                    self.log.exception(e)
                    if raise_error:
                        raise RestAPI.ChuckUploadFailed('Create file failed', file_name=file_name, parent_id=kwargs.get('parent_id'), exception=e)
                    return file_name, None # TODOL How to know this value is name or ID.
            # Start to upload file content.
            idx = 0
            while upload_offset > 0:
                idx += 1
                # Move offset.
                start_upload_offset = start_offset if idx == 1 else end_upload_offset
                if upload_offset > upload_chunk_size:
                    upload_offset -= upload_chunk_size
                    end_upload_offset = start_upload_offset + upload_chunk_size
                    file_commit = False
                else:
                    upload_offset = 0
                    end_upload_offset = end_position
                    file_commit = True
                self.log.debug('[Upload chuck #{}] start_upload_offset: {}, end_upload_offset:{}'.format(idx, start_upload_offset, end_upload_offset))
                try:
                    try:
                        self.reduce_log = True
                        self.upload_resumable_file_content(
                            file_id=file_id, offset=start_upload_offset, done=file_commit,
                            data=partial_read_in_chunks(file_object, start_upload_offset, end_upload_offset, read_chunk_size),
                            timeout=timeout
                        )
                    finally:
                        self.reduce_log = False
                except Exception as e:
                    self.log.exception(e)
                    if raise_error:
                        raise RestAPI.ChuckUploadFailed('Chuck upload failed', file_id, start_upload_offset, parent_id=kwargs.get('parent_id'), exception=e)
                    return file_id, start_upload_offset
            return file_id, None
        finally:
            if set_global_timeout:
                self.reset_global_timeout()

    def recursive_upload(self, path, parent_id='root', chunk_size=1024*2, **kwargs):
        """ Upload entire specified folder or upload specified file.
        """
        name = os.path.basename(path)
        if os.path.isdir(path):
            # Upload folder.
            folder_id = self.create_folder(name, parent_id=parent_id)
            # Upload all data in this folder.
            for root, dirs, files in os.walk(path):
                # Upload all files.
                for file_name in files:
                    file_path = '{}/{}'.format(path, file_name)
                    #self.upload_file(file_name=file_name, file_object=open(file_path), chunk_size=chunk_size, parent_id=folder_id, **kwargs)
                    self.chuck_upload_file(file_object=open(file_path), file_name=file_name,  parent_id=folder_id,
                        read_chunk_size=chunk_size, set_global_timeout=False, **kwargs)
                # Upload all folders.
                for dir_name in dirs:
                    dir_path = '{}/{}'.format(path, dir_name)
                    self.recursive_upload(path=dir_path, parent_id=folder_id, chunk_size=chunk_size, **kwargs)
                break # one level
        elif os.path.isfile(path):
            self.chuck_upload_file(file_object=open(path), file_name=name, read_chunk_size=chunk_size, set_global_timeout=False, **kwargs)
            #self.upload_file(file_name=name, file_object=open(path), chunk_size=chunk_size, parent_id=parent_id, **kwargs)


    def share_file(self, file_id, owner_id=None, user_id_to_share='anybody', permission='ReadFile', prefix_type='proxy'):
        """ Share one file and return its cache URL and access token. 

        :param file_id: String. File ID to share.
        :param owner_id: String. Owner ID of the shared file.
        :param user_id_to_share: String or ID list. To users to share. Ref to create_shares().
        :param permission: String. File acccess permission for this share. Ref to set_permission().
        """
        # Consider onwer is caller if owner_id is not supplied..
        if not owner_id:
            owner_id = self.get_user_id()
        self.log.info('Sharing file: file_id={0}, owner_id={1}, user_id_to_share={2}, permission={3}'.format(
            file_id, owner_id, user_id_to_share, permission))
        # 1. Create share.
        share_id = self.create_shares(owner_id, user_id_to_share, file_id)
        # 2. Get share details by share ID. 
        resp = self.get_shares(share_id)
        self.log.debug('Get share details with {0}: {1}'.format(share_id, resp))
        # 3. Set file permission to NAS.
        share_details = resp['data']
        auth_id = share_details['authId']
        share_token = share_details['shareToken']
        device_id = share_details['deviceId']
        # file_id = share_details['fileIds'][0]
        try:
            cache_url = share_details["cacheUrl"] # "https://cache.mycloud.com/cache",
        except:
            cache_url = self.environment.get_cache_service()
        try:
            proxy_url = share_details["network"]["proxyURL"] # "https://dev1-proxy1.wdtest1.com:443/dc544edb-f13a-4bb9-8f3f-b4f39de6b3b6"
        except:
            proxy_url = '{0}/{1}'.format(self.environment.get_external_uri(), device_id)
        # port_forward_url = share_details["network"]["portForwardURL"] # Not sure how to get it.
        self.set_permission(file_id, user_id=auth_id, entity_type='cloudShare', permission=permission)
        # 4. Generate cache URL.
        #if prefix_type == 'proxy':
        prefix_url = proxy_url
        return {
            'access_token': share_token,
            'auth_id': auth_id,
            'cache_url': self.get_cache_url(cache_url=cache_url, device_id=device_id, file_id=file_id, prefix_url=prefix_url),
            'file_id': file_id,
            'owner_id': owner_id,
            'share_id': share_id,
            'proxy_url': proxy_url,
            'file_content_post_url': '/sdk/v2/files/{}/content'.format(file_id)
        }

    def share_file_by_name(self, file_name, parent_id='root', user_id_to_share='anybody', prefix_type='proxy'):
        """ Share file by searching file name and return its cache URL and access token.  """
        self.log.info('Sharing file by name: {0}'.format(file_name))
        item, elapsed_time = self.search_file_by_parent_and_name(name=file_name, parent_id=parent_id)
        owner_id = self.get_user_id()
        return self.share_file(file_id=item['id'], owner_id=owner_id, user_id_to_share=user_id_to_share, prefix_type='proxy')

    def get_cache_url(self, cache_url, device_id, file_id, prefix_url):
        # Assume the proxy URL is fixed or we have to take the URL from share detail.
        return '{0}/{1}/sdk/v2/files/{2}/content?prefix={3}'.format(
            cache_url, device_id, file_id, urllib.quote_plus(prefix_url)) # prefix_url need to do URL encode(From Spana).

    def get_content_from_cache(self, cache_url, access_token, allow_redirects=False, stream=True, timeout=None, auth_by_header=True):
        """ Return response object for verifying ED service behaviors with the specified cache_url
        and the specified access_token.

        :param allow_redirects: Boolean. To fellow redirect URL or not.
        :param stream: Boolean. Stream content or not. 
        """
        self.log.info('Getting content from cache.')
        headers = {}
        if auth_by_header:
            headers = {'Authorization': 'Bearer {0}'.format(access_token)}
        else:
            cache_url = '{}&access_token={}'.format(cache_url, access_token)
        response = self.send_request(
            method='GET',
            url=cache_url,
            headers=headers,
            allow_redirects=allow_redirects,
            stream=stream,
            timeout=timeout
        )
        return response

    def delete_content_from_cache(self, cache_url, access_token, auth_by_header=True):
        """ Return response object for verifying ED service behaviors with the specified cache_url
        and the specified access_token.
        """
        self.log.info('Deleting content from cache.')
        headers = {}
        if auth_by_header:
            headers = {'Authorization': 'Bearer {0}'.format(access_token)}
        else:
            cache_url = '{}&access_token={}'.format(cache_url, access_token)
        response = self.send_request(
            method='DELETE',
            url=cache_url,
            headers=headers
        )
        if response.status_code != 204:
            self.error('Failed to execute deteling cache content', response)
        return response

    def get_devices_info_per_specific_user(self, as_owner=True):
        """
            Get the Devices this User is attached to (APPROVED or PENDING_APPROVAL)

            Returns: deviceId, modelId, mac, name, cloudConnected in String format.
        """
        self.log.info('Getting devices info per specific user')

        if as_owner: # For the user who is not owner, he/she may cannot get information because not approved.
            request_inst = self.owner_bearer_request
        else:
            request_inst = self.bearer_request
        response = request_inst(
            method='GET',
            url="{0}/device/v1/user/{1}".format(self.environment.get_device_service(), self.get_user_id()),
        )
        if response.status_code == 200:
            self.log.info('Get devices info per specific user successfully')
            return response.json().get('data')
        else:
            self.error('Failed to devices info per specific user', response)

    def enable_pip(self):
        """ Enable PIP feature to upload device logs to sumologic.
        REF: http://build-docs.wdmv.wdc.com/docs/cloud.html#post-device-deviceid-agreement
        """
        self.log.info('Enable PIP...')
        device_id, _, _, _ = self.get_local_code_and_security_code()
        response = self.owner_bearer_request(
            method='POST',
            url='{}/device/v1/device/{}/agreement'.format(self.environment.get_device_service(), device_id),
            data=json.dumps([{
                "type": "pip",
                "accepted": True
            }])
        )
        if response.status_code != 200:
            self.error('Failed to enable PIP.', response)
        else:
            response = self.bearer_request(
                method='PUT',
                url='{}/authservice/v1/auth0/users/{}'.format(self.environment.get_device_service(), self.get_user_id()),
                data=json.dumps({
                    "user_metadata": {"client_pip_accepted": True}
                })
            )
            if response.status_code != 200:
                self.error('Failed to enable PIP.', response)

        return response

    def disable_pip(self):
        """ Disable PIP feature to upload device logs to sumologic. """
        self.log.info('Disable PIP...')
        device_id, _, _, _ = self.get_local_code_and_security_code()
        response = self.bearer_request(
            method='POST',
            url='{}/device/v1/device/{}/agreement'.format(self.environment.get_device_service(), device_id),
            data=json.dumps([{
                "type": "pip",
                "accepted": False
            }])
        )
        if response.status_code != 200:
            self.error('Failed to disable PIP.', response)
        else:
            response = self.bearer_request(
                method='PUT',
                url='{}/authservice/v1/auth0/users/{}'.format(self.environment.get_device_service(), self.get_user_id()),
                data=json.dumps({
                    "user_metadata": {"client_pip_accepted": False}
                })
            )
            if response.status_code != 200:
                self.error('Failed to disable PIP.', response)

        return response

    def get_external_ip_address(self, website=0):
        website_map = {
            0: ['http://ip.jsontest.com', lambda resp: resp.json()['ip']],
            1: ['https://www.myexternalip.com/json', lambda resp: resp.json()['ip']],
            2: ['https://api64.ipify.org?format=json', lambda resp: resp.json()['ip']],
            3: ['https://ipinfo.io', lambda resp: resp.json()['ip']],
            4: ['https://www.trackip.net/ip?json', lambda resp: resp.json()['IP']]
        }
        url, handler = website_map[website]
        self.log.debug('getting external ip in client...')
        resp = self.json_request(
            method='GET',
            url=url
        )
        if not resp or resp.status_code != 200:
            self.error("fail to get external ip address", resp)
        ip = handler(resp)
        self.log.info('External IP: ' + ip)
        return ip

    def get_localdevice_from_cloud(self, external_ip_address=None):
        self.log.info('Getting local devices from cloud...')

        if not external_ip_address: # from test client
            for itr in xrange(20):
                try:
                    external_ip_address = self.get_external_ip_address(itr)
                    break
                except Exception as e:
                    time.sleep(6)
                    self.log.info("#{} retrying to get external ip".format(itr))
            if not external_ip_address:
                raise RuntimeError("Cannot make the call without external ip")

        response = self.bearer_request(
            method='GET',
            url='{}/device/v1/localdevice'.format(GCS.get(self.env)),
            headers={'x-forwarded-for': external_ip_address}
        )
        if response.status_code != 200:
            self.error('Failed to make call', response)
        return response.json()

    def get_device_from_cloud(self, device_id=None):
        # Need owner token
        self.log.info('Getting device from cloud...')

        if not device_id:
            device_id = self.get_device_id()

        response = self.bearer_request(
            method='GET',
            url='{}/device/v1/device/{}'.format(GCS.get(self.env), device_id)
        )
        if not response or response.status_code != 200:
            self.error("Failed to get device from cloud", response)

        return response.json()

    def get_device_network_from_cloud(self, device_id=None):
        self.log.info('Getting device from cloud...')

        if not device_id:
            device_id = self.get_device_id()

        response = self.bearer_request(
            method='GET',
            url='{}/device/v1/device/{}/network'.format(GCS.get(self.env), device_id)
        )
        if not response or response.status_code != 200:
            self.error("Failed to get device network from cloud", response)

        return response.json()

    def bearer_request(self, method, url, set_corid=True, **kwargs):
        """ Send request with bearer headers. """
        access_token = self.get_id_token()
        headers = {
            'Authorization': 'Bearer {0}'.format(access_token)
        }
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        return self.json_request(method, url, set_corid, **kwargs)

    def owner_bearer_request(self, method, url, set_corid=True, **kwargs):
        """ Send request with bearer headers. """
        # TODO: refresh token
        access_token = self.owner_access_token
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {0}'.format(access_token)
        }
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        return self.json_request(method, url, set_corid, **kwargs)

    def admin_bearer_request(self, method, url, set_corid=True, **kwargs):
        """ Send request with admin bearer headers. """
        self.cloud.set_base_url(url=self.environment.get_auth_service())
        access_token = self.cloud.get_admin_token()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {0}'.format(access_token)
        }
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        return self.json_request(method, url, set_corid, **kwargs)

    def get_device_id(self):
        # self.device_id will be updated in get local code method
        if not self.device_id:
            self.get_local_code_and_security_code()

        return self.device_id

    def shutdown_device(self):
        """
            API "Reboot Device", the document link:
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#update-device

            Shutdown Device

            :return: Boolean
        """
        self.log.info("Shutdown device")
        id_token = self.get_id_token()
        url = "{0}/sdk/v1/device".format(self.url_prefix)
        time = self.get_local_code_and_security_code()[3]
        headers = {'Authorization': 'Bearer {0}'.format(id_token)}
        params = {"boot": {
                     "time": time,
                     "type": "shutdown"
                 }}
        result = requests.put(url, headers=headers, data=json.dumps(params))
        if result.status_code == 204:
            self.log.info('Shutdown API executing successfully')
            return True
        else:
            self.error('Failed to execute shutdown API: {0}, error message: {1}'.
                       format(result.status_code, result.content))

    def get_user_permission(self, user_id):
        self.log.debug('Getting user permission: {}'.format(user_id))
        response = self.admin_bearer_request(
            method='GET',
            url='{0}/sdk/v1/devicePermsSearch/granting?entityType=user&entityID={1}'.format(self.url_prefix, user_id)
        )
        if response.status_code != 200:
            self.error('Failed to execute get user permission', response)
        return response.json()

    def handle_app_install_status_502(self, app_name, proxy):
        """
            Handle 502 install status of app
        """
        self.log.debug('Handle 502 status for install/uninstall app')
        while True:
            self.log.debug('Now date time:{}'.datatime.now())
            response = self.owner_bearer_request(
                method='GET',
                url='https://{0}/sdk/v1/apps/{1}'.format(proxy, app_name)
            )
            self.log.debug('Status code: {}'.format(response.status_code))
            if response.status_code == 200:
                return
            time.sleep(5)

    def get_owner_devices_proxy_url(self):
        """
            Grabs devices proxy url that attached to specific user
        """
        self.log.debug("Getting Devices Proxy URL ...")
        data =  self.get_devices_info_per_specific_user()        
        dataList = []
        for i in data:
            dataList.append((i['name'], i['network']['proxyURL']))
        return dataList

    def get_owner_devices_ip(self):
        """
            Grabs devices IP that attached to specific user
        """
        self.log.debug("Getting Devices IP ...")
        data =  self.get_devices_info_per_specific_user()        
        dataList = []
        for i in data:
            if i['type'] != "wdcloud":
                dataList.append((i['name'], i['network']['internalURL']))
        return dataList

    def get_install_app_status(self, app_name):
        """
            Install status of app
        """
        response = self.owner_bearer_request(
            method='GET',
            url='{0}/sdk/v1/apps/{1}'.format(self.url_prefix, app_name),
            retry_times=0
        )
        if response.status_code >= 500:
            self.log.warning('Get install status response code is {}, do not send request again ...'.format(response.status_code))
            return response.status_code
        elif response.status_code == 404:
            self.log.warning('Get install status response code is {}, stop to get install app status ...'.format(response.status_code))
            return response.status_code
        else:
            start = response.text.find('port":')
            if (start != -1):
                start = start + 6
                end = response.text.find(',', start)
                if (int(response.text[start:end]) != 0):
                    return response.status_code
            return 'installing ...'

    def get_file_perms(self, file_id=None, as_owner=True):
        """
            GET /v1/filePermsSearch/granting
            GET /v1/filePermsSearch/granting?fileID=<id>
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#search-granting-file-permissions
        """
        self.log.info('Getting file perms of restsdk...')
        if as_owner: # For the user who is not owner, he/she may cannot get information because not approved.
            request_inst = self.owner_bearer_request
        else:
            request_inst = self.bearer_request
        url = "{}/sdk/v1/filePermsSearch/granting".format(self.url_prefix)
        if file_id:
            url += '?fileID={}'.format(file_id)
        response = request_inst(
            method='GET',
            url=url
        )
        if response.status_code == 200:
            return response.json()
        else:
            self.error('Failed to get file perms', response)

    def get_filesystem(self, filesystem_id=None, as_owner=True):
        """
            GET /v1/filesystems
            GET /v1/filesystem/<id>
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#get-filesystems
        """
        self.log.debug('Getting filesystems of restsdk...')
        if as_owner: # For the user who is not owner, he/she may cannot get information because not approved.
            request_inst = self.owner_bearer_request
        else:
            request_inst = self.bearer_request
        url = "{}/sdk/v1/filesystems".format(self.url_prefix)
        if filesystem_id:
            url += '/{}'.format(filesystem_id)
        response = request_inst(
            method='GET',
            url=url
        )
        if response.status_code == 200:
            self.log.debug('Get filesystem successfully')
            return response.json()
        else:
            self.error('Failed to get filesystem', response)

    def create_filesystem(self, folder_path=None, vol_id=None, name=None, as_owner=True):
        """
            POST /v1/filesystems
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#create-filesystem
        """
        self.log.info('Creating filesystems of restsdk...')
        if as_owner: # For the user who is not owner, he/she may cannot get information because not approved.
            request_inst = self.owner_bearer_request
        else:
            request_inst = self.bearer_request
        data = {}
        if folder_path: data['path'] = folder_path
        if vol_id: data['volID'] = vol_id
        if name: data['name'] = name
        response = request_inst(
            method='POST',
            url="{}/sdk/v1/filesystems".format(self.url_prefix),
            data=json.dumps(data)
        )
        if response.status_code == 201:
            self.log.info('Create filesystem successfully')
            return response.headers['Location'].rsplit('/').pop()
        elif response.status_code == 409:
            self.log.warning('The RestSDK filesystem has already been created, checking the filesystem ID')
            file_systems = self.get_filesystem()
            for fs in file_systems.get("filesystems"):
                if fs.get('path') == folder_path:
                    return fs.get('id')
            self.error("Cannot find any file system with path: {}!".format(folder_path))
        else:
            self.error('Failed to create filesystem', response)

    def delete_filesystem(self, filesystem_id=None, as_owner=True):
        """
            DELETE /v1/filesystems/id
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#delete-filesystem
        """
        self.log.info('Deleting filesystem_id [{}]...'.format(filesystem_id))
        if as_owner: # For the user who is not owner, he/she may cannot get information because not approved.
            request_inst = self.owner_bearer_request
        else:
            request_inst = self.bearer_request
        response = request_inst(
            method='DELETE',
            url="{}/sdk/v1/filesystems/{}".format(self.url_prefix, filesystem_id)
        )
        if response.status_code == 202:
            self.log.info('Delete filesystem successfully')
        elif response.status_code == 404:
            self.log.info('The filesystem_id:[{}] is not Found'.format(filesystem_id))
        else:
            self.error('Failed to delete filesystem', response)

    def get_filesystem_by(self, cmp_fs):
        result = self.get_filesystem()
        if 'filesystems' in result:
            for filesystem in result['filesystems']:
                if cmp_fs(filesystem):
                    return filesystem

    def get_volumes(self, filesystem_id=None, as_owner=True):
        """
            GET /v1/volumes
            GET /v1/volumes/<id>
            http://build-docs.wdmv.wdc.com/docs/restsdk.html#get-volumes
        """
        self.log.info('Getting volumes of restsdk...')
        if as_owner: # For the user who is not owner, he/she may cannot get information because not approved.
            request_inst = self.owner_bearer_request
        else:
            request_inst = self.bearer_request
        url = "{}/sdk/v1/volumes".format(self.url_prefix)
        if filesystem_id:
            url += '/{}'.format(filesystem_id)
        response = request_inst(
            method='GET',
            url=url
        )
        if response.status_code == 200:
            return response.json()
        else:
            self.error('Failed to get volumes', response)

    def get_volumes_by(self, cmp_vl):
        result = self.get_volumes()
        if 'volumes' in result:
            for volume in result['volumes']:
                if cmp_vl(volume):
                    return volume

    # ======================================================================================#
    #                                       KDP USE                                         #
    # ======================================================================================#

    def get_all_app_info_kdp(self):
        """
            Get KDP device app all info
        """
        response = self.bearer_request(
            method='GET',
            url='{}/sdk/v1/apps'.format(self.url_prefix)
        )
        if response.status_code != 200:
            self.error('Failed to get app list', response)
        else:
            return response.json()

    def get_app_info_kdp(self, app_id):
        """
            Get KDP device app info
        """
        response = self.bearer_request(
            method='GET',
            url='{0}/sdk/v1/apps/{1}'.format(self.url_prefix, app_id)
        )
        if response.status_code == 404:
            self.log.warning('Failed to get app info, err code: {}'.format(response.status_code))
            return response.status_code
        else:
            return response.json()

    def get_app_state_kdp(self, app_id):
        """
            Get app state
        """
        return self.get_app_info_kdp(app_id).get('state')

    def wait_for_app_install_completed(self, app_id, timeout=60*10, ignore_error=False):
        """
            Wait for app installation completed
        """
        self.log.debug('Wait App({}) installation completed ...'.format(app_id))
        start_time = time.time()
        while (timeout > time.time() - start_time):
            try:
                app_state = self.get_app_state_kdp(app_id)
            except Exception as e:
                if ignore_error:
                    app_state = None
                else:
                    raise
            if app_state != 'installed':
                self.log.info('App state: {} ...'.format(app_state))
                time.sleep(5)
            else:
                self.log.info('App state: {}, App install completed'.format(app_state))
                return True
        self.log.error("App installation failed !! The timeout is {} seconds, but app installation still doesn't complete.".format(timeout))
        return False

    def wait_for_app_uninstall_completed(self, app_id, timeout=60*2):
        """
            Wait for app uninstallation completed
        """
        self.log.debug('Wait App({}) uninstallation completed ...'.format(app_id))
        start_time = time.time()
        while (timeout > time.time() - start_time):
            app_state = self.get_app_state_kdp(app_id)
            if app_state != 'notInstalled':
                self.log.info('App state: {} ...'.format(app_state))
                time.sleep(2)
            else:
                self.log.info('App state: {}, App uninstall completed'.format(app_state))
                return True
        self.log.error("App uninstallation failed !!")
        return False

    def install_app_kdp(self, app_id, app_url=None, config_url=None, retry_times=None):
        """
            Install app to device from ECR
        """
        if app_url and config_url:
            params = {'downloadURL': app_url,
                      'configURL': config_url}
        else:
            params = ''
        self.log.info('{0} is installing app({1})...'.format(self.username, app_id))
        response = self.bearer_request(
            method='PUT',
            url='{0}/sdk/v1/apps/{1}'.format(self.url_prefix, app_id),
            params=params,
            retry_times=retry_times
        )
        if response.status_code == 204:
            self.log.info('Send install API for app({0}) succeed, status code: {1}'.format(app_id, response.status_code))
        elif response.status_code == 401:
            self.log.warning('User access token is unauthenticated')
        else:
            self.error('Failed to install app({}).'.format(app_id), response)
        return response.status_code

    def uninstall_app_kdp(self, app_id):
        """
            Uninstall app
        """
        self.log.info('{0} is uninstalling app({1})...'.format(self.username, app_id))
        response = self.bearer_request(
            method='DELETE',
            url='{0}/sdk/v1/apps/{1}'.format(self.url_prefix, app_id)
        )
        if response.status_code == 204:
            self.log.info('Send uninstall API for app({0}) succeed, status code: {1}'.format(app_id, response.status_code))
        elif response.status_code == 401:
            self.log.warning('User access token is unauthenticated')
        elif response.status_code == 404:
            self.log.info('The app({0}) is not found on device. status code: {1}'.format(app_id, response.status_code))
        else:
            self.error('Failed to delete app({}).'.format(app_id), response)
        return response.status_code

    def get_installed_app_id_kdp(self):
        installed_app_id = []
        app_list = self.get_installed_apps()
        for apps in app_list:
            if apps.get("state") == "installed":
                installed_app_id.append(apps.get("id"))
        return installed_app_id

    class ChuckUploadFailed(RuntimeError):

        def __init__(self, error_msg, file_id=None, start_offset=0, file_name=None, parent_id=None, exception=None):
            self.file_id = file_id
            self.file_name = file_name
            self.parent_id = parent_id
            self.start_offset = start_offset
            self.src_exception = exception
            RuntimeError.__init__(self, error_msg)


if __name__ == '__main__':
    print "### Running as a script, so running this code as a test ###\n"
    if len(sys.argv) < 2:
        print 'Please input the uut IP Address. ex. python restAPI.py 192.168.1.65'
        sys.exit(1)

    # Test device information
    uut_ip = sys.argv[1]
    email = 'wdctesttaurestapi01+qawdc@test.com'
    email2 = 'wdctesttaurestapi02+qawdc@test.com'
    password = 'Test1234'
    env = 'dev1'

    # Create User 1 & 2, and attach them in the test device
    rest_u1 = RestAPI(uut_ip, env, email, password)
    rest_u2 = RestAPI(uut_ip, env, email2, password)

    # Test to create folder/file in root folder and sub folder by User1(owner)
    rest_u1.upload_data(data_name='test_root_folder')
    rest_u1.upload_data(data_name='test_sub_folder', parent_folder='test_root_folder')
    rest_u1.upload_data(data_name='test_root_file.txt', file_content='Test upload file')
    rest_u1.upload_data(data_name='test_sub_file.txt', file_content='Test upload file', parent_folder='test_root_folder')

    # Test to set permission to User2, somebody, and anybody
    owner_id = rest_u1.get_user_id()
    user_id = rest_u2.get_user_id()

    # Test to reboot device
    # rest_u1.reboot_device()

    # Todo: Below tests need to be updated
    '''
    # Test to set folder permissions
    folder_id = rest_u1.get_data_id_list(type='folder', data_name='test_root_folder')
    rest_u1.set_permission(folder_id, user_id=user_id, permission="ReadFile")
    rest_u1.set_permission(folder_id, user_id=user_id, permission="WriteFile")
    rest_u1.set_permission(folder_id, user_id='somebody', permission="ReadFile")
    rest_u1.set_permission(folder_id, user_id='somebody', permission="WriteFile")
    rest_u1.set_permission(folder_id, user_id='anybody', permission="ReadFile")
    rest_u1.set_permission(folder_id, user_id='anybody', permission="WriteFile")

    # Test to get permission of test folder
    rest_u1.get_permission(folder_id)

    # Test to upload file share record to the cloud
    share_id = rest_u1.create_shares(owner_id, [owner_id, user_id], folder_id)
    print "Share ID: {}".format(share_id)

    # Test to get file share record from the cloud
    result = rest_u1.get_shares(share_id)
    print "Get folder share result:\n{}".format(result)

    # Test to set file permissions
    file_id = rest_u1.get_data_id_list(type='file', data_name='test_root_file.txt')
    rest_u1.set_permission(file_id, user_id=user_id, permission="ReadFile")
    rest_u1.set_permission(file_id, user_id=user_id, permission="WriteFile")
    rest_u1.set_permission(file_id, user_id='somebody', permission="ReadFile")
    rest_u1.set_permission(file_id, user_id='somebody', permission="WriteFile")
    rest_u1.set_permission(file_id, user_id='anybody', permission="ReadFile")
    rest_u1.set_permission(file_id, user_id='anybody', permission="WriteFile")

    # Test to get permission of test file
    rest_u1.get_permission(file_id)

    # Test to upload file share record to the cloud
    share_id = rest_u1.create_shares(owner_id, [owner_id, user_id], file_id)
    print "Share ID: {}".format(share_id)

    # Test to get file share record from the cloud
    result = rest_u1.get_shares(share_id)
    print "Get file share result:\n{}".format(result)

    # Test to set sub folder permissions
    root_folder_id = rest_u1.get_data_id_list(type='folder', data_name='test_root_folder')
    sub_folder_id = rest_u1.get_data_id_list(type='folder', parent_id=root_folder_id, data_name='test_sub_folder')
    rest_u1.set_permission(sub_folder_id, user_id=user_id, permission="ReadFile")
    rest_u1.set_permission(sub_folder_id, user_id=user_id, permission="WriteFile")
    '''