__author__ = 'Estvan Huang <Estvan.Huang@wdc.com>'

# std modules
import json
import time
# 3rd party modules
import requests
# platform modules
from common_utils import create_logger
from constants import LOGSTASH_SERVER_TW
from middleware.error import get_junit_msg_key_from
from junit_xml import TestCase, TestSuite


log = create_logger(log_name='TestResult') # global logging instance


#
# Test Results Area
#
class ResultList(list):
    """
    A list of test results, including import/export features.

    [Usage]
        Use it just like list object. There are some examples in __main__ block.

    [Notes]
        Only accept TestResult object if you will use with xml feature.
    """
    # Data for middleware.
    TEST_SUITE = None
    TEST_NAME = None
    TEST_ELAPSED_SEC = None
    TEST_PASS = None
    # Data for Duration Estimation.
    TEST_AVG_ELAPSED_SEC = None
    TEST_MAX_ELAPSED_SEC = None
    TEST_MIN_ELAPSED_SEC = None
    TEST_LAST_ERR_ELAPSED_SEC = None


    def set_common_data(self, **kwargs):
        """ Set data for updating each test result of ResultList. """
        for keyword, value in kwargs.iteritems():
            self.__setattr__(keyword, value)
        return self.__dict__

    def _update_data_to_all(self):
        """ Update data to each test result of ResultList. """
        return # Disable it because we have no scenario for it.
        if not self.__dict__:
            return
        log.info('Set common data to test results.')
        for test_result in self:
            test_result.update(self.__dict__)

    def to_file(self, path, output_format='json'):
        """ Covert result set to the specified format file. """
        self._update_data_to_all() # Update common data before exporting.

        if output_format == 'junit-xml': # Interfacing junit_xml.
            with open(path, 'w') as f:
                TestSuite.to_file(f, [self.convert_to_TestSuite()], prettyprint=True)
        else: # json
            object_to_json_file(self, path)

    def from_file(self, path, input_format='json'):
        """ 
        Loading data from the specified file and update to self instance.

        [Return]
            ResultList object.
        """
        # TODO: Support junit-xml.
        import_list = json_file_to_object(path)
        self.extend(import_list)
        return self

    def upload_to_logstash(self, server_url=None):
        self._update_data_to_all() # Update common data before uploading.

        for test_result in self:
            test_result.upload_to_logstash(server_url)
        return True

    def convert_to_TestSuite(self):
        """ 
        Convert self object to TestSuite object.

        [Notes]
            1. Only pass key name which is accepted in TestResult to create the new object.
            2. All of test result objects in ResultList must be TestResult object.

        [Return]
            TestSuite object.
        """
        common_data = self.__dict__
        test_cases = [test_result.convert_to_TestCase() for test_result in self]
        default_name = self[0].get('testSuite') if self else None

        return TestSuite(
            name=common_data.get('name', default_name), test_cases=test_cases, hostname=common_data.get('hostname'),
            id=common_data.get('id'),  package=common_data.get('package'), timestamp=common_data.get('timestamp'),
            properties=common_data.get('properties')
        )

    def summarize(self, print_out=False, print_executed_test=False):
        """ Determine test is pass or failed. """
        failed_tests = []
        passed_tests = []
        skipped_tests = []
        other_tests = [] # No idea for now.

        # Classify sub-testcases by its result.
        for itr_result in self:
            if hasattr(itr_result, 'TEST_PASS'):
                if itr_result.TEST_PASS:
                    passed_tests.append(itr_result)
                elif itr_result.TEST_PASS is None:
                    skipped_tests.append(itr_result)
                else:
                    failed_tests.append(itr_result)
            else:
                other_tests.append(itr_result)

        # Duration Estimation.
        def fetch_elapsed_time(results):
            return [i.TEST_ELAPSED_SEC for i in results if i.TEST_ELAPSED_SEC]

        passed_time_list = fetch_elapsed_time(passed_tests)
        self.TEST_AVG_ELAPSED_SEC = sum(passed_time_list)/len(passed_time_list) if passed_time_list else None
        self.TEST_MAX_ELAPSED_SEC = max(passed_time_list) if passed_time_list else None
        self.TEST_MIN_ELAPSED_SEC = min(passed_time_list) if passed_time_list else None
        failed_time_list = fetch_elapsed_time(failed_tests)
        self.TEST_LAST_ERR_ELAPSED_SEC = failed_time_list[-1] if failed_time_list else None

        # Print message.
        if print_out:
            log.info('-'*75)
            log.info('Total tests : {}'.format(len(self)))
            if print_executed_test:
                for test in self:
                    log.info("=> {}".format(getattr(test, 'TEST_NAME', 'Unknown')))
            log.info('Failed tests: {}'.format(len(failed_tests)))
            for failed_test in failed_tests:
                log.info("=> {} is FAILED".format(getattr(failed_test, 'TEST_NAME', 'Unknown')))
            for skipped_test in skipped_tests:
                log.info("=> {} is SKIPPED".format(getattr(skipped_test, 'TEST_NAME', 'Unknown')))
            log.info('-'*75)
            log.info('Average Elapsed Time: {}'.format(self.TEST_AVG_ELAPSED_SEC))
            log.info('Maximum Elapsed Time: {}'.format(self.TEST_MAX_ELAPSED_SEC))
            log.info('Minimum Elapsed Time: {}'.format(self.TEST_MIN_ELAPSED_SEC))
            log.info('Last Error Elapsed Time: {}'.format(self.TEST_LAST_ERR_ELAPSED_SEC))
            log.info('-'*75)

        # Determine result by sub-testcases.
        if self.TEST_PASS is None:
            if failed_tests:
                self.TEST_PASS = False
            else:
                self.TEST_PASS = True

        return self.TEST_PASS


class ELKLoopingResult(ResultList):
    """ Looping result for upload to ELK. """

    TEST_ITERATION = None

    def __init__(self, test_suite, test_name, build, iteration=None, *args, **kargs):
        """ See ELKTestResult. """
        self.TEST_SUITE = test_suite
        self.TEST_NAME = test_name
        self.TEST_BUILD = build
        self.additional_dict = kargs

        if iteration:
            self.TEST_ITERATION = '{0}_itr_{1}'.format(build, str(iteration).zfill(2))

        super(ELKLoopingResult, self).__init__(*args)

    def upload_to_logstash(self, server_url=None):
        upload_dict = {
            "testSuite": self.TEST_SUITE,
            "testName" : self.TEST_NAME,
            "build"    : self.TEST_BUILD,
            "elapsed_sec": self.TEST_ELAPSED_SEC,
            "result_type": "looping",
            "ave_elapsed_sec": self.TEST_AVG_ELAPSED_SEC,
            "max_elapsed_sec": self.TEST_MAX_ELAPSED_SEC,
            "min_elapsed_sec": self.TEST_MIN_ELAPSED_SEC,
            "last_err_elapsed_sec": self.TEST_LAST_ERR_ELAPSED_SEC,
            "test_pass": self.TEST_PASS
        }
        upload_dict.update(self.additional_dict)
        return upload_to_logstash(upload_dict, server_url)


class IntegrationLoopingResult(ELKLoopingResult):

    def upload_to_logstash(self, server_url=None):
        upload_dict = {
            "testSuite": self.TEST_SUITE,
            "testName" : self.TEST_NAME,
            "build"    : self.TEST_BUILD,
            "iteration": self.TEST_ITERATION,
            "elapsed_sec": self.TEST_ELAPSED_SEC,
            "result_type": "integration_looping",
            "ave_elapsed_sec": self.TEST_AVG_ELAPSED_SEC,
            "max_elapsed_sec": self.TEST_MAX_ELAPSED_SEC,
            "min_elapsed_sec": self.TEST_MIN_ELAPSED_SEC,
            "last_err_elapsed_sec": self.TEST_LAST_ERR_ELAPSED_SEC,
            "test_pass": self.TEST_PASS
        }
        upload_dict.update(self.additional_dict)
        return upload_to_logstash(upload_dict, server_url)


class IntegrationResult(ELKLoopingResult):

    def summarize(self, print_out=True, print_executed_test=False):
        """ Determine test is pass or failed. """
        passed_tests = []
        failed_tests = []
        error_tests = []
        failure_tests = []
        skipped_tests = []
        other_err_tests = []
        other_tests = []

        # Collect failed sub-tests
        for testcase in self:
            if testcase.TEST_PASS is True:
                passed_tests.append(testcase)
                continue
            if 'skipped_message' in testcase or testcase.TEST_PASS is None:
                skipped_tests.append(testcase)
                continue
            failed_tests.append(testcase)
            if 'error_message' in testcase:
                error_tests.append(testcase)
            elif 'failure_message' in testcase:
                failure_tests.append(testcase)
            else:
                other_err_tests.append(testcase)

        # Print message.
        #if print_out:
        log.info('-'*75)
        log.info('Total tests : {}'.format(len(self)))
        if print_executed_test:
            for test in self:
                log.info("=> {}".format(test.TEST_NAME))
        log.info('Failed tests: {}'.format(len(failed_tests)))
        for error_test in error_tests: # Normal test fail.
            log.info("=> {} is FAILED".format(error_test.TEST_NAME))
        for failure_test in failure_tests:
            log.info("=> {} is FAILURE".format(failure_test.TEST_NAME))
        for other_err_test in other_err_tests:
            log.info("=> {} is Undefined Error".format(getattr(other_err_test, 'TEST_NAME', 'NoTestName')))
        log.info('Skipped tests: {}'.format(len(skipped_tests)))
        for skipped_test in skipped_tests:
            log.info("=> {} is SKIPPED".format(skipped_test.TEST_NAME))
        log.info('-'*75)

        if self.TEST_PASS is None:
            if failed_tests:
                self.TEST_PASS = False
            else:
                self.TEST_PASS = True

        return self.TEST_PASS

    def upload_to_logstash(self, server_url=None):
        upload_dict = {
            "testSuite": self.TEST_SUITE,
            "testName" : self.TEST_NAME,
            "build"    : self.TEST_BUILD,
            "elapsed_sec": self.TEST_ELAPSED_SEC,
            "result_type": "integration",
            "test_pass": self.TEST_PASS
        }
        upload_dict.update(self.additional_dict)
        return upload_to_logstash(upload_dict, server_url)


class TestResult(dict):
    """
    A set to record test result, including import/export features.

    [Usage]
        Use it just like dict object. There are some examples in __main__ block.
    """
    # Data for middleware.
    TEST_SUITE = None
    TEST_NAME = None
    TEST_ELAPSED_SEC = None
    TEST_PASS = None
    # Popcorn
    POPCORN_RESULT = None


    def to_file(self, path, output_format='json'):
        """ Covert result data to the specified format file. """
        if output_format == 'junit-xml': # Interfacing junit_xml.
            with open(path, 'w') as f:
                test_case = self.convert_to_TestCase()
                # 'name' filed will take key 'name' or 'testName'.
                test_suite = TestSuite(name=self.get('name', self.get('testName')), test_cases=[test_case])
                TestSuite.to_file(f, [test_suite], prettyprint=True)
        else: # json
            object_to_json_file(self, path)

    def from_file(self, path, input_format='json'):
        """ 
        Loading data from the specified file and update to self instance.

        [Return]
            TestResult object.
        """
        # TODO: Support junit-xml.
        import_dict = json_file_to_object(path)
        self.update(import_dict)
        return self

    def upload_to_logstash(self, server_url=None):
        self['test_pass'] = self.TEST_PASS # Update before upload.
        return upload_to_logstash(self, server_url)

    def convert_to_TestCase(self):
        """ 
        Convert self object to TestCase object.

        [Notes]
            1. Only pass key name which is accepted in TestResult to create the new object.
            2. Set 'error_message', 'error_output', 'failure_message', 'failure_output', 'skipped_message' or 'skipped_output'
               to replace invoking method add_error_info/add_failure_info/add_skipped_info.

        [Return]
            TestCase object.
        """
        test_case = TestCase( # 'name' filed will take key 'name' or 'testName'.
            name=self.get('name', self.get('testName')), classname=self.get('classname', self.get('testSuite')),
            elapsed_sec=self.get('elapsed_sec'), stdout=self.get('stdout'), stderr=self.get('stderr'),
            attachments=self.get('attachments'), metrics=self.get('metrics')
        )

        # Convert add_error_info/add_failure_info/add_skipped_info with setting values.
        key = get_junit_msg_key_from(self)
        if key:
            test_case.__setattr__(key, self[key])

        return test_case

    def summarize(self, print_out=True):
        """ Determine test is pass or failed. """
        if self.TEST_PASS is None:
            # Determine with Junit rules.
            key = get_junit_msg_key_from(self)
            if key == 'skipped_message':
                self.TEST_PASS = None
            elif key:
                self.TEST_PASS = False
            else:
                self.TEST_PASS = True

        # Print logs.
        if print_out:
            log.info('{} is {}'.format(self.TEST_NAME, self.TEST_PASS if self.TEST_PASS is not None else 'SKIPPED'))

        return self.TEST_PASS


class ELKTestResult(TestResult):
    """ Create TestResult object with a basic template. """

    def __init__(self, test_suite, test_name, build, iteration=None, **kargs):
        """
        [Arguments]                            TestResult object:
                                               {
            test_suite :  "TESTs"          =>    "testSuite": "TESTs",
            test_name  :  "TEST_1"         =>    "testName" : "TEST_1",
            build      :  "VERSION"        =>    "build"    : "VERSION",
            iteration  :  2                =>    "iteration": "VERSION_itr_02",
            kargs      :  {"Key": value}   =>    "Key"      : value
                                               }
        """
        self.TEST_SUITE = test_suite
        self.TEST_NAME = test_name

        if iteration:
            kargs['iteration'] = '{0}_itr_{1}'.format(build, str(iteration).zfill(2))

        kargs['result_type'] = 'testcase'

        super(ELKTestResult, self).__init__(testSuite=test_suite , testName=test_name, build=build, **kargs)


#
# Tool Kits Area
#
def upload_to_logstash(dict_data, server_url=None):
    """ 
    Upload the given dict data to specified logstash server via HTTP.

    [Raise]
        Raise TestResultError if data upload failed.
    """
    if not server_url:
        server_url = LOGSTASH_SERVER_TW

    headers = {'Content-Type': 'application/json'}
    response = requests.post(url=server_url, data=json.dumps(dict_data, ensure_ascii=False), headers=headers)
    if response.status_code != 200:
        raise TestResultError('Upload to logstash server {0} failed. Status Code: {1}, Content: {2}'.format(
            server_url, response.status_code, response.content))

    log.info('Uploaded data to logstash server: {}'.format(server_url))
    return True

def object_to_json_file(object_data, path):
    """ Serialize a Python object to json formated data and save it to a file. """
    with open(path, 'w') as fp:
        json.dump(object_data, fp, ensure_ascii=False)
    log.info('Output to json file:{}.'.format(path))

def json_file_to_object(path):
    """ Load specified file and deserialize content to a Python object. """
    with open(path, 'r') as fp:
        return json.load(fp)


#
# Custom Exception Area
#
class TestResultError(RuntimeError):
    pass


if __name__ == '__main__':
    """ Examples """
    import os

    def print_file(file_path):
        with open(file_path, 'r') as fp:
            print 'File:', file_path
            print 'Content:', ''.join(fp.readlines())

    # Test Settings
    logstash_url = 'http://10.136.127.127:8081'
    file_path = '/tmp/result_file'
    data = {'testName': 'Unit Test', 'build': '123456', 'data-1': 'TEXT', 'data-2': 123}

    #
    # Test Tool Kits
    #
    print '\n[Test Tool Kits]\n'
    # Test object_to_json_file
    object_to_json_file(data, file_path)
    print 'Export to json file...'
    print_file(file_path)
    """ ## Output ###
    Export to json file...
    File: /tmp/result_file
    Content: {"data-1": "TEXT", "data-2": 123, "testName": "Unit Test", "build": "123456"}
    """
    
    # Test json_file_to_object
    import_data = json_file_to_object(file_path)
    print '\nImport data:', import_data
    """ ### Output ###
    Import data: {u'data-1': u'TEXT', u'data-2': 123, u'testName': u'Unit Test', u'build': u'123456'}
    """

    # Test upload_to_logstash
    print '\nTest upload_to_logstash:', upload_to_logstash(import_data, server_url=logstash_url)
    """ ### Output ###
    Test upload_to_logstash: True
    """

    #
    # Test TestResult
    #
    print '\n[Test TestResult]\n'
    # Creation Case 1
    tr = TestResult()
    print 'Case 1: Empty TestResult =', tr
    tr['data-1'] = 'TEXT'
    tr['data-2'] = 123
    print 'Case 1: TestResult =', tr
    """ ### Output ###
    Case 1: Empty TestResult = {}
    Case 1: TestResult = {'data-1': 'TEXT', 'data-2': 123}
    """
    # Creation Case 2
    tr = TestResult(data_1='TEXT', data_2=123)
    print 'Case 2: TestResult =', tr
    """ ### Output ###
    Case 2: TestResult = {'data_2': 123, 'data_1': 'TEXT'}
    """
    # Creation Case 3
    tr = TestResult(data)
    print 'Case 3: TestResult =', tr
    """ ### Output ###
    Case 3: TestResult = {'data-1': 'TEXT', 'data-2': 123, 'testName': 'Unit Test', 'build': '123456'}
    """
    # Creation Case 4
    tr = TestResult(**data)
    print 'Case 4: TestResult =', tr
    """ ### Output ###
    Case 4: TestResult = {'data-1': 'TEXT', 'data-2': 123, 'testName': 'Unit Test', 'build': '123456'}
    """

    # Test json export
    print '\nExport to json file...'
    tr.to_file(file_path, output_format='json')
    print_file(file_path)
    """ ### Output ###
    Export to json file...
    File: /tmp/result_file
    Content: {"data-1": "TEXT", "data-2": 123, "testName": "Unit Test", "build": "123456"}
    """

    # Test json import
    print '\nImport json file:', TestResult().from_file(file_path, input_format='json')
    """ ### Output ###
    Import json file: {u'data-1': u'TEXT', u'data-2': 123, u'testName': u'Unit Test', u'build': u'123456'}
    """

    # Test junit-xml export
    tr.to_file(file_path, output_format='junit-xml')
    print '\nExport to junit-xml file...'
    print_file(file_path)
    """ ### Output ###
    Export to junit-xml file...
    File: /tmp/result_file
    Content: 
    <?xml version="1.0" ?>
    <testsuites errors="0" failures="0" skipped="0" tests="1" time="0.0">
            <testsuite errors="0" failures="0" name="Unit Test" skipped="0" tests="1" time="0">
                    <testcase name="Unit Test"/>
            </testsuite>
    </testsuites>
    """

    # Test upload_to_logstash
    print '\nTest upload_to_logstash:', tr.upload_to_logstash(server_url=logstash_url)
    """ ### Output ###
    Test upload_to_logstash: True
    """

    #
    # Test ResultList
    #
    print '\n[Test ResultList]\n'
    # Creation Case 1
    rs = ResultList()
    print 'Case 1: Empty ResultList =', rs
    rs.append(tr)
    print 'Case 1: ResultList =', rs
    """ ### Output ###
    Case 1: Empty ResultList = []
    Case 1: ResultList = [{'data-1': 'TEXT', 'data-2': 123, 'testName': 'Unit Test', 'build': '123456'}]
    """
    # Creation Case 2
    tr1 = TestResult(name='tr1', elapsed_sec=123, error_message='err_msg', error_output='err_out', **data)
    tr2 = TestResult(classname='tr2', elapsed_sec=456, failure_message='fail_msg', failure_output='fail_out', **data)
    tr3 = TestResult(name='tr3', classname='class-tr3', elapsed_sec=0, skipped_message='skip_msg', skipped_output='skip_out', **data)
    rs = ResultList([tr, tr1, tr2, tr3])
    print 'Case 2: ResultList =', rs
    """ ### Output ###
    Case 2: ResultList = 
        [{'build': '123456', 'data-1': 'TEXT', 'data-2': 123, 'testName': 'Unit Test'},
         {'build': '123456',
          'data-1': 'TEXT',
          'data-2': 123,
          'elapsed_sec': 123,
          'error_message': 'err_msg',
          'error_output': 'err_out',
          'name': 'tr1',
          'testName': 'Unit Test'},
         {'build': '123456',
          'classname': 'tr2',
          'data-1': 'TEXT',
          'data-2': 123,
          'elapsed_sec': 456,
          'failure_message': 'fail_msg',
          'failure_output': 'fail_out',
          'testName': 'Unit Test'},
         {'build': '123456',
          'classname': 'class-tr3',
          'data-1': 'TEXT',
          'data-2': 123,
          'elapsed_sec': 0,
          'name': 'tr3',
          'skipped_message': 'skip_msg',
          'skipped_output': 'skip_out',
          'testName': 'Unit Test'}]
    """

    # Test set_common_data
    print '\nEmpty ResultList =', rs.set_common_data()
    print 'Add ResultList =', rs.set_common_data(name='Test_Name', c_data_1='TEXT-2')
    print 'Add ResultList =', rs.set_common_data(**{'c_data_2': 456})
    """ ### Output ###
    Empty ResultList = {}
    Add ResultList = {'name': 'Test_Name', 'c_data_1': 'TEXT-2'}
    Add ResultList = {'name': 'Test_Name', 'c_data_1': 'TEXT-2', 'c_data_2': 456}
    """

    # Test json export
    print '\nExport to json file...'
    rs.to_file(file_path, output_format='json')
    print_file(file_path)
    """ ### Output ###
    Export to json file...
    File: /tmp/result_file
    Content: 
        [{'build': '123456',
          'c_data_1': 'TEXT-2',
          'c_data_2': 456,
          'data-1': 'TEXT',
          'data-2': 123,
          'name': 'Test_Name',
          'testName': 'Unit Test'},
         {'build': '123456',
          'c_data_1': 'TEXT-2',
          'c_data_2': 456,
          'data-1': 'TEXT',
          'data-2': 123,
          'elapsed_sec': 123,
          'error_message': 'err_msg',
          'error_output': 'err_out',
          'name': 'Test_Name',
          'testName': 'Unit Test'},
         {'build': '123456',
          'c_data_1': 'TEXT-2',
          'c_data_2': 456,
          'classname': 'tr2',
          'data-1': 'TEXT',
          'data-2': 123,
          'elapsed_sec': 456,
          'failure_message': 'fail_msg',
          'failure_output': 'fail_out',
          'name': 'Test_Name',
          'testName': 'Unit Test'},
         {'build': '123456',
          'c_data_1': 'TEXT-2',
          'c_data_2': 456,
          'classname': 'class-tr3',
          'data-1': 'TEXT',
          'data-2': 123,
          'elapsed_sec': 0,
          'name': 'Test_Name',
          'skipped_message': 'skip_msg',
          'skipped_output': 'skip_out',
          'testName': 'Unit Test'}]
    """

    # Test json import
    print '\nImport json file:', ResultList().from_file(file_path, input_format='json')
    """ ### Output ###
    Import json file: 
    [{u'build': u'123456',
      u'c_data_1': u'TEXT-2',
      u'c_data_2': 456,
      u'data-1': u'TEXT',
      u'data-2': 123,
      u'name': u'Test_Name',
      u'testName': u'Unit Test'},
     {u'build': u'123456',
      u'c_data_1': u'TEXT-2',
      u'c_data_2': 456,
      u'data-1': u'TEXT',
      u'data-2': 123,
      u'elapsed_sec': 123,
      u'error_message': u'err_msg',
      u'error_output': u'err_out',
      u'name': u'Test_Name',
      u'testName': u'Unit Test'},
     {u'build': u'123456',
      u'c_data_1': u'TEXT-2',
      u'c_data_2': 456,
      u'classname': u'tr2',
      u'data-1': u'TEXT',
      u'data-2': 123,
      u'elapsed_sec': 456,
      u'failure_message': u'fail_msg',
      u'failure_output': u'fail_out',
      u'name': u'Test_Name',
      u'testName': u'Unit Test'},
     {u'build': u'123456',
      u'c_data_1': u'TEXT-2',
      u'c_data_2': 456,
      u'classname': u'class-tr3',
      u'data-1': u'TEXT',
      u'data-2': 123,
      u'elapsed_sec': 0,
      u'name': u'Test_Name',
      u'skipped_message': u'skip_msg',
      u'skipped_output': u'skip_out',
      u'testName': u'Unit Test'}]
    """

    # Test junit-xml export
    rs.to_file(file_path, output_format='junit-xml')
    print '\nExport to junit-xml file...'
    print_file(file_path)
    """ ### Output ###
    Export to junit-xml file...
    File: /tmp/result_file
    Content: 
    <?xml version="1.0" ?>
    <testsuites errors="1" failures="1" skipped="1" tests="4" time="579.0">
            <testsuite errors="1" failures="1" name="Test_Name" skipped="1" tests="4" time="579">
                    <testcase name="Test_Name"/>
                    <testcase name="Test_Name" time="123.000000">
                            <error message="err_msg" type="error">err_out</error>
                    </testcase>
                    <testcase classname="tr2" name="Test_Name" time="456.000000">
                            <failure message="fail_msg" type="failure">fail_out</failure>
                    </testcase>
                    <testcase classname="class-tr3" name="Test_Name">
                            <skipped message="skip_msg" type="skipped">skip_out</skipped>
                    </testcase>
            </testsuite>
    </testsuites>
    """

    # Test upload_to_logstash
    print '\nTest upload_to_logstash:', rs.upload_to_logstash(server_url=logstash_url)
    """ ### Output ###
    Test upload_to_logstash: True
    """

    # Clear temporary file.
    if os.path.exists(file_path):
        os.remove(file_path)
