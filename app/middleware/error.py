# -*- coding: utf-8 -*-
""" Exceptions of middleware. 
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import inspect
from collections import OrderedDict
# platform modules
from platform_libraries.constants import Test


class TestError(RuntimeError):
    """ Test failed is due to unexpected errors. """
    pass

class TestFailure(RuntimeError):
    """ An exception for test failed. """
    pass

class TestSkipped(RuntimeError):
    """ An exception for ignoring the test. """
    pass

class TestPass(RuntimeError):
    """ An exception for passing the test. """
    pass

class StopTest(RuntimeError):
    """ An exception for stopping the test. """
    pass


# For JUnit
JUNIT_MSG_FIELDS = ['error_message', 'error_output', 'failure_message', 'failure_output', 'skipped_message', 'skipped_output']


def get_junit_msg_key_from(dict_result):
    for key in JUNIT_MSG_FIELDS:
        if key in dict_result:
            return key
    return None

def status_mapping(exception):
    rules = OrderedDict([
        ((TestError, StopTest), Test.NOTEXCUTED),
        (TestFailure, Test.FAILED),
        (TestSkipped, Test.SKIPPED),
        (TestPass, Test.PASSED),
        (Exception, Test.FAILED)
    ])
    if inspect.isclass(exception):
        cehcker = issubclass
    else:
        cehcker = isinstance

    for rule, status in rules.iteritems():
        if cehcker(exception, rule):
            return status
    return None

def exception_mapping(status):
    return OrderedDict([
        (Test.PASSED, TestPass),
        (Test.FAILED, TestFailure),
        (Test.SKIPPED, TestSkipped),
        (Test.NOTEXCUTED, TestError) 
    ]).get(status)

def field_mapping(status):
    return OrderedDict([
        (Test.FAILED, 'failure_message'), # Failed
        (Test.SKIPPED, 'skipped_message'), # Skipped
        (Test.NOTEXCUTED, 'error_message')  # NotExecuted
    ]).get(status)
