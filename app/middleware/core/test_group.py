# -*- coding: utf-8 -*-
""" Implementation of Test Group Cehck.
"""

# std modules
import types
# middleware modules
import middleware.error as error


#
# Golbal Utilities
#
def get_groups(group_list):
    all_tg = []
    for tg in group_list:
        all_tg += tg
    return all_tg

def raise_if_test_group_matched(testcases, subtest):
    """ For now only support the first check.
    TODO: Continue test result check.
    """
    # Check test result from Front to End.
    for testcase in testcases:
        if not testcase['instance']:
            continue
        # Check group rules from Front to End.
        for group in subtest['group']:
            if group.detect(testcase):
                # Raise exception.
                group.trigger(testcase)

def gen_display_message(testcase, exception):
    return "Since {}'s result' is {}, Test is {}".format(testcase['instance'].TEST_NAME, testcase['pass'], error.status_mapping(exception))

#
# Test Group Classes
#
class TestGroup(list):

    def __init__(self, group_names, trigger_method, detect_method):
        super(TestGroup, self).__init__(group_names)
        # Hook method
        self.trigger = types.MethodType(trigger_method, self) # for raising exception to generate dummy test case.
        self.detect = types.MethodType(detect_method, self) # for check test group rules.

    def match(self, other):
        # Is there any group name mached?
        return True if set(self).intersection(other) else False

class PassGroup(TestGroup):

    def __init__(self, group_names):
        super(PassGroup, self).__init__(group_names, pass_trigger, pass_detect)

class ErrorGroup(TestGroup):

    def __init__(self, group_names):
        super(ErrorGroup, self).__init__(group_names, error_trigger, failed_detect)

class FailedGroup(TestGroup):

    def __init__(self, group_names):
        super(FailedGroup, self).__init__(group_names, failed_trigger, failed_detect)

class SkipGroup(TestGroup):

    def __init__(self, group_names):
        super(SkipGroup, self).__init__(group_names, skip_trigger, failed_detect)

#
# Hook methods
#
def pass_trigger(self, testcase):
    raise error.TestPass(gen_display_message(testcase, error.TestPass))

def error_trigger(self, testcase):
    raise error.TestError(gen_display_message(testcase, error.TestError))

def failed_trigger(self, testcase):
    raise error.TestFailure(gen_display_message(testcase, error.TestFailure))

def skip_trigger(self, testcase):
    raise error.TestSkipped(gen_display_message(testcase, error.TestSkipped))

def pass_detect(self, subtest):
    if not subtest['pass']:
        return False
    if not self.match(get_groups(subtest['group'])):
        return False
    return True

def failed_detect(self, subtest):
    if subtest['pass']:
        return False
    if not self.match(get_groups(subtest['group'])):
        return False
    return True
