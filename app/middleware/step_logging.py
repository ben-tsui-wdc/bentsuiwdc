# -*- coding: utf-8 -*-
""" Logging with test steps.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std models
import logging
import time
import traceback
from pprint import pformat
# platform modules
from platform_libraries.constants import Test
# middleware modules
import error


# Logging Level
TEST_STEP = 60
# Logging NAME
DISPLAY_NAME= '[TestStep]'


#
# Basic Structure Area
#
class TestStep(dict):
    """ Record for each step during test. """

    def __init__(self, **kwargs):
        info = {
            'index': None, # number
            # TODO: Should use a new filed like testcase to record all information instaed it?
            'iteration': None, # number
            'description': None, # string
            'messages': [], # string list
            'status': None, # string
            'exc_info': None, # tuple
            'start_time': None, # float
            'end_time': None # float
        }
        info.update(kwargs)
        super(TestStep, self).__init__(**info)

    def set_index(self, index):
        self['index'] = index

    def set_description(self, description):
        self['description'] = description

    def set_messages(self, messages):
        self['messages'] = messages

    def append_message(self, message):
        self['messages'].append(message + '\n')

    def set_status(self, status):
        self['status'] = status

    def set_exc_info(self, exc_info, overwrite=False):
        if self['exc_info'] and not overwrite: # Default we keep the first error.
            return
        self['exc_info'] = exc_info
        if exc_info: # Auto update messages/status.
            display_messages = traceback.format_exception(*exc_info)
            if self['messages']: # Move original message to end of message.
                display_messages = display_messages + self['messages']
            self.set_messages(display_messages)
            # Determine status by exception type.
            self.set_status(error.status_mapping(exc_info[1]))

    def set_start_time(self, start_time=None):
        self['start_time'] = start_time if start_time else time.time() 

    def set_end_time(self, end_time=None):
        self['end_time'] = end_time if end_time else time.time()

    def get_test_time(self):
        if self['end_time'] and self['start_time']:
            return self['end_time'] - self['start_time']
        return None

    def gen_err_msg(self):
        indent = '\n'
        traceback_indent = ' '*4
        try:
            msgs = indent + 'Index: {}'.format(self['index'])
            if self['iteration']:
                msgs += indent + 'Iteration: {}'.format(self['iteration'])
            if self.get_test_time():
                msgs += indent + 'Elapsed Time: {}'.format(self.get_test_time())
            msgs += indent + 'Description: {}'.format(self['description'])
            msgs += indent + 'Status: {}'.format(self['status'])
            if self['exc_info']:
                msgs += indent + 'Exception: {}'.format(repr(self['exc_info'][1]))
            msgs += indent + 'Error Messages: \n{}'.format(traceback_indent+traceback_indent.join(self['messages']))
            return msgs
        except:
            return str(self)

    def print_error(self, print_func=None):
        def print_msg(msg):
            if print_func:
                print_func(msg)
            else:
                print(msg)
        print_func(self.gen_err_msg())
        


class TestStepList(list):
    """ List for keep all test steps dirung test. """

    def __init__(self, *args, **kwargs):
        super(TestStepList, self).__init__(*args, **kwargs)
        self.index = None
        self.reset_index()

    def reset_index(self):
        self.index = 0

    def get_index(self):
        self.index += 1
        return self.index

    def sort_steps(self, reverse=False):
        self.sort(key=lambda step: step['index'], reverse=reverse)
        return self.sort

    def get_last_one(self):
        self.sort_steps()
        if not self:
            return None
        return self[-1]

    def get(self, index):
        for step in self:
            if step['index'] == index:
                return step
        return None


#
# Basic Utilities Area
#
def gen_init_warpper(init_method):
    # Wrapper __init__ method of logging.Logger.
    def __init__(self, *args, **kwargs):
        init_method(self, *args, **kwargs)
        self.test_steps = None
        self.reset_test_steps()
    return __init__


#
# Logging Hook Methods Area
#
def test_step(self, description, status=Test.PASSED, messages=None, *args, **kwargs):
    """ Logging method. """
    if self.isEnabledFor(TEST_STEP):
        test_step = TestStep(description=description, status=status, messages=messages if messages else [])
        self.append_test_step(test_step)
        self._log(TEST_STEP, description, args, **kwargs) 
        return test_step

def reset_test_steps(self):
    self.test_steps = TestStepList()

def append_test_step(self, test_step):
    # Set index.
    test_step.set_index(self.test_steps.get_index())
    # Set test time.
    now_time = time.time()
    test_step.set_start_time(start_time=now_time)
    last_one = self.test_steps.get_last_one()
    if last_one:
        last_one.set_end_time(end_time=now_time)
    # Append to test step list.
    self.test_steps.append(self.update_testcase_status_to(test_step))

def update_testcase_status_to(self, test_step):
    if not self.testcase:
        return test_step
    # Update TestCase status to TestStep.
    test_step['iteration'] = self.testcase.env.iteration
    return test_step

def print_test_steps(self):
    print 'Test Steps:\n', pformat(self.test_steps)

def gen_err_msg(self):
    errs = [t for t in self.test_steps if t.get('exc_info') or t.get('status') not in [Test.PASSED]]
    if not errs:
        return ''
    try:
        msg = 'Test Errors:\n'
        for err in errs:
            msg += err.gen_err_msg() + '\n'
        return msg
    except Exception, e:
        self.exception('Got an error: {}'.format(e))
        return 'Test Errors:\n{}'.format(pformat(errs))

def print_errors(self):
    msgs = self.gen_err_msg()
    if msgs:
        self.warning(msgs)


#
# Addtional features
#
def force_log(self, default_level, screen_level, description, *args, **kwargs):
    """ Logging method. """
    self._log(screen_level if screen_level > default_level else default_level, description, args, **kwargs) 


# Add TEST_STEP level to logging class.
logging.Logger.__init__ = gen_init_warpper(logging.Logger.__init__)
logging.Logger.TestStep = TestStep
logging.Logger.TestStepList = TestStepList
logging.Logger.test_step = test_step
logging.Logger.reset_test_steps = reset_test_steps
logging.Logger.append_test_step = append_test_step
logging.Logger.update_testcase_status_to = update_testcase_status_to
logging.Logger.print_test_steps = print_test_steps
logging.Logger.gen_err_msg = gen_err_msg
logging.Logger.print_errors = print_errors
logging.Logger.Test = Test
logging.Logger.force_log = force_log
logging.Logger.testcase = None # Supply a way to access testcase.
logging.addLevelName(TEST_STEP, DISPLAY_NAME)
