# -*- coding: utf-8 -*-

# std modules
from pprint import pformat

# platform modules
from constants import GlobalConfigService as GCS
from constants import ClientID, ClientSecret


class ServiceEnvironment(object):

    env_sets = {} # Will be updated by update_service_urls().
    # Need to set up default clientId/clientSecret.

    def __init__(self, env_name, env_version=None, client_id=None, client_secret=None, http_requester=None):
        if not env_name:
            self.env_name = 'dev1'
        else:
            self.env_name = env_name

        self.current_env = self.env_sets[self.env_name]

        if client_id:
            self.current_env['client_id'] = client_id
        if client_secret:
            self.current_env['client_secret'] = client_secret

        self.gen_env().set_http_requester(http_requester) # for support old code.
        self.env_version = env_version # Version of service URLs.

    def url_mapping(self, url_dict):
        # Update all to self.current_env
        return url_dict

    def set_http_requester(self, http_requester):
        self.http_requester = http_requester
        return self

    def gen_env(self):
        if self.env_name not in self.env_sets:
            self.env_sets[self.env_name] = {}
        return self

    def get_env_name(self):
        return self.env_name

    def get(self, key):
        return self.current_env.get(key)

    def set(self, key, value):
        return self.current_env.set(key, value)

    def get_client_id(self):
        return self.get('client_id')

    def get_client_secret(self):
        return self.get('client_secret')

    def update_service_urls(self, client_settings=None, env_version=None):
        """
            Update self.env_sets with response from GCS.
            :param client_settings: A set of parameters of get_configuration() in dict.
        """
        self.env_version = env_version
        if self.env_name in ['dev2', 'qa2']: # This is for config V2.
            feature_version = 'v2'
        else:
            feature_version = 'v1'
        if not client_settings:
            client_settings = {}
        urls = get_service_urls(self.http_requester, self.env_name, feature_version, **client_settings)
        self.current_env.update(self.url_mapping(urls))
        self.http_requester.log.info('Updated service configuration:\n{}'.format(pformat(self.current_env)))

    def get_service_urls(self, client_settings=None, env_version=None, client_type='app', client_sub_type='mobile', **kwargs):
        self.env_version = env_version
        if self.env_name in ['dev2', 'qa2']: # This is for config V2.
            feature_version = 'v2'
        else:
            feature_version = 'v1'
        if not client_settings:
            client_settings = {}
        return get_service_configuration(self.http_requester, env=self.env_name, feature_version=feature_version,
            client_type=client_type, client_sub_type=client_sub_type, **kwargs)


class RestEnvironment(ServiceEnvironment):

    env_sets = {
        "dev1": {
                "externalURI": "https://dev1-proxy1.wdtest1.com:443", # deprecated
                "cacheService": "https://cache.wdtest2.com/cache", # deprecated
                "client_id": ClientID.DEV1.MOBILE_APP,
                "client_secret": ClientSecret.DEV1.MOBILE_APP
        },
        "dev2":  {
                "client_id": ClientID.DEV2.MOBILE_APP,
                "client_secret": ClientSecret.DEV2.MOBILE_APP
        },
        "qa1":  {
                "externalURI": "https://qa1-proxy1.wdtest2.com:443", # deprecated
                "cacheService": "https://cache.wdtest1.com/cache", # deprecated
                "client_id": ClientID.QA1.MOBILE_APP,
                "client_secret": ClientSecret.QA1.MOBILE_APP
        },
        "qa2":  {
                "client_id": ClientID.QA2.MOBILE_APP,
                "client_secret": ClientSecret.QA2.MOBILE_APP
        },
        "prod": {
                "externalURI": "https://i-042ccc2815c8b6bde.mycloud.com:443", # deprecated
                "cacheService": "https://cache.mycloud.com/cache", # deprecated
                "client_id": ClientID.PROD.MOBILE_APP,
                "client_secret": ClientSecret.PROD.MOBILE_APP
        }
    }

    def url_mapping(self, url_dict):
        return {
            "authService": url_dict["service.auth0.url"],
            "authServiceSignUp": url_dict["service.auth.url"],
            "deviceService": url_dict["service.device.url"],
            "shareService": url_dict["service.share.url"],
            "configService": url_dict["service.config.url"],
            "appService": url_dict["service.appcatalog.url"]
        }

    def get_auth_service(self):
        return self.get('authService')

    def get_auth_service_sign_up(self):
        return self.get('authServiceSignUp')

    def get_device_service(self):
        return self.get('deviceService')

    def get_share_service(self):
        return self.get('shareService')

    def get_config_service(self):
        return self.get('configService')
 
    def get_external_uri(self): # deprecated
        return self.get('externalURI')

    def get_cache_service(self): # deprecated
        return self.get('cacheService')


class CloudEnvironment(ServiceEnvironment):

    env_sets = {
        "dev1": {
                "client_id": ClientID.DEV1.AUTOMATION,
                "client_secret": ClientSecret.DEV1.AUTOMATION
        },
        "qa1":  {
                "client_id": ClientID.QA1.AUTOMATION,
                "client_secret": ClientSecret.QA1.AUTOMATION
        },
        "prod": {
                "client_id": ClientID.PROD.RSDK_TEST,
                "client_secret": ClientSecret.PROD.RSDK_TEST
        }
    }

    def url_mapping(self, url_dict):
        return {
            "service.config.url": url_dict["service.config.url"],
            "service.device.url": url_dict["service.device.url"],
            "service.appcatalog.url": url_dict["service.appcatalog.url"],
            "service.m2m.url": url_dict["service.m2m.url"],
            "service.ota.url": url_dict["service.ota.url"],
            "service.auth.url": url_dict["service.auth.url"]
        }


#
# Tools Area
#


def get_service_configuration(http_requester, env, env_version=None, feature_version='v1', device_id=None, configuration_id=None,
        client_type=None, client_sub_type=None, fw_version=None, authorization=None, config_url=None):
    """
        Get configuration from GCS.
        :param env: Type of environment.
        :param env_version: version of environment.
        :param feature_version: "v1" or "v2" in url path.
        :param device_id: Specify device ID to find configuration.
        :param configuration_id: Specify configuration ID to get configuration.
        :param client_type: Specify client type to find configuration.
        :param client_sub_type: Specify client sub type to find configuration.
        :param fw_version: Specify fw version to find configuration.
        :param authorization: Specify authorization to find configuration.
    """
    http_requester.log.debug('Getting service configuration...')
    # Handle paramters
    params = []
    if device_id: params.append('deviceId={}'.format(device_id))
    if configuration_id: params.append('configurationId={}'.format(configuration_id))
    if client_type: params.append('clienttype={}'.format(client_type))
    if client_sub_type: params.append('clientSubType={}'.format(client_sub_type))
    if fw_version: params.append('fwVersion={}'.format(fw_version))
    params_str = '?' + '&'.join(params) if params else ''
    # Send request.
    response = http_requester.json_request(
        method='GET',
        url='{}/config/{}/config{}'.format(config_url if config_url else GCS.get(env, version=env_version), feature_version, params_str),
        headers={'Authorization': authorization} if authorization else {}
    )       
    if response.status_code != 200:
        http_requester.error('Get service configuration failed', response)
    http_requester.log.debug('Get service configuration successfully')
    return response.json()

def get_service_urls(http_requester, env, feature_version, client_type='app', client_sub_type='mobile', **kwargs):
    """
        Get service URLs for update.
        :param: refer to get_service_configuration().
    """
    r = get_service_configuration(http_requester, env=env, feature_version=feature_version, client_type=client_type,
            client_sub_type=client_sub_type, **kwargs)
    return r['data']['componentMap']["cloud.service.urls"]

