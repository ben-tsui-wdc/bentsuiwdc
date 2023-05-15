""" A tool to parse Junit xml report to HTML table.
"""
___author___ = 'Ben Tsui <ben.tsui@wdc.com'

import click
import json
import re
import os
from collections import OrderedDict
from xml.etree.ElementTree import parse


@click.command()
@click.option('--xml_path', default='output.xml', help='The path of xml test result')
@click.option('--result_path', default='result.txt', help='The path to save parse result')
@click.option('--code_mapping', default=None, help='The table to mapping result code to status string on report, which is a json string.')
def parser_xml_result(xml_path, result_path, code_mapping):

    def get_mapping(element, code_mapping, default_mapping):
        """ Mapping result code(which in [] at head of message) to status string on report.
        ex: 
            Mapping Table: 
                   Code          Display      Class Name
                {"Code-123": ["Not Support", "notsupport"]}
            Report:
                        Message           ->       Status     &   Class Name
                "[Code-123]Some message"  ->   "Not Support"  &  "notsupport"
        }
        """
        try:
            # Get message from element object.
            msg = element.get('message', '')
            # Fetch code string from message.
            code_string = re.search(r"\[(.+?)\]", msg).group(1)
            # Mapping code string to status string.
            if isinstance(code_mapping[code_string], basestring):
                return code_mapping[code_string], default_mapping[1] # ex: ("Custom_MSG", "fail")
            return code_mapping[code_string]
        except:
            return default_mapping

    def _save_result_to_file(total_case=0, total_pass=0, total_failure=0, total_error=0, total_skip=0,
                             html_result=None, file_path=result_path):
        try:
            with open(file_path, "w") as f:
                f.write('TOTAL_CASES={}\n'.format(total_case))
                f.write('TOTAL_PASS={}\n'.format(total_pass))
                f.write('TOTAL_FAILS={}\n'.format(total_failure))
                f.write('TOTAL_NOTEXECUTE={}\n'.format(total_error))
                f.write('TOTAL_SKIP={}\n'.format(total_skip))
                f.write('HTML_RESULT={}\n'.format(html_result))
        except Exception as e:
            print 'Failed to save results to file:{0}, error message:{1}'.format(file_path, repr(e))
            raise

    # Parse code_mapping to dict object.
    try:
        if isinstance(code_mapping, basestring):
            code_mapping = json.loads(code_mapping)
    except:
        print 'Unable to parse code_mapping to dict object.'
        code_mapping = None

    # Check Junit xml report.
    if not os.path.isfile(xml_path):
        error_message = 'Unable to find the xml result file:{}'.format(xml_path)
        print error_message
        _save_result_to_file(html_result='<p class="fail">{}</p>'.format(error_message))

    # Parse Junit xml report.
    tree = parse(xml_path)
    root = tree.getroot()
    if root.tag == 'testsuites':
        root = tree.getroot()[0]

    total_cases = int(root.attrib['tests'])
    total_failures = int(root.attrib['failures'])
    total_errors = int(root.attrib['errors'])
    total_skips = int(root.attrib['skipped'])
    print "Executed Cases: {}".format(total_cases)
    print "No. of failed cases: {}".format(total_failures)
    print "No. of non executed cases: {}".format(total_errors)
    print "No. of skipped cases: {}".format(total_skips)
    total_pass = total_cases - total_failures - total_errors - total_skips
    print "No. of passed cases: {}".format(total_pass)
    if total_pass < 0:
        total_pass = 0
    case_result = OrderedDict()
    for case in root.findall('testcase'):
        case_name = case.get('name')
        fail_result = case.find('failure')
        error_result = case.find('error')
        skip_result = case.find('skipped')
        if fail_result is not None:
            case_result[case_name] = get_mapping(
                element=fail_result, code_mapping=code_mapping,
                default_mapping=('Failed', 'fail')
            )
        elif error_result is not None:
            case_result[case_name] = get_mapping(
                element=error_result, code_mapping=code_mapping,
                default_mapping=('NotExecuted', 'error')
            )
        elif skip_result is not None:
            case_result[case_name] = get_mapping(
                element=skip_result, code_mapping=code_mapping,
                default_mapping=('Skipped', 'skipped')
            )
        else:
            case_result[case_name] = ('Pass', 'pass')

    # Generate HTML table.
    html_results = '<table id="report"><tr class="back"><td><b>Test Case</b></td><td><b>Test Result</b></td></tr>'
    for i, name in enumerate(case_result, 1):
        result, class_name = case_result[name]
        print "{:2d} - {:30} : {:15}".format(i, name, result)
        html_results += '<tr><td class="{0}">{1}</td><td class="{0}">{2}</td></tr>'.format(class_name, name, result)
    html_results += '</table>'

    _save_result_to_file(total_cases, total_pass, total_failures, total_errors, total_skips, html_results)


if __name__ == "__main__":
    parser_xml_result()
