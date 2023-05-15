# -*- coding: utf-8 -*-
""" Decorator tools for Test Case. 
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import time
# platform modules
from platform_libraries.constants import Test
from platform_libraries.pyutils import NoResult


def elapsed_time(field):
    """ Measure the elapsed time of specified class method.
    Auto assign the time to "field" field of self.test_result. 
    """
    def time_decorator(test_method):
        def elapsed_time_wrapper(self, *args, **kwargs):
            # Measure elapsed time.
            start_time = time.time()
            ret_val = test_method(self, *args, **kwargs)
            # Update time to test result data.
            self.data.test_result[field] = time.time() - start_time
            return ret_val
        return elapsed_time_wrapper
    return time_decorator

def record_result(field):
    """ Auto assign return value of specified class method to "field" field of self.test_result. """
    def result_decorator(test_method):
        def record_result_wrapper(self, *args, **kwargs):
            ret_val = test_method(self, *args, **kwargs)
            # Update value to test result.
            self.data.test_result[field] = ret_val
            return ret_val
        return record_result_wrapper
    return result_decorator

def pass_by_retval(field, pass_str=Test.PASSED, fail_str=Test.FAILED):
    """ Auto assign "pass_str" or "fail_str" to "field" field according by return value. """
    def pass_decorator(test_method):
        def pass_by_retval_wrapper(self, *args, **kwargs):
            try:
                ret_val = test_method(self, *args, **kwargs)
                self.data.test_result[field] = pass_str if ret_val else fail_str
            except:
                self.data.test_result[field] = fail_str
                raise
            return ret_val
        return pass_by_retval_wrapper
    return pass_decorator

def error_handle(error_handler_name='error_handler', finally_handler_name='finally_handler', reraise=True):
    """ Decorator for Try-Except-Finally block. 

    [Arguments]
        error_handler: string
            Method name of exception block handler. Find method on the same level of "self".
        finally_handler: string
            Method name of finally block handler. Find method on the same level of "self".
    """
    def error_decorator(test_method):
        error_name = error_handler_name
        finally_name = finally_handler_name
        is_reraise = reraise
        def error_handle_wrapper(self, *args, **kwargs):
            try:
                return test_method(self, *args, **kwargs)
            except Exception, e:
                error_handler = getattr(self, error_name, None)
                if error_handler:
                    error_handler(e)
                if is_reraise:
                    raise
            finally:
                finally_handler = getattr(self, finally_name, None)
                if finally_handler:
                    finally_handler()
        return error_handle_wrapper
    return error_decorator

def exit_test(method):
    """ Exit test behaviors.

    [Returns]
        Return NoResult object if it catch any Exception, or just return response of wraped method.
    """
    def exit_test_wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except:
            self.env.log.exception('Last One Exception During Testing:')
            return NoResult
        finally: 
            self.finally_of_exit_test()
    return exit_test_wrapper


#
# Sub-Task Decorator Tools
#
SUB_TASK_STATUS = '_sub_tast'
STATUS_SUCCESS, STATUS_NOT_EXECUTE, STATUS_FAILED, STATUS_STOP, STATUS_DO_INIT, NOT_STOP = xrange(6)


def sub_task_init(stop_level=STATUS_STOP):
    """ Check status before run test.
    
    [Arguments]
        stop_level: int
            Stop this test if there has any previous test status is equal or bigger than the given value. 
    """
    def init_decorator(init_method):
        sl = stop_level
        def init_wrapper(self, *args, **kwargs):
            if SUB_TASK_STATUS in self.share:
                status_value = self.share[SUB_TASK_STATUS]
                if status_value == STATUS_DO_INIT: # A solution to do something when previous test is failed.
                    if not hasattr(self, '_init_call'):
                        raise self.err.StopTest('No _init_call function found.')
                    self._init_call()
                    self.share[SUB_TASK_STATUS] = None
                elif status_value >= sl:
                    raise self.err.StopTest('Not execute due to previous sub-task status: {} (Stop Level: {})'.format(status_value, sl))
            else: # Default value
                self.share[SUB_TASK_STATUS] = None

            return init_method(self, *args, **kwargs)
        return init_wrapper
    return init_decorator

def sub_task_test(mapping=None, reset=False):
    """ Update test status for the next test. 

    [Arguments]
        mapping: list
            Exception class-status value pairs list.
            Example: [(ValueError, STATUS_FAILED), (Exception, STATUS_STOP)]
    """
    def test_decorator(test_method):
        # Default behavior: Just update itself status to STATUS_FAILED if catch any exception.
        do_reset = reset
        mp = mapping
        if not mp or not isinstance(mp, list):
            mp = [(Exception, STATUS_FAILED)]
        def test_wrapper(self, *args, **kwargs):
            try:
                ret = test_method(self, *args, **kwargs)
                if do_reset or not SUB_TASK_STATUS in self.share:
                    self.share[SUB_TASK_STATUS] = STATUS_SUCCESS
                return ret
            except Exception, e: 
                previous_status = self.share.get(SUB_TASK_STATUS, STATUS_SUCCESS) 
                for err_obj, status_value in mp:
                    if isinstance(e, err_obj) and status_value > previous_status:
                        self.log.warning('Set SUB_TASK_STATUS to {}.'.format(status_value))
                        self.share[SUB_TASK_STATUS] = status_value
                        raise
        return test_wrapper
    return test_decorator
