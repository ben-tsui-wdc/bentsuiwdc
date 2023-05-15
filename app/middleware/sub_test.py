# -*- coding: utf-8 -*-
""" Implementation of Sub-Test.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# platform modules
from decorator import STATUS_STOP, sub_task_init, sub_task_test
from middleware.test_case import TestCase, Settings


# TODO: Need more case to validate.
class SubTest(TestCase):
    """ Superclass for Sub-Test. """

    SETTINGS = Settings(**{
        'disable_loop': False,
        'disable_firmware_consistency': False,
        'adb': True,
        'power_switch': True, 
        'uut_owner' : True,
        'init_stop_level': STATUS_STOP,
        'failure_status_mapping': []
    })

    def __init__(self, input_obj):
        self.declare()
        env = self.Environment()
        env.bind(testcase_inst=self)
        env.init_test_case(input_obj=input_obj)
        # Check previous test status.
        self.sub_test_init()

    def sub_test_init(self):
        @sub_task_init(stop_level=self.SETTINGS.get('init_stop_level', STATUS_STOP))
        def call(*args, **kwargs):
            self.init()
        call(self)

    def _run_test(self):
        @sub_task_test(mapping=self.SETTINGS.get('failure_status_mapping'))
        def call(*args, **kwargs):
            return super(SubTest, self)._run_test()
        return call(self)

    def _run_loop_test(self):
        @sub_task_test(mapping=self.SETTINGS.get('failure_status_mapping'))
        def call(*args, **kwargs):
            return super(SubTest, self)._run_loop_test()
        return call(self)
