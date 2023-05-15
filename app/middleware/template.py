# -*- coding: utf-8 -*-
""" Test Template is designed for single test scenario.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"


class TestCaseTemplate(object):
    """ Basic template for test case. """

    TEST_SUITE = None
    TEST_NAME = None
    SETTINGS = {} # Settings for __init__() of child class.

    def declare(self):
        """ Custom Declare Block

        Declare default attributes you need in test here.
        """
        pass

    def init(self):
        """ Custom Initiate Block

        Initiate anything you need in test here.
        """
        pass

    def run_test(self):
        """ Enterpoint of executing single round testing.

        [Execute Steps]
            before_test() -> test() -> after_test()
        """
        raise NotImplementedError('Implement it in child class.')

    def before_test(self):
        """ This block will auto executed BEFORE execute test().

        You may use this block to prepare environment for test. 
        """
        pass

    def test(self):
        """ Design test logic and overwrite this method. """
        raise NotImplementedError('Need to implement it in YOUR Test Case.')

    def after_test(self):
        """ This block will auto executed AFTER execute test().

        You may use this block to clean environment for test. 
        """
        pass

    def run_loop_test(self):
        """ Enterpoint of executing loop testing.

        [Execute Steps]
            before_loop() -> looping run_test() -> after_loop()
        """
        raise NotImplementedError('Implement it in child class.')

    def before_loop(self):
        """ This block will auto executed BEFORE looping run_test(). """
        pass

    def after_loop(self):
        """ This block will auto executed AFTER looping run_test(). """
        pass

    def main(self):
        """ Start testing with the given arguments.

        Invoke this method in __main__.
        """
        raise NotImplementedError('Implement me in child class.')

    def upload_result(self):
        """ This block will auto executed end of each iteration. """
        raise NotImplementedError('Optional implement it in YOUR Test Case.')

    def upload_loop_result(self):
        """ This block will auto executed end of iteration. """
        raise NotImplementedError('Optional implement it in YOUR Test Case.')
