# -*- coding: utf-8 -*-
""" Collection of useful python utilities.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

import logging
import os
import json
import string
import time
import traceback
import types
import re
from pprint import pformat

import requests


class Singleton(type):
    """ The metaclass for Singleton pattern. """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


#
# Replacement Class
#
class NotSet(object):
    """ The replacement of assigning None object to argument. """
    pass

class NoResult(object):
    """ The replacement of returning None object. """
    pass


#
# Utilities
#
def save_to_file(iter_obj, file_name):
    """ Read data from "iter_obj" and save content to "file_name":

    [Arguments]
        iter_obj: Iterator object
            Data source iterator.
        file_name: String
            The file save path.
    """
    try:
        with open(file_name, 'wb') as f:
            for chunk in iter_obj:
                if chunk:
                    f.write(chunk)
    except:
        if os.path.exists(file_name):
            os.remove(file_name)
        raise

def rename_duplicate_filename(file_name, end_with_extension=False):
    if not os.path.exists(file_name):
        return file_name

    # Keep file ext.
    ext = ''
    if end_with_extension and '.' in file_name:
        file_name, _, ext = file_name.rpartition('.')

    # Find idx number.
    current_idx = 0
    if '.' in file_name:
        tmp_name, _, check_idx = file_name.rpartition('.')
        if check_idx.isdigit():
            file_name = tmp_name
            current_idx = int(check_idx)

    # Increase idx number.
    file_name = '{}.{}'.format(file_name, current_idx+1)

    # Add file ext.
    if ext:
        file_name = '{}.{}'.format(file_name, ext)

    return rename_duplicate_filename(file_name, end_with_extension)

def read_in_chunks(file_object, chunk_size=1024*512):
    """Lazy function (generator) to read a file piece by piece.
    Default chunk size: 512k.
    """
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data

def partial_read_in_chunks(file_object, start_position, end_position, chunk_size=1024*512):
    """Lazy function (generator) to read a file piece by piece with start position and end position.
    Default chunk size: 512k.
    """
    read_offset = end_position - start_position
    while read_offset > 0:
        if read_offset > chunk_size:
            read_chunk = chunk_size
            read_offset -= chunk_size
        else:
            read_chunk = read_offset
            read_offset = 0
        yield file_object.read(read_chunk)

def ignore_unknown_codec(string):
    """ Convert the given string to base string, and replace the unknown codec char by "_". """
    convert_string = []
    for ch in string:
        try:
            '{}'.format(ch)
        except:
            convert_string.append('_')
        else:
            convert_string.append(str(ch))
    return ''.join(convert_string)

def retry(func, excepts=None, retry_lambda=NotSet, delay=30, max_retry=20, log=None, not_raise_error=False, *args, **kwargs):
    """ Retry the specified function. 

    [Arguments]
        retry_lambda: lambda function
            Retry func only if this function return True. Will pass return value of func to this function.
    """
    if not excepts:
        excepts = (RuntimeError)

    retry_times = 0
    while True:
        raised_custom_error = False
        ret = None
        try:
            ret = func(*args, **kwargs)
            if retry_lambda is not NotSet:
                if retry_lambda(ret):
                    raised_custom_error = True
                    raise RuntimeError('Response is not expected, value is: {}'.format(ret))
            return ret
        except excepts as e:
            # Just raise exception if retry count is max.
            if max_retry == retry_times:
                if not_raise_error and raised_custom_error:
                    return ret
                raise
            # Increase retry times.
            retry_times += 1
            # log it if log function is specified.
            if not log:
                continue
            if isinstance(e, requests.exceptions.RequestException):
                log('Catch a requests exception: {}{}'.format(e, ', the call is' if hasattr(e, 'request') or hasattr(e, 'response') else ''))
                if hasattr(e, 'request'): log_request(e.request, log)
                if hasattr(e, 'response'): log_response(e.response, log)
            else:
                log('Catch exception:', exc_info=True)
            log('Execute #{}, retry it after {} sec.'.format(retry_times, delay))
            log('.'*75)
            # delay retry...
            time.sleep(delay)


#
# Request Tool Area
#
def log_request(request, logger, debug_logger=None, reduce_token=False):
    if not debug_logger: debug_logger=logger
    logger('HTTP Request:')
    logger('* Method : {}'.format(request.method))
    logger('* URL    : {}'.format(request.url))
    try:
        if hasattr(request, 'body') and request.body:
            try: # Print whole string if it is JSON string.
                json.loads(request.body)
                debug_logger('* Body   : {}'.format(request.body))
            except ValueError:
                if 512 > len(request.body):
                    debug_logger('* Body   : {}'.format(request.body))
    except:
        pass
    if reduce_token:
        log_header = dict(request.headers)
        if 'Authorization' in log_header:
            log_header['Authorization'] = "*" + log_header['Authorization'][7:12] + "*" + log_header['Authorization'][-5:]
        debug_logger('* Headers: \n{}'.format(pformat(log_header)))
    else:
        debug_logger('* Headers: \n{}'.format(pformat(request.headers)))

def log_response(response, logger, debug_logger=None, show_content=True):
    if not debug_logger: debug_logger=logger
    logger('HTTP Response:')
    logger('* Status Code : {}'.format(getattr(response, 'status_code', '')))
    if show_content:
        try:
            if hasattr(response, 'content') and response.content:
                try: # Print whole string if it is JSON string.
                    json.loads(response.content)
                    debug_logger('* Content: {}'.format(response.content))
                except ValueError:
                    if 512 > len(response.content):
                        debug_logger('* Content: {}'.format(response.content))
        except:
            pass
    
    debug_logger('* Reason : {}'.format(getattr(response, 'reason', '')))
    debug_logger('* Headers: \n{}'.format(pformat(getattr(response, 'headers', ''))))
    if hasattr(response, 'elapsed'):
        logger('* Seconds: {}'.format(response.elapsed.total_seconds()))


#
# String Utilities Area
#
# Porting from AAT project
def decode_unicode_args(func):
    def _decode_unicode_args(*args, **kwargs):
        """
        Decorator to decode Unicode arguments into ASCII.
        """
        args = list(args)
        temp_args = list(args)
        for i, arg in enumerate(temp_args):
            if type(arg) == types.UnicodeType:
                try:
                    PrintLogging.debug('Encoding {0} as ASCII'.format(arg))
                    args[i] = arg.encode('ascii', 'ignore')
                except UnicodeDecodeError:
                    traceback.print_exc()
        temp_kwargs = dict(kwargs)
        for key, arg in temp_kwargs.items():
            if type(arg) == types.UnicodeType:
                try:
                    PrintLogging.debug('Encoding {0} as ASCII'.format(arg))
                    kwargs[key] = arg.encode('ascii', 'ignore')
                except UnicodeDecodeError:
                    traceback.print_exc()
        return func(*args, **kwargs)
    return _decode_unicode_args


printable = string.ascii_letters + string.digits + string.punctuation + string.whitespace


@decode_unicode_args
def hex_escape(s):
    return ''.join(c if c in printable else r'\x{0:02x}'.format(ord(c)) for c in s)


@decode_unicode_args
def escape(s):
    return ''.join(c if c in printable else '' for c in s)

@decode_unicode_args
def replace_escape_sequence(string, show_hex=False):
    """Delete Linux control codes from serial output."""
    # replace unicode escape, followed by formatting (used by Linux
    # to format console output)
    if show_hex:
        string = hex_escape(string)
    else:
        string = escape(string)
    re1 = re.compile('(.)(\\[)(\\?)?(\\d+)([a-z])', re.IGNORECASE | re.DOTALL)
    re2 = re.compile('(.)(\\[)(\\d+)(;)(\\d+)([a-z])', re.IGNORECASE | re.DOTALL)
    string = re1.sub('', string)
    return re2.sub('', string).strip().replace('\r', '')


# Sample logging tool.
class PrintLogging(object):

    def __init__(self, level=logging.NOTSET, name=None):
        self.setLevel(level)
        self.name = None

    def setLevel(self, level):
        self.level = level

    def log(self, level, msg, tag='INFO', exc_info=False):
        if level < self.level:
            return
        if exc_info:
            traceback.print_exc()
        print '{0: <10} {1}'.format(tag, msg)

    def debug(self, msg, exc_info=False):
        self.log(logging.DEBUG, msg, 'DEBUG', exc_info)

    def info(self, msg, exc_info=False):
        self.log(logging.INFO, msg, 'INFO', exc_info)

    def warning(self, msg, exc_info=False):
        self.log(logging.WARNING, msg, 'WARNING', exc_info)

    def error(self, msg, exc_info=False):
        self.log(logging.ERROR, msg, 'ERROR', exc_info)

    def critical(self, msg, exc_info=False):
        self.log(logging.CRITICAL, msg, 'CRITICAL', exc_info)
