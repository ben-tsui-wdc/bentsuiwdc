# -*- coding: utf-8 -*-
""" Implementation of Test Template which contains common utilities.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import copy, datetime, logging, glob, subprocess, sys, os
from argparse import ArgumentParser, Namespace
from distutils.util import strtobool
from pprint import pformat
# platform modules
import platform_libraries.common_utils as common_utils
from platform_libraries.common_utils import create_logger, upload_logs, update_stream_handlers
from platform_libraries.constants import LOGSTASH_SERVER_TW
from platform_libraries.pyutils import ignore_unknown_codec, NoResult
# middleware modules
import middleware.error as error
from middleware.arguments import KeywordArguments
from middleware.component import ResultComponent, TimingComponent, UtilityManagement
from middleware.decorator import exit_test
from middleware.template import TestCaseTemplate


class Settings(dict):
    """ Preset settings for test case features. """

    def is_available(self, key, default=False):
        if key not in self:
            return self.get(key, default)
        value = self.get(key)
        if value: # Enable
            return value
        else: # Disable
            return default


class TestCase(TestCaseTemplate):
    """ Superclass for test case. """

    # For Popcorn
    PROJECT = None
    PLATFORM = None
    TEST_TYPE = None
    TEST_JIRA_ID = None
    PRIORITY = None
    COMPONENT = None
    FW_BUILD = None
    VERSION = None
    BUILD = None
    ISSUE_JIRA_ID = None
    ENVIROMENT = None
    USER = None
    OS_NAME = None
    OS_VERSION = None
    REPORT_NAME = None

    SETTINGS = Settings(**{ # Default flags for features, accept the changes if SETTINGS data supplied;
                 # For input arguments relative features, the key name is the same as input argument.
                 # Set True to Value means Enable this feature or Set True to this attribute as default value;
                 # Set False to Value means Disable this feature or Set False to this attribute as default value.
        'disable_loop': False,
        'always_do_after_test': True,
        'always_do_after_loop': True
    })

    def __init__(self, input_obj, keeper_list=None):
        """ Parse input_obj and init everything.

        [Argumensts]
            input_obj: Accept argparse.ArgumentParser, argparse.Namespace, TestCase or dict object.
            keeper_list: Hotfix to get testcase instance data when init failed.
        """
        if isinstance(keeper_list, list): keeper_list.append(self)
        try:
            self.declare()
            env = self.Environment() # FIXME if someone got better idea to compose these objects.
            if isinstance(keeper_list, list): keeper_list.append(env)
            env.bind(testcase_inst=self)
            env.init_test_case(input_obj=input_obj)
            # Custom initiation.
            self.init()
        except Exception, e:
            self.init_error_handle(e)
            raise

    @exit_test
    def run_test(self):
        self.log.force_log(logging.INFO, self.env.stream_log_level, '*** Start {}...'.format(self.TEST_NAME))
        test_result = self._run_test()
        self.log.force_log(logging.INFO, self.env.stream_log_level, '*** {} Is Done.'.format(self.TEST_NAME))
        return test_result

    def _run_test(self):
        """ Run single round test. """
        try:
            self.data.reset_test_result()   # Always reset test data before testing.
        except Exception,e:
            self.log.exception(e)
            raise
        try:
            self._before_single_test_steps()
            self._single_test_steps()
        except Exception, e:
            self.error_handler(e) # (Test failed) Error raised in this flow will auto update to test result.
            raise
        finally: # always do export file and upload result.
            self.data.test_result.summarize(print_out=False)
            if not self.env.disable_save_result: self.data.export_test_result()
            self._upload_test_result()
            if not self.env.disable_popcorn_report:
                self.data.gen_popcorn()
                self.data.export_test_result_as_popcorn()
                if not self.env.disable_upload_popcorn_report: self.data.upload_test_result_to_popcorn()
        return self.data.test_result

    def _single_test_steps(self):
        try:
            # Run before_test step.
            self.device_log('*** Start before_test()...')
            self.before_test()
            self.device_log('*** before_test() Is Done.')
            # Start timing
            self.timing.start()
            # Run test step.
            self.device_log('*** Start test()...')
            self.test()
            self.device_log('*** test() Is Done.')
        except Exception, e:
            self.env.log.warning('Catch Exception:\n{}'.format(e), exc_info=True) # To show message immediately.
            self.update_error_to_test_step() # (Not a test failed)
            raise
        finally:
            self.timing.finish() # Record time even it failed

            # Controllable Step: after_test.
            if self.env.always_do_after_test:
                self.device_log('*** Start after_test()...')
                try:
                    # Run after_test step.
                    self.after_test()
                except (self.err.TestError, self.err.TestFailure, self.err.TestSkipped, self.err.StopTest), e:
                    #self.error_handler(e) # (Test failed) Need more sample to verify it need or not.
                    self.update_error_to_test_step() # This exception may update to wrong test step, here we use "overwrite" flag to avoid issue.
                    raise # This raising may overwrite previous exception.
                except Exception, e:
                    self.env.log.warning('Error encountered during after_test(): {}'.format(e), exc_info=True)
                self.device_log('*** after_test() Is Done.')

    @exit_test
    def run_loop_test(self):
        self.log.force_log(logging.INFO, self.env.stream_log_level, '*** Start {}...'.format(self.TEST_NAME))
        try:
            self._run_loop_test()
        except Exception, e:
            self.loop_error_handler(e) # (Test failed) Error raised in this flow will auto update to test result.
            raise
        finally:
            self.data.loop_results.summarize(print_out=False)
             # always do export file.
            if not self.env.disable_save_result: self.data.export_loop_results()
            self._upload_loop_result()
            if not self.env.disable_popcorn_report: 
                self.data.export_loop_results_as_popcorn()
                if not self.env.disable_upload_popcorn_report: self.data.upload_loop_results_to_popcorn()
        self.log.force_log(logging.INFO, self.env.stream_log_level, '*** {} Is Done.'.format(self.TEST_NAME))
        return self.data.loop_results

    def _run_loop_test(self):
        """ Run loop test. """
        # Always reset loop results before testing.
        try:
            self.data.reset_loop_results()
        except Exception,e:
            self.log.exception(e)
            raise
        try:
            self.device_log('*** Start before_loop()...')
            self.before_loop()
            self.device_log('*** before_loop() Is Done.')
            # Start timing
            self.loop_timing.start_looping()
            for self.env.iteration in xrange(self.env.loop_times_from, self.env.loop_times+1):
                self.log.info('*** Start {0} Iteration #{1}...'.format(self.TEST_NAME, self.env.iteration))
                try:
                    self._before_single_iteration_steps()
                    self._single_iteration_steps()
                except Exception, e:
                    if not self.env.run_even_failure:
                        if not isinstance(e, self.err.TestSkipped):
                            raise
                    self.env.log.warning('[Looping] Catch Exception:\n{}'.format(e), exc_info=True) # To show message immediately.
                self.log.info('*** {0} Iteration #{1} Is Done.'.format(self.TEST_NAME, self.env.iteration))
        except Exception, e:
            self.update_error_to_test_step() # need one for looping?
            raise
        finally:
            self.loop_timing.finish_looping() # Record time even it failed

            if self.env.always_do_after_loop:
                self.device_log('*** Start after_loop()...')
                try:
                    self.after_loop()
                except (self.err.TestError, self.err.TestFailure, self.err.TestSkipped, self.err.StopTest), e:
                    self.update_error_to_test_step() # need one for looping?
                    raise
                except Exception, e:
                    self.env.log.warning('Error encountered during after_loop(): {}'.format(e), exc_info=True)
                self.device_log('*** after_loop() Is Done.')

    def _single_iteration_steps(self):
        try:
            self._run_test()
        finally: # always append test result.
            self.data.append_loop_result()
            self.finally_of_single_iteration()

    def main(self):
        self.log.info('>'*75)
        if self.env.is_looping():
            ret_val = self.run_loop_test()
            test_result = self.data.loop_results
        else:
            ret_val = self.run_test()
            test_result = self.data.test_result
        self.log.info('<'*75)
        self._end_of_test()
        test_pass = test_result.summarize(print_out=True)
        if test_pass is None:
            self.log.warning('{} Is SKIPPED.'.format(self.TEST_NAME))
            return None
        elif not test_pass:
            self.log.warning('{} Is FAILED.'.format(self.TEST_NAME))
            return False # Test failed caused by exception.
        self.log.warning('{} Is PASSED.'.format(self.TEST_NAME))
        return True

    def update_error_to_test_step(self):
        last_exc_info = sys.exc_info()
        if not last_exc_info:
            return
        last = self.log.test_steps.get_last_one()
        # XXX: Here we expect last one should not be an error of test does use TestStep.
        if not last or (last['exc_info'] and last['exc_info'][1] != last_exc_info[1]): # Handle for the same exception.
            # Generate a step to record this error.
            last = self.log.TestStep()
            self.log.append_test_step(last)
            # Update TestStep time by test time.
            if getattr(self, 'timing', None):
                if self.timing.start_time: last.set_start_time(start_time=self.timing.start_time)
                if self.timing.end_time: last.set_end_time(end_time=self.timing.end_time) # This time may update.
        last.set_exc_info(last_exc_info)

    def _end_of_test(self):
        # For monitor test step logs.
        #self.log.print_test_steps()
        if not self.env.disable_print_errors:
            self.log.print_errors()
        # Close all utilities if it needs.
        if not getattr(self, 'utils', None):
            return
        try:
            self.utils.close_utils()
        except Exception, e:
            self.env.log.warning('Closing utility: {}'.format(e), exc_info=True)
        
    def _upload_test_result(self):
        """ Use upload_result() only if it has been overridden. """
        self.data.print_test_result()
        if self.env.dry_run:
            return
        try:
            self.upload_result()
        except NotImplementedError: # Not implement upload_result().
            self.data.upload_test_result()

    def _upload_loop_result(self):
        if self.env.dry_run:
            return
        try:
            self.upload_loop_result()
        except NotImplementedError: # Not implement upload_loop_result().
            self.data.upload_loop_result()

    #
    # MiddleWare Hooks Area
    #
    def init_error_handle(self, exception):
        self.update_error_to_test_step()
        self.finally_of_exit_test()
        self._end_of_test()

    def error_handler(self, exception):
        return self.data.error_callback(exception)

    def loop_error_handler(self, exception):
        return self.data.loop_error_callback(exception)

    def finally_of_single_iteration(self):
        pass

    def finally_of_exit_test(self):
        # Behavior extendion after test exited.
        if self.env.disable_upload_logs:
            return
        try:
            self.upload_output_folders_server()
        except Exception, e:
            self.env.log.error(e, exc_info=True)

    # Add more extendion hooks if we need.
    def _before_single_test_steps(self):
        pass

    def _before_single_iteration_steps(self):
        pass

    def device_log(self, msg, force=False):
        # Log utility to print both on local consloe and device.
        if force:
            self.log.force_log(logging.INFO, self.env.stream_log_level, msg)
        else:
            self.log.info(msg)

    # Upload logs.
    def upload_output_folders_server(self):
        target_path = self.gen_target_path()
        # Upload all the folder which name start with "output".
        self.env.log.info('Upload logs to remote path: {}'.format(target_path))
        self.env.log.debug('Check logs size...')
        try:
            # Estamte total size, compress files if it is too large.
            du = subprocess.Popen(['bash', '-c', 'du -sm {}*'.format(self.env.output_folder)], stdout=subprocess.PIPE)
            p = subprocess.Popen(['awk', '{ total += $1 }; END { print total }'], stdin=du.stdout, stdout=subprocess.PIPE)
            stdout = p.communicate()[0].strip()
            if stdout.isdigit(): self.env.log.debug('Log total size: {} MB'.format(stdout))
            if int(stdout) >= 100: # Compress logs if large then 100 MB.
                self._upload_compressed_logs(target_path)
                return
        except Exception, e:
            self.env.log.warning(e, exc_info=True)
            self.env.log.warning('Trying to upload file by file...')
        # Even upload compressed logs failed, it will retry to upload file by file again.
        try:
            self._upload_logs(target_path)
        except Exception, e: # Final retry with compressed logs.
            self.env.log.warning(e, exc_info=True)
            self.env.log.warning('Final retry to upload with compressed logs...')
            self._upload_compressed_logs(target_path)

    def _upload_compressed_logs(self, target_path):
        self.env.log.debug('Compress logs to {}.tgz...'.format(self.env.output_folder))
        subprocess.check_output(["tar cvzf {0}.tgz {0}*".format(self.env.output_folder)], shell=True)
        self.env.log.debug('Upload compressed logs...')
        upload_logs(output_path=self.env.output_folder+'.tgz', target_path=target_path)

    def _upload_logs(self, target_path):
        self.env.log.debug('Upload logs...')
        for output_folder in glob.glob('{}*'.format(self.env.output_folder)):
            self.env.log.info('Upload folder {}...'.format(output_folder))
            try:
                upload_logs(output_path=output_folder, target_path=target_path)
            except Exception, e:
                self.env.log.warning(e, exc_info=True)

    def gen_target_path(self):
        return '{}/{}'.format(
            self.TEST_SUITE if self.TEST_SUITE else 'Unknown',
            datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')
        )


    class Environment(object):
        """ Initiate all attributes which TestCase use here. """

        EXPORT_FILED = '_testcase'

        def bind(self, testcase_inst):
            """ Bind Environment instance to TestCase instance. """
            testcase_inst.env = self
            self.testcase = testcase_inst

        def input_parse(self, input_obj):
            """ Accept ArgumentParser, Namespace, TestCase or dict object. """
            # ArgumentParser -> Namespace
            if isinstance(input_obj, ArgumentParser):
                input_obj = vars(input_obj.parse_args())
            # Namespace -> dict
            if isinstance(input_obj, Namespace):
                input_obj = vars(input_obj)
            # TestCase -> dict
            if isinstance(input_obj, TestCase):
                input_obj = input_obj.env.dump_to_dict()
            return KeywordArguments(input_obj) # Note Here! Use KeywordArguments to preprocessing input arguments.

        def init_test_case(self, input_obj):
            """ Initiate Environment and the TestCase instance which already binded.

            For consistency, put all variables in Environment instance as far as possible; only the attributes
            like the utilities are designed for child class can put in TestCase instance.
            """
            kwargs = self.input_parse(input_obj)
            # Init Steps.
            self.init_logging(kwargs=kwargs) # Init logging first to make sure all the feature can print debug message.
            self.load_settings(kwargs=kwargs)
            self.check_test_name(kwargs=kwargs)
            self.init_flow_variables(of_inst=self, kwargs=kwargs)
            self.init_variables(of_inst=self, kwargs=kwargs)
            self.init_popcorn_variables(of_inst=self.testcase, kwargs=kwargs)
            self.init_components(of_inst=self.testcase, kwargs=kwargs)
            self.init_utilities(of_inst=self.testcase, kwargs=kwargs)
            self.post_init(of_inst=self, kwargs=kwargs)
            self.run_hook(kwargs=kwargs)
            self.init_custom_variables(of_inst=self.testcase, kwargs=kwargs)
            self.print_debug_message()

        def init_logging(self, kwargs):
            # Set default steam level and affact to the following new loggers.
            common_utils.STREAM_LOG_LEVEL = kwargs.get('stream_log_level')
            # Update @logger class logs.
            update_stream_handlers()
            # Init logging for Environment.
            log_inst = create_logger(log_name='middleware', stream_log_level=common_utils.STREAM_LOG_LEVEL)
            self.log = copy.copy(log_inst) # Copy it for TestStep feature in the same name test.
            self.log.testcase = self.testcase # bind testcase.
            self.log.reset_test_steps()
            # Init logging for TestCase.
            kwargs.get('log') # Add access record.
            log_inst = create_logger(
                log_name=self.testcase.__class__.__name__, stream_log_level=common_utils.STREAM_LOG_LEVEL
            )
            self.testcase.log = copy.copy(log_inst) # Copy it for TestStep feature in the same name test.
            self.testcase.log.testcase = self.testcase # bind testcase.
            self.testcase.log.reset_test_steps()

        def check_test_name(self, kwargs):
            custom_TEST_SUITE = kwargs.get('TEST_SUITE')
            custom_TEST_NAME = kwargs.get('TEST_NAME')
            # Replace values if it supplied.
            # Replace all unknown char by "_".
            if custom_TEST_SUITE:
                self.testcase.TEST_SUITE = ignore_unknown_codec(custom_TEST_SUITE)
            if custom_TEST_NAME:
                self.testcase.TEST_NAME = ignore_unknown_codec(custom_TEST_NAME)
            if not self.testcase.TEST_SUITE:
                raise ValueError('TEST_SUITE is not supplied.')
            if not self.testcase.TEST_NAME:
                raise ValueError('TEST_NAME is not supplied.')

        def load_settings(self, kwargs):
            # Merge child's settings to parent settings.
            settings = Settings(**TestCase.SETTINGS) # Load default settings.
            self._extend_hook_of_load_child_settings(settings, kwargs) # Load child settings.
            settings.update(self.testcase.SETTINGS) # Load settings from test.
            settings.update(self.parse_input_settings(kwargs)) # Load settings from command line.
            self.testcase.SETTINGS = settings

        def _extend_hook_of_load_child_settings(self, settings, kwargs):
            """ This method we want to update class's default Settings which are between Core Test Case and test case you'r running.
            """
            parents = self.testcase.__class__.__bases__
            if not parents:
                return
            # Recusive update all child's settings.
            parents_to_update = []
            while parents:
                # Trace parent class
                focus_parents = parents
                parents = []
                for parent in focus_parents:
                    if parent == TestCase:
                        continue
                    # Only choose the FIRST ordering child's settings.
                    if hasattr(parent, 'SETTINGS'):
                        parents = parent.__bases__ # Once we have a parent calss, then fellow its parent.
                        parents_to_update.append(parent)
                        break

            # Update all setting in list from top to down.
            # Here we expect class: Product test case (e.g. Kamino), Existing test case (When we reuse by inheriting)
            for cls in parents_to_update[::-1]:
                settings.update(cls.SETTINGS)

        def parse_input_settings(self, kwargs):
            input_list = kwargs.get('Settings')
            settings = {}
            if not input_list:
                return settings
            for pair in input_list:
                try:
                    name, flag = pair.split('=')
                    settings[name] = True if strtobool(flag) else False
                except:
                    self.log.warning('Expected string format is like "adb=False"')
                    raise
            return settings

        def init_flow_variables(self, of_inst, kwargs):
            """ Initiate variables for bulitin testing flow. """
            target_inst = of_inst
            target_inst.iteration = 0 # Record current test iteration.
            target_inst.is_subtask = kwargs.has_key(self.EXPORT_FILED) # Input data include EXPORT_FILED.
            target_inst.always_do_after_test = self.testcase.SETTINGS.get('always_do_after_test', True)
            target_inst.always_do_after_loop = self.testcase.SETTINGS.get('always_do_after_loop', True)
            target_inst.disable_loop = self.testcase.SETTINGS.get('disable_loop', False) # (NOT IN input args) Control flag to disable loop test.
            target_inst.disable_upload_logs = kwargs.get('disable_upload_logs', False) # Control flag to not upload output folder to server.
            target_inst.disable_save_result = kwargs.get('disable_save_result', False) # Control flag to not save test result to file.
            target_inst.disable_print_errors = kwargs.get('disable_print_errors', False) # Control flag to not print test errors at end of tests.
            target_inst.debug_middleware = kwargs.get('debug_middleware') # Control flag to print debug message of middleware.
            target_inst.dry_run = kwargs.get('dry_run') # Control flag to upload test result to logstash.
            target_inst.stream_log_level = kwargs.get('stream_log_level') # Log level for all libraries.
            target_inst.run_even_failure = kwargs.get('run_even_failure') # Control flag to keep runnig looping test.
            
        def init_variables(self, of_inst, kwargs):
            """ Initiate common variables """
            target_inst = of_inst
            # UUT and Test settings
            target_inst.logstash_server_url = kwargs.get('logstash_server_url') or LOGSTASH_SERVER_TW
            target_inst.loop_times = kwargs.get('loop_times')
            target_inst.loop_times_from = kwargs.get('loop_times_from', 1)
            # Folder Paths
            target_inst.results_folder = kwargs.get('results_folder') or 'output/results'
            target_inst.output_folder = kwargs.get('output_folder') or 'output'

        def init_popcorn_variables(self, of_inst, kwargs):
            """ Initiate Popcorn variables """
            target_inst = of_inst
            target_inst.env.disable_popcorn_report = kwargs.get('disable_popcorn_report', False)
            target_inst.env.disable_upload_popcorn_report = kwargs.get('disable_upload_popcorn_report', False)
            target_inst.env.popcorn_skip_error = kwargs.get('popcorn_skip_error', False)
            if kwargs.get('popcorn_project'): target_inst.PROJECT = kwargs.get('popcorn_project')
            if kwargs.get('popcorn_platform'): target_inst.PLATFORM = kwargs.get('popcorn_platform')
            if kwargs.get('popcorn_test_type'): target_inst.TEST_TYPE = kwargs.get('popcorn_test_type')
            if kwargs.get('popcorn_test_jira_id'): target_inst.TEST_JIRA_ID = kwargs.get('popcorn_test_jira_id')
            if kwargs.get('popcorn_priority'): target_inst.PRIORITY = kwargs.get('popcorn_priority')
            if kwargs.get('popcorn_component'): target_inst.COMPONENT = kwargs.get('popcorn_component')
            if kwargs.get('popcorn_version'): target_inst.VERSION = kwargs.get('popcorn_version')
            if kwargs.get('popcorn_build'): target_inst.BUILD = kwargs.get('popcorn_build')
            if kwargs.get('popcorn_fwbuild'): target_inst.FW_BUILD = kwargs.get('popcorn_fwbuild')
            if kwargs.get('popcorn_issue_jira_id'): target_inst.ISSUE_JIRA_ID = kwargs.get('popcorn_issue_jira_id')
            if kwargs.get('popcorn_enviroment'): target_inst.ENVIROMENT = kwargs.get('popcorn_enviroment')
            if kwargs.get('popcorn_user'): target_inst.USER = kwargs.get('popcorn_user')
            if kwargs.get('popcorn_os_name'): target_inst.OS_NAME = kwargs.get('popcorn_os_name')
            if kwargs.get('popcorn_os_version'): target_inst.OS_VERSION = kwargs.get('popcorn_os_version')
            if kwargs.get('popcorn_source'): target_inst.POPCORN_SOURCE = kwargs.get('popcorn_source')
            if kwargs.get('popcorn_report_name'): target_inst.REPORT_NAME = kwargs.get('popcorn_report_name')
            target_inst.BUILD_URL = kwargs.get('popcorn_build_url') or os.environ.get('BUILD_URL')

        def init_components(self, of_inst, kwargs):
            """ Initiate components """
            target_inst = of_inst
            target_inst.ext = None
            target_inst.data = ResultComponent(testcase_inst=self.testcase)
            target_inst.loop_timing = TimingComponent(testcase_inst=self.testcase) if self.is_looping() else None
            target_inst.timing = TimingComponent(testcase_inst=self.testcase)
            target_inst.uut = None
            # share 'utils' for keeping update/close methods.
            if self.is_subtask and kwargs.get(self.EXPORT_FILED):
                target_inst.utils = kwargs[self.EXPORT_FILED].utils
            else:
                target_inst.utils = UtilityManagement(testcase_inst=self.testcase)

            # Experimental feature.
            if self.is_subtask: # binding share space
                target_inst.share = getattr(kwargs.get(self.EXPORT_FILED), 'share', None)
            else:
                target_inst.share = dict()

        def init_utilities(self, of_inst, kwargs):
            """ Initiate common utilities """
            target_inst = of_inst
            target_inst.err = error
            if self.is_subtask:
                self._init_utilities_with_testcase(target_inst, kwargs.get(self.EXPORT_FILED), kwargs)
            else:
                self._init_utilities(target_inst, kwargs)

        def _init_utilities(self, target_inst, kwargs):
            """ Create utilities if it needs. """
            pass

        def _init_utilities_with_testcase(self, target_inst, testcase, kwargs):
            """ Use the utilities of the given testcase instance instead of creating new one.
                If the given instance does not create utility, then just create one for it, and re.
            """
            pass

        def post_init(self, of_inst, kwargs):
            """ Initiate anything which need to do after all initiations done. """
            target_inst = of_inst

        def init_custom_variables(self, of_inst, kwargs):
            args_dict = kwargs.gen_unused_dict()
            for k, v in args_dict.iteritems():
                setattr(of_inst, k, v)

        def run_hook(self, kwargs):
            """ Initiate Block Of Child Class """
            pass

        def dump_to_dict(self):
            """ Dump attributes to a dict object which can pass into input_parse(). """
            # Collect Environment attributes, remove unused attributes data from dict.
            settings = vars(self).copy()
            settings.pop('disable_upload_logs', None) # Sub-tests don't need to upload.
            settings.pop('iteration', None)
            settings.pop('is_subtask', None)
            settings.pop('always_do_after_test', None)
            settings.pop('always_do_after_loop', None)
            settings.pop('loop_times', None) # Not share loop_times
            settings.pop('loop_times_from', None) # Not share loop_times_from
            settings.pop('testcase', None)
            # To share data to other test case.
            settings[self.EXPORT_FILED] = self.testcase
            self._extend_hook_of_dump_to_dict(settings)
            return settings

        # Extend hook for dump_to_dict().
        def _extend_hook_of_dump_to_dict(self, settings):
            pass

        def print_debug_message(self):
            if not self.debug_middleware:
                return
            self.log.info('#'*75)
            self.log.info("TEST_SUITE={0} TEST_NAMES={1}".format(self.testcase.TEST_SUITE, self.testcase.TEST_NAME))
            self.log.info("Environment Attributes: \n{}".format(pformat(vars(self))))
            self.log.info("Test Case Attributes: \n{}".format(pformat(vars(self.testcase))))
            self.log.info('#'*75)

        def is_looping(self):
            return not self.disable_loop and self.loop_times
