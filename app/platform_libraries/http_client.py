# -*- coding: utf-8 -*-
""" HTTP libraries.
"""
# std modules
import socket

# 3rd party modules
import requests

# platform modules
import common_utils
from platform_libraries.pyutils import log_request, log_response, retry


@common_utils.logger()
class HTTPRequester(object):

    def __init__(self, log_inst=None, buildin_debug=False, debug_request=True, debug_response=False, fixed_corid=None, default_timeout=60*5):
        
        if log_inst: self.log = log_inst
        
        self.session = requests.Session()
        self._persistent_connection = False

        self._default_global_timeout = default_timeout # For request hangs issue.
        self._global_timeout = self._default_global_timeout
        self._retry_times = 3
        self._retry_delay = 60
        self.set_global_timeout(default_timeout)
        self.debug_request = debug_request
        self.debug_response = debug_response
        self.fixed_corid = fixed_corid
        self.previous_response = None
        if buildin_debug:
            from httplib import HTTPConnection
            HTTPConnection.debuglevel = 1
        if not fixed_corid: self.render_correlation_id()
        self.reduce_log = False
        self.before_send_request = None

    def set_global_timeout(self, timeout):
        # Default value is None (never timeout).
        self.log.debug('Set global timeout: {}s'.format(timeout))
        socket.setdefaulttimeout(timeout)
        self._global_timeout = timeout

    def set_retry_delay(self, retry_delay=60):
        self.log.debug('Set retry delay of http request: {} seconds'.format(retry_delay))
        self._retry_delay = retry_delay

    def reset_global_timeout(self):
        self.log.debug('Re-Set global timeout: {}s'.format(self._default_global_timeout))
        socket.setdefaulttimeout(self._default_global_timeout)
        self._global_timeout = self._default_global_timeout

    def render_correlation_id(self):
        self.fixed_corid = common_utils.gen_correlation_id()
        self.log.debug('Render a new correlation id: {}'.format(self.fixed_corid))

    def increase_correlation_id(self):
        if '#' not in self.fixed_corid['x-correlation-id']: # Set default index.
            self.fixed_corid['x-correlation-id'] = self.fixed_corid['x-correlation-id'] + '#1'
        else: # Inrease requests index.
            cor_id, requests_idx = self.fixed_corid['x-correlation-id'].split('#')
            self.fixed_corid['x-correlation-id'] = cor_id + '#' + str(int(requests_idx)+1)

    def log_request(self, response, logger, debug_logger=None):
        log_request(response.request, logger, debug_logger, reduce_token=self.reduce_log)

    def log_response(self, response, logger, debug_logger=None, show_content=True):
        log_response(response, logger, debug_logger, show_content)

    def error(self, message, response=None):
        """
            Save the error log and raise Exception at the same time
            :param message: The error log to be saved
        """
        self.log.error(message)
        # Use it after all API send resquest by send_request() 
        #response = response or self.previous_response
        if isinstance(response, requests.Response):
            self.log_request(response, logger=self.log.error, debug_logger=self.log.debug)
            self.log_response(response, logger=self.log.error, debug_logger=self.log.debug)
            # raise requests.HTTPError() not return None(raise RuntimeError next line)
            response.raise_for_status()
        raise RuntimeError(message)

    def send_request(self, method, url, set_corid=True, retry_times=None, **kwargs):

        #  hook point before sending a request
        if self.before_send_request: self.before_send_request()

        def retry_check(response):
            # logging
            if self.debug_request: self.log_request(response, logger=self.log.debug, debug_logger=self.log.debug)
            if self.debug_response: self.log_response(response, logger=self.log.debug, debug_logger=self.log.debug)
            # Response checks
            if hasattr(response, 'status_code') and response.status_code < 500:
                # Additional checks for 401 issue on Kamino device.
                if response.status_code == 401 and hasattr(self, 'has_adb_client') and self.has_adb_client():
                    self.log.info('is_machine_time_correct: {}'.format(self._adb_client.is_machine_time_correct()))
                return False
            return True

        self.previous_response = None
        if set_corid:
            #cid_dict = common_utils.gen_correlation_id()
            self.increase_correlation_id()
            if not self.reduce_log: self.log.debug('Set x-correlation-id: {}'.format(self.fixed_corid['x-correlation-id']))
            if 'headers' in kwargs:
                kwargs['headers'].update(self.fixed_corid)
            else:
                kwargs['headers'] = self.fixed_corid
        if 'timeout' not in kwargs: # For request hangs issue.
            kwargs['timeout'] = self._global_timeout
        try:
            if self._persistent_connection:
                session_method_func = getattr(self.session, method.lower())
                response = retry( # Retry for it broken (status code >= 500 or no status code) by somehow
                                  # to decrease the issues devolers won't handle.
                    func=session_method_func, url=url,
                    excepts=(Exception), delay=self._retry_delay, max_retry=retry_times if isinstance(retry_times, int) else self._retry_times,
                    log=self.log.info, retry_lambda=retry_check, not_raise_error=True, **kwargs
                )
                
            else:  # Original requests.request
                response = retry( # Retry for it broken (status code >= 500 or no status code) by somehow
                                  # to decrease the issues devolers won't handle.
                    func=requests.request, method=method, url=url,
                    excepts=(Exception), delay=self._retry_delay, max_retry=retry_times if isinstance(retry_times, int) else self._retry_times,
                    log=self.log.info, retry_lambda=retry_check, not_raise_error=True, **kwargs
                )

        except Exception, e:
            self.log.debug('[Request Failure] {}'.format(e), exc_info=True)
            raise
        self.previous_response = response

        return response
        # TODO: Handle something here.

    def json_request(self, method, url, set_corid=True, **kwargs):
        """ Send request with Content-Type=application/json. """
        headers = {
            'Content-Type': 'application/json',
        }
        if 'headers' in kwargs and kwargs['headers']:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        return self.send_request(method, url, set_corid, **kwargs)
