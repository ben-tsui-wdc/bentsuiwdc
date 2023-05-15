# -*- coding: utf-8 -*-
""" Test Utils for KDP
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import json
# platform modules
from middleware.error import TestFailure
from platform_libraries.pyutils import PrintLogging
# 3rd party
import requests


# Data Providers

def read_lines_to_string(path):
    with open(path) as f:
        return f.read().splitlines()

def read_lines_to_dict(path):
    return [json.loads(l) for l in read_lines_to_string(path)]


# Test Executors

def get_log_from_test_method(test_method, inst_name='log', backup_log_inst=PrintLogging()):
    return getattr(test_method.im_self, inst_name, backup_log_inst)

def get_test_log(test_method, inst_name='log', backup_log_inst=None):
    inst = getattr(test_method.im_self, inst_name, backup_log_inst)
    if not inst:
        if not backup_log_inst:
            return PrintLogging()
        inst = backup_log_inst
    return inst

def run_test_with_data(test_data, test_method, execept_handler=None, finally_handler=None):
    """ Data driven util with given "test_data", all sub-tests are integrated as a single test.
    test_data: test data in a list. Each item in list will have a sub-test.
    """
    test_fails = []

    for idx, data in enumerate(test_data, 1):
        get_test_log(test_method).info('Started sub-test#{} with data: {}'.format(idx, data))
        try:
            test_method(data)
        except Exception as e:
            test_fails.append([idx, e])
            get_test_log(test_method).error('Got an error: {}'.format(e), exc_info=True)
            if execept_handler:
                no_raise_exec(execept_handler, get_log_from_test_method(test_method), e)
        finally:
            if finally_handler:
                no_raise_exec(finally_handler, get_log_from_test_method(test_method))
            get_test_log(test_method).info('Sub-test#{} is finished'.format(idx))

    if test_fails:
        msg = '\n' + '>' * 80 + '\n'
        for e in test_fails:
            msg += 'sub-test#{}:\n{}\n'.format(e[0], e[1])
        msg += '<' * 80
        raise TestFailure(msg)

def run_test_with_suit(test_suit, execept_handler=None, finally_handler=None):
    """ Data driven util with given "test_suit", all sub-tests are integrated as a single test.
    test_suit: (test_method, data_dict) or test_method in a list. Each item in list will have a sub-test.
    """
    test_fails = []

    for idx, subtest in enumerate(test_suit, 1):
        if not isinstance(subtest, tuple):
            test_method = subtest
            data_dict = {}
        else:
            test_method, data_dict = subtest
        get_test_log(test_method).info('Started sub-test#{} with data: {}'.format(idx, data_dict))
        try:
            test_method(**data_dict)
        except Exception as e:
            test_fails.append([idx, e])
            get_test_log(test_method).error('Got an error: {}'.format(e), exc_info=True)
            if execept_handler:
                no_raise_exec(execept_handler, get_log_from_test_method(test_method), e)
        finally:
            if finally_handler:
                no_raise_exec(finally_handler, get_log_from_test_method(test_method))
            get_test_log(test_method).info('Sub-test#{} is finished'.format(idx))

    if test_fails:
        msg = '\n' + '>' * 80 + '\n'
        for e in test_fails:
            msg += 'sub-test#{}:\n{}\n'.format(e[0], e[1])
        msg += '<' * 80
        raise TestFailure(msg)

def api_negative_test(test_method, data_dict, expect_status, pre_handler=None, finally_handler=None):
    try:
        if pre_handler: pre_handler()
        test_method(**data_dict)
        raise TestFailure('Success to perform the call which is not as expected')
    except requests.HTTPError as e:
        assert e.response.status_code == expect_status, 'Status code is {} not {}'.format(
            e.response.status_code, expect_status)
        get_test_log(test_method).info('Got {} status as expected'.format(expect_status))
    finally:
        if finally_handler:
            no_raise_exec(finally_handler, get_log_from_test_method(test_method))

def exec_filter(exec_list, filter_names):
    """ Filter given "exec_list" by given filter_names.
    exec_list: item can be ("method", ...) or "method" in a list.
    filter_names: can be a string or a string list.
    """
    if not filter_names:
        return exec_list

    output = []
    if isinstance(filter_names, str): # it's a string
        check_names = [filter_names]
    if not isinstance(filter_names, list):
        raise AssertionError('filter_names is not a string or a string list')
    else:
        check_names = filter_names

    for m in exec_list:
        method = m
        if isinstance(m, tuple): # expected method is at first idx
            method = m[0]
        if method.__name__ in check_names:
            output.append(m)
    return output


# Others

def no_raise_exec(func, log_inst=None, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_inst: log_inst.warning('Got an error: {}'.format(e), exc_info=True)
