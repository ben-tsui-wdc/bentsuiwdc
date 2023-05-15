# -*- coding: utf-8 -*-
""" Implementation of Integration Extensions.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
from pprint import pformat
# platform modules
from platform_libraries.pyutils import ignore_unknown_codec, NoResult
from platform_libraries.test_result import ELKTestResult, IntegrationResult, IntegrationLoopingResult
from platform_libraries.junit_xml import TestSuite
# middleware modules
import test_group as TG
import middleware.dummy_case as dummy_case
import middleware.error as error
from middleware.component import TestCaseComponent, ResultComponent
from mtbf import choice_generator, gen_testcases, unique_choice_generator, group_generator
from test_case import Settings, TestCase


class IntegrationExtensions(object):
    """ Superclass for integration method extensions. """

    INTEGRATION_SETTINGS = Settings(**{
    })

    def _run_test(self):
        """ Steps of run single round test. """
        self.data.reset_test_result()
        try:
            self.device_log('*** Start Integration:before_test()...')
            self.before_test()
            self.device_log('*** Integration:before_test() Is Done.')
            self.timing.start()
            self.device_log('*** Start Integration:test()...')
            self.test()
            self.device_log('*** Integration:test() Is Done.')
        finally:
            self.timing.finish()

            # Controllable Step: after_test.
            if self.env.always_do_after_test:
                self.device_log('*** Start Integration:after_test()...')
                try:
                    self.after_test()
                except (self.err.TestError, self.err.TestFailure, self.err.TestSkipped, self.err.StopTest):
                    raise
                except Exception, e:
                    self.env.log.warning('Error encountered during after_test(): {}'.format(e), exc_info=True)
                self.device_log('*** Integration:after_test() Is Done.')

            self.data.test_result.summarize(print_out=True)
             # always do after_test and export file.
            if not self.env.disable_save_result: self.data.export_test_result()
            self._upload_test_result()
            if not self.env.disable_popcorn_report: 
                self.data.export_test_result_as_popcorn()
                if not self.env.disable_upload_popcorn_report: self.data.upload_test_result_to_popcorn()
        return self.data.test_result

    def test(self):
        """ IntegrationTest supply test() as default.
        
        Execute each sub-test and handle test response.
        """
        def _gen_testcases():
            if self.env.choice: # Return choice_generator and run sequential.
                testcases = gen_testcases(choice_generator(self.integration.source_testcases, self.env.choice))
            elif self.env.unique_choice:
                testcases = gen_testcases(unique_choice_generator(self.integration.source_testcases, self.env.unique_choice))
            else: # Return original testcases and run sequential.
                testcases = self.integration.source_testcases
            # Add the group test cases back to self.integration.source_testcases
            if self.env.exec_group:
                testcases = group_generator(testcases, self.integration.original_source_testcases, self.env.exec_group)


            self.log.warning("final TestCase {}".format('*'*40))
            for item in testcases:
                print item
                print '\n'
            self.log.warning("final TestCase {}".format('*'*40))



            return [SubTestCase(tc) for tc in testcases] # Shallow copy for each item to make sure have unique log instance.

        # Custom execute ordering.
        if self.env.exec_ordering:
            self.integration.source_testcases = [self.integration.source_testcases[idx] for idx in self.env.exec_ordering]

        # Customize the group test case
        if self.env.exec_group:
            self.integration.adjusted_testcases = []
            self.integration.group_case_idx = []
            self.integration.original_source_testcases = []
            for group in self.env.exec_group.split():
                for idx in eval(group):
                    self.integration.group_case_idx.append(idx)
            for idx, testcase in enumerate(self.integration.source_testcases):
                # Keep the original_source_testcase
                self.integration.original_source_testcases.append(testcase)
                # Pick up the test case which DOESN'T belong to group
                if idx not in self.integration.group_case_idx:
                    self.integration.adjusted_testcases.append(self.integration.source_testcases[idx])
            self.integration.source_testcases = self.integration.adjusted_testcases

        # MTBF featute.
        self.integration.set_testcases(_gen_testcases())

        for self.env.subtest_index, subtest in enumerate(self.integration.testcases, start=1):
            self.log.info('~'*75)
            self.device_log('*** Start sub-test #{}...'.format(self.env.subtest_index), force=True)
            self.integration.init_subtest(subtest)  # Create instances of sub-test. 
            self.integration.reder_subtest(subtest, self.env.subtest_index) # Add integration test information into sub-test.
            self._before_launch_subtest()
            # Run test
            ret_val = subtest.launch(callback=self.data.append_subtest)
            if ret_val is False:
                if self.env.stop_on_failure:
                    raise self.err.StopTest('Sub-test: {} is failed'.format(subtest['name']))

    #
    # MiddleWare Hooks Area
    #
    # Add more hooks if we need.
    def _before_launch_subtest(self):
        pass

    def _end_of_test(self):
        if not self.env.disable_print_errors and getattr(self, 'integration', None): # Check atts because it may called at init step.
            try:
                msgs = ''
                for iteration_index, testcases in enumerate(self.integration.loop_testcases, start=1):
                    for subtest_index, subtest in enumerate(testcases, start=1):
                        err_msg = subtest['instance'].log.gen_err_msg()
                        if err_msg:
                            msgs += '[{3}#{0} {1}]\n{2}\n'.format(
                                subtest_index, subtest['name'], err_msg, 'Itr-{} '.format(iteration_index) if self.env.loop_times else '')
                if msgs:
                    self.log.warning('* Sub-test Errors:\n{}'.format(msgs))
            except Exception, e:
                self.log.exception('Got an error during print test errors: {}'.format(e))
            if self.log.gen_err_msg(): self.log.info('* Main-thread Errors:')
        TestCase._end_of_test(self)


    class Environment(object):
        """ Superclass for integration environment method extensions. """

        def run_hook(self, kwargs):
            self.init_integration_flow_variables(of_inst=self, kwargs=kwargs)
            self.init_integration_components(of_inst=self.testcase)

        def init_integration_flow_variables(self, of_inst, kwargs):
            """ Initiate variables for integration testing flow. """
            target_inst = of_inst
            target_inst.disable_subtest_dryrun = kwargs.get('disable_subtest_dryrun', False) 
            target_inst.stop_on_failure = kwargs.get('stop_on_failure', False) 
            target_inst.choice = kwargs.get('choice', None)
            target_inst.unique_choice = kwargs.get('unique_choice', None)
            target_inst.exec_ordering = kwargs.get('exec_ordering', None)
            target_inst.exec_group = kwargs.get('exec_group', None)

        def init_integration_components(self, of_inst):
            """ Initiate components """
            target_inst = of_inst
            target_inst.data = IntegrationResultComponent(testcase_inst=target_inst) # replace
            target_inst.dummy_case = dummy_case
            target_inst.integration = IntegrationComponent(testcase_inst=target_inst)
            target_inst.testgroup = TG

        # Overwrite it replace Overwrite dump_to_dict.
        def _extend_hook_of_dump_to_dict(self, settings):
            #settings.pop('disable_subtest_dryrun', None)
            settings.pop('stop_on_failure', None)
            settings.pop('choice', None)
            settings.pop('unique_choice', None)
            settings.pop('exec_ordering', None)


class IntegrationResultComponent(ResultComponent):
    """ Result component of integration test. """

    def init(self):
        self.init_worksapce()
        self.test_result = None # "IntegrationResult" object to record the test result on the current iteration.
        self.loop_results = None # "ResultList" object to append each test iteration result.
        self.file_prefix = '' # Prefix part of output file name.
        self.upload_logstash = True

    def reset_test_result(self):
        self.env.log.info('Reset Test Result.')
        # For UUT may not support.
        uut = getattr(self.testcase, 'uut', None)
        if not uut:
            uut = {}
        self.test_result = IntegrationResult(
            test_suite=self.testcase.TEST_SUITE, test_name=self.testcase.TEST_NAME,
            build=uut.get('firmware', ''), iteration=self.env.iteration,
            product=uut.get('model', '')
        )

    def reset_loop_results(self):
        self.env.log.info('Reset Test Loop Results.')
        # For UUT may not support.
        uut = getattr(self.testcase, 'uut', None)
        if not uut:
            uut = {}
        self.loop_results = IntegrationLoopingResult(
            test_suite=self.testcase.TEST_SUITE, test_name=self.testcase.TEST_NAME, iteration=self.env.iteration,
            build=uut.get('firmware', ''), product=uut.get('model', '')
        )

    def export_test_result(self):
        """ Export xml file, not json file. """
        if self.env.iteration: # run in loop
            export_path = '{0}/{1}#{2}.xml'.format(self.env.results_folder, self.testcase.TEST_SUITE, self.env.iteration)
        else:
            export_path = '{0}/{1}.xml'.format(self.env.results_folder, self.testcase.TEST_SUITE)
        export_path = self.get_abs_path(export_path)
        self.test_result.to_file(export_path, output_format='junit-xml')
        self.env.log.info('Save Result To {}'.format(export_path))

    def export_loop_results(self):
        """ Use TestSuite.to_file to export xml file, """
        export_path = '{}/{}test_report.xml'.format(self.env.results_folder, self.testcase.loop_result_name)
        export_path = self.get_abs_path(export_path)
        with open(export_path, 'w') as f:
            # Use TestSuite.to_file() export loop_results.
            test_suites = [round_result.convert_to_TestSuite() for round_result in self.loop_results]
            for idx, test_suite in enumerate(test_suites, start=1):
                # Add postfix name.
                test_suite.name = '{0}#{1}'.format(test_suite.name, idx)
            TestSuite.to_file(f, test_suites, prettyprint=True)
        self.env.log.info('Save Loop Results To {}'.format(export_path))

    def export_test_result_as_popcorn(self):
        if self.env.iteration: # run in loop
            return # only export one report for entire test.
        self.export_popcorn_report(self.test_result)

    def upload_test_result_to_popcorn(self):
        if self.env.iteration or self.env.is_subtask: # run in loop or integration
            return # only export one report for entire test.
        self.upload_results_to_popcorn(self.test_result)

    def export_loop_results_as_popcorn(self):
        # TODO: Need to think it is good to put in one suite or several suites.
        self.export_popcorn_report(sum(self.loop_results, []))

    def upload_loop_results_to_popcorn(self):
        self.upload_results_to_popcorn(sum(self.loop_results, []))

    def append_subtest(self, subtest):
        """ Append each result of sub-tests to self.test_result, and add JUnit information. """
        result_list = []
        if isinstance(subtest['result'], list):
            # Modify looping sub-test attributes for display clearly on JUnit report.
            for idx, result in enumerate(subtest['result'], start=1):
                # sub-test testName = TEST_NAME#idx
                # FIXME: Use copy object if we don't want modify source object.
                result['testName'] = '{0}#{1}'.format(result['testName'], idx)
            result_list.extend(subtest['result'])
        else:
            result_list.append(subtest['result'])

        for result in result_list:
            if not isinstance(result, ELKTestResult):
                self.env.log.warning('Skipped unknown result: {}'.format(result))
                continue
            self.test_result.append(result)

    def error_callback(self, exception):
        # TODO: Implement it after we have any idea.
        return

    def print_test_result(self):
        if not self.env.debug_middleware:
            return
        self.env.log.info('#'*75)
        self.env.log.info('Integration Test Result: \n{}'.format(pformat(self.test_result)))
        self.env.log.info('#'*75)


class IntegrationComponent(TestCaseComponent):
    """ Test cases management of integration test. """

    def init(self):
        self.source_testcases = [] # Raw sub-tests list.
        self.testcases = [] # Sub-tests to run.
        self.current_idx = None
        self.current_testcase = None
        self.loop_testcases = []

    def set_testcases(self, testcases):
        self.testcases = testcases
        self.loop_testcases.append(testcases) # Record for each iteration.

    def add_testcase(self, testcase, custom_env=None, group=None):
        """ Register a list of test cases to integration test. """
        subtest = self.gen_subtest(testcase, custom_env, group)
        self.source_testcases.append(subtest)
        self.testcases.append(subtest)
        
    def add_testcases(self, testcases):
        """ Register one test cases to integration test. """
        for testcase in testcases:
            if isinstance(testcase, dict):
                self.add_testcase(**testcase)
            elif isinstance(testcase, (tuple, list)):
                self.add_testcase(*testcase)
            elif issubclass(testcase, TestCase):
                self.add_testcase(testcase)
            else:
                raise ValueError('Unknown testcase.')

    def gen_subtest(self, testcase, custom_env=None, group=None):
        default_env = {
            'dry_run': True, # Subtest not upload data by itself, do it at IntegrationTest.
            'disable_upload_logs': True # Do it at end of integration test.
        }
        env = default_env
        if custom_env:
            if not isinstance(custom_env, dict):
                raise ValueError('custom_env only accept dict.')
            env.update(custom_env)

        if self.env.disable_subtest_dryrun:
            env['dry_run'] = False

        return SubTestCase(**{
            'class': testcase,
            'custom_env': env,
            'name': testcase.TEST_NAME,
            'group': group
        })

    def init_subtest(self, subtest):
        """ Create test case instance and reset result. """
        if not isinstance(subtest, SubTestCase):
            raise ValueError('subtest only accept SubTestCase.')

        testcase = subtest['class']
        custom_env = subtest['custom_env']
        # Copy self data.
        input_env = self.env.dump_to_dict().copy()
        # Update input_env with custom_env.
        input_env.update(custom_env)
        # Create instance with input_env. 
        try:
            keeper_list = []
            if subtest['group']:
                # Raise test exception if any of prevous test cases is matched. 
                # self.current_idx seems None.
                self.testcase.testgroup.raise_if_test_group_matched(testcases=self.testcases[:self.current_idx], subtest=subtest)
            subtest['instance'] = testcase(input_obj=input_env, keeper_list=keeper_list)

            # Check subtest has generated new library instances, then share to other subtests.
            self.share_subtest_library_instance(subtest)
        except Exception, e:
            # When initiate sub-test faile, here create a dummy case to replace original one,
            # this behavior is to make integration test keep going.
            # The key reason of this way is there are no way to create testcase instance when it initiate failed
            # by code logic error or raising custum error.
            # Please keep observing this behavior is suitable or not.
            # Use custom  name if it has, or use default test name in class.
            self._set_test_name(input_env, testcase)
            self.env.log.exception('Catch An Exception During Initiate Sub-test: {}.'.format(input_env['TEST_NAME']))
            self.env.log.warning('Create a DummyCase for this case...')
            # Excute additional hook.
            self._extend_hook_of_init_subtest_exception(input_env, subtest)
            # Create test case instance.
            if isinstance(e, error.TestPass): # Only for exception raised from test group feature.
                subtest['instance'] = dummy_case.get_pass_case(subtest['class'])(input_obj=input_env, pass_message=str(e))
                self.env.log.warning('Create PassCase finish and replace original case in result list.')
            else: # Normal
                subtest['instance'] = dummy_case.get_failure_case(subtest['class'])(input_obj=input_env, exception=e)
                self.env.log.warning('Create FailureCase finish and replace original case in result list.')
                if keeper_list and isinstance(keeper_list[0], TestCase): # Replace log instance by original testcase for show error message at end.
                    subtest['instance'].log = keeper_list[0].log
        subtest['result'] = None 
        subtest['pass'] = None

    def share_subtest_library_instance(self, subtest):
        try:
            if not hasattr(subtest['instance'], 'env'):
                return
            subtest_dict = subtest['instance'].env.dump_to_dict()
            if not self.env.EXPORT_FILED in subtest_dict:
                return
            subtest_inst = subtest_dict[self.env.EXPORT_FILED]

            def get_lib_inst(subtest_inst, lib_name):
                inst = getattr(subtest_inst, lib_name, None)
                if not inst: # not instance
                    return
                # may missing check type
                if isinstance(inst, int) or isinstance(inst, bool) or isinstance(inst, str):
                    return
                return inst

            def share_lib_exists(integration_inst, lib_name):
                # not sure need to add more check or not.
                if getattr(integration_inst, lib_name, None) is None:
                    return True
                return False

            for lib_name in subtest['instance'].SETTINGS:
                lib_inst = get_lib_inst(subtest_inst, lib_name)
                if lib_inst and share_lib_exists(self.testcase, lib_name):
                    setattr(self.testcase, lib_name, lib_inst)
                    self.env.log.info('Copy {} library instance and share to other subtests'.format(lib_name))
        except Exception as e:
            self.env.log.warning('Got error while sharing subtest library: {}'.format(e), exc_info=True)

    def _set_test_name(self, input_env, testcase):
        custom_TEST_SUITE = input_env.get('TEST_SUITE')
        if custom_TEST_SUITE:
            input_env['TEST_SUITE'] = ignore_unknown_codec(custom_TEST_SUITE)
        else:
            input_env['TEST_SUITE'] = testcase.TEST_SUITE
        custom_TEST_NAME = input_env.get('TEST_NAME')
        if custom_TEST_NAME:
            input_env['TEST_NAME'] = ignore_unknown_codec(custom_TEST_NAME)
        else:
            input_env['TEST_NAME'] = testcase.TEST_NAME

    # Overwrite it replace Overwrite init_subtest.
    def _extend_hook_of_init_subtest_exception(self, input_env, subtest):
        pass

    def init_subtests(self):
        """ Init all sub-tests. """
        for testcase in self.testcases:
            self.init_subtest(subtest=testcase)

    def reder_subtest(self, subtest, idx):
        """ Dynamic modify attributes of subtests before run test:
            1. Rename output data.
            2. Rename TEST_SUITE.
        """
        # prefix = TEST_SUITE-IDX- or TEST_SUITE#123-IDX-
        if self.env.iteration:
            prefix = '{0}#{1}-{2}-'.format(self.testcase.TEST_SUITE, self.env.iteration, idx)
        else:
            prefix = '{0}-{1}-'.format(self.testcase.TEST_SUITE, idx)

        # file name = TEST_SUITE#123-IDX-SOME_TEST#456
        subtest['instance'].data.file_prefix = prefix
        # TODO: Still no name when sub test is failed.
        if getattr(subtest['instance'].env, 'logcat_name', None):
            subtest['instance'].env.logcat_name = '{0}-{1}'.format(subtest['instance'].TEST_NAME, subtest['instance'].env.logcat_name)
        # Replace TEST_SUITE of sub-test for JUnit report.
        subtest['instance'].TEST_SUITE = self.testcase.TEST_SUITE
        self._extend_hook_of_reder_subtest(locals())

    # Overwrite it replace Overwrite reder_subtest.
    def _extend_hook_of_reder_subtest(self, locals):
        pass

    def reder_subtests(self):
        """ Reder all sub-tests. """
        for idx, testcase in enumerate(self.testcases, start=1):
            self.reder_subtest(subtest=testcase, idx=idx)

    def list(self):
        """ List all sub-tests. """
        self.env.log.info('#'*75)
        for idx, testcase in enumerate(self.testcases, start=1):
            self.env.log.info("#{0} : TEST_NAME: {1} custom_env: {2}".format(idx, testcase['name'], testcase['custom_env']))
        self.env.log.info('#'*75)

    #
    # Protocols Implementations
    #
    def __iter__(self):
        self.current_idx = 0
        self.current_testcase = None
        return self

    def next(self):
        idx = self.current_idx + 1
        try:
            self.current_testcase = self.testcases[idx]
        except IndexError:
            raise StopIteration()

        self.current_idx = idx
        return self.current_testcase

    def __len__(self):
        return len(self.testcases)


class SubTestCase(dict):
    """ Sub-testcase of integration test. """

    def __init__(self, *args, **kwargs):
        self['class'] = None       # Class object of testcase.
        self['custom_env'] = None  # Dict data to update the Environment of testcase.
        self['instance'] = None    # Test case instance.
        self['name'] = None        # Test case name.
        self['result'] = None      # Test result, it could be ELKTestResult(Single case) or ResultList(Looping case).
        self['pass'] = None        # Test is pass or not.
        self['group'] = None       # Test group.

        # args check
        if 'group' in kwargs and kwargs['group']:
            if not isinstance(kwargs['group'], list):
                raise ValueError('"group" should be a list')
            for g in kwargs['group']:
                if not isinstance(g, TG.TestGroup):
                    raise ValueError('{} is not a TestGroup'.format(type(g)))

        # init
        super(SubTestCase, self).__init__(*args, **kwargs)

    def launch(self, callback=None):
        """ Run test and save result. """
        # Update test case name from instance.
        self['name'] = self['instance'].TEST_NAME
        # Run test.
        ret_val = self['instance'].main()
        # Update self attributes.
        if self['instance'].env.is_looping():
            self['result'] = self['instance'].data.loop_results
        else:
            self['result'] = self['instance'].data.test_result
        if callback: # update hook
            callback(self)
        self['pass'] = ret_val
        return ret_val
