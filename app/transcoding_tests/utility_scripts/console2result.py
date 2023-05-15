# -*- coding: utf-8 -*-
""" A tool to parse Jenkins conlose logs to xml report.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
from argparse import ArgumentParser
import cPickle as pickle


def scan_and_parse(log_path):
    """ Main function. """
    with open(log_path, 'r') as log:
        with open('results.pkl', 'wb') as output:
            while True:
                try:
                    log_block = find_subtest(log)
                    test_info = parse_log(log_block)
                    pickle.dump(test_info, output, pickle.HIGHEST_PROTOCOL)
                except RuntimeError:
                    break
                except Exception, e:
                    raise
                    #print e

def load_and_convert(result_path, util_index):
    """ Main function. """
    results = ResultList()
    with open(result_path, 'rb') as f:
        while True:
            try:
                if util_index and len(results) == util_index:
                    break
                test_info = pickle.load(f)
                results.append(convert_elk_result(test_info))
            except EOFError:
                break 
    results.to_file('report.xml', output_format='junit-xml')

def find_subtest(f):
    """ Find the next test case and return test logs in list. """
    log_block = []

    while True: # To find the start line of test case.
        line = f.readline()
        if line.startswith('KAT.middleware                : INFO     *** Start Sub-test #'):
            break
        if not line: # End of file.
            raise RuntimeError('EOF')

    log_block.append(line)
    while True: # Load whole message of this test case.
        line = f.readline()
        log_block.append(line)
        if line.startswith('KAT.middleware                : INFO     *** Sub-test #'):
            return log_block
        if not line: # End of file.
            raise RuntimeError('EOF')

def parse_log(log_block):
    info = {
        'index': None,
        'name': None,
        'pass': True,
        'errmsg': None
    }
    for line in log_block: # Check lines.
        # Get test index number.
        if line.startswith('KAT.middleware                : INFO     *** Start Sub-test #'):
            info['index'] = line.split('#').pop().split('...')[0]
        # Get test result.
        if 'PASS' in line:
            info['name'] = line.split('KAT.RESTSDKTranscoding        : WARNING  ').pop().split(' is PASS')[0]
            info['pass'] = True
        if 'FAILED' in line:
            info['name'] = line.split('KAT.RESTSDKTranscoding        : WARNING  ').pop().split(' is FAILED')[0]
            info['pass'] = False
        # Get error message.
        if 'KAT.RESTSDKTranscoding        : ERROR    [STATUS-' in line:
            info['errmsg'] = line.split('KAT.RESTSDKTranscoding        : ERROR    ').pop().strip()
    return info

def convert_elk_result(test_info):
    test_result = ELKTestResult(
        test_suite='RESTSDK_Transcoding', test_name=test_info['name'],
        build='build'
    )
    if test_info['errmsg']: test_result['error_message'] = test_info['errmsg']
    return test_result


if __name__ == '__main__':
    parser = ArgumentParser(description='Parse Jenkins conlose log to xml report')
    parser.add_argument('-lp', '--log_path', help='log path to parse', default=None)
    parser.add_argument('-rp', '--result_path', help='pkl file to parse', default=None)
    parser.add_argument('-ui', '--util_index', help='last test index to export', type=int, default=None)
    args = parser.parse_args()
    if args.log_path:
        scan_and_parse(log_path=args.log_path)
    if args.result_path:
        from platform_libraries.test_result import ELKTestResult, ResultList
        load_and_convert(result_path=args.result_path, util_index=args.util_index)
