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
@click.option('--code_mapping_category', default=None, help='The table to mapping result code to addtional category on report, which is a json string.')
def parser_xml_result(xml_path, result_path, code_mapping, code_mapping_category):

    def _get_code_string(element):
        # Get message from element object.
        msg = element.get('message', '')
        # Fetch code string from message.
        return re.search(r"\[(.+?)\]", msg).group(1)

    def get_mapping(element, default_mapping):
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
            # Fetch code string from element object.
            code_string = _get_code_string(element)
            # Mapping code string to status string.
            if isinstance(code_mapping[code_string], basestring):
                return code_mapping[code_string], default_mapping[1] # ex: ("Custom_MSG", "fail")
            return code_mapping[code_string]
        except:
            return default_mapping

    def move_total_count(move_from, element):
        """ Mapping result code(which in [] at head of message) to specified category, and then
        add total count to mappinged category and subtract the value from move_from.
        ex: 
            Mapping Table: 
                   Code       Category Name
                {"Code-123": "Category_Name"}
            move_from:
                total_failures = 200
            addtional_totals:
                {"Code-Category_Name": 0}
            Result:
                Return 199 and change {"Code-Category_Name": 1}
        }
        """
        try:
            # Fetch code string from element object.
            code_string = _get_code_string(element)
            # Mapping code string to category.
            category = code_mapping_category[code_string]
            addtional_totals[category] += 1
            return move_from-1
        except:
            return move_from

    def _save_result_to_file(total_case=0, total_pass=0, total_failure=0, total_error=0, total_skip=0,
                             html_result=None, file_path=result_path, addtional_totals=None):
        try:
            with open(file_path, "w") as f:
                f.write('TOTAL_CASES={}\n'.format(total_case))
                f.write('TOTAL_PASS={}\n'.format(total_pass))
                f.write('TOTAL_FAILS={}\n'.format(total_failure))
                f.write('TOTAL_NOTEXECUTE={}\n'.format(total_error))
                f.write('TOTAL_SKIP={}\n'.format(total_skip))
                if addtional_totals:
                    for name, total in addtional_totals.iteritems():
                        try:
                            f.write('TOTAL_{}={}\n'.format(name.upper(), total))
                        except Exception as e:
                            print 'Failed to write data:{0}, error message:{1}'.name(name, repr(e))
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
    # Parse code_mapping_category to dict object.
    try:
        if isinstance(code_mapping_category, basestring):
            code_mapping_category = json.loads(code_mapping_category)
    except:
        print 'Unable to parse code_mapping_category to dict object.'
        code_mapping_category = None

    # Init addtional_totals from code_mapping_category.
    # The values of code_mapping_category is the key in addtional_totals.
    addtional_totals = {}
    if code_mapping_category:
        addtional_totals = {v: 0 for v in code_mapping_category.values()}

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

    # Init suite_name.
    suite_name = None

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
        # Here we take testsuites's name as classname of all sub test.
        # But it may need to fix once we has case has different value issue.
        if not suite_name and case.get('classname'):
            suite_name = case.get('classname')
        case_name = case.get('name')
        fail_result = case.find('failure')
        error_result = case.find('error')
        skip_result = case.find('skipped')
        if fail_result is not None:
            case_result[case_name] = get_mapping(
                element=fail_result, default_mapping=('Failed', 'fail')
            )
            total_failures = move_total_count(
                move_from=total_failures, element=fail_result
            )
        elif error_result is not None:
            case_result[case_name] = get_mapping(
                element=error_result, default_mapping=('NotExecuted', 'error')
            )
            total_errors = move_total_count(
                move_from=total_errors, element=error_result
            )
        elif skip_result is not None:
            case_result[case_name] = get_mapping(
                element=skip_result, default_mapping=('Skipped', 'skipped')
            )
            total_skips = move_total_count(
                move_from=total_skips, element=skip_result
            )
        else:
            case_result[case_name] = ('Pass', 'pass')

    if addtional_totals:
        print "--- Total Counts Re-mapping ---"
        print "Executed Cases: {}".format(total_cases)
        print "No. of failed cases: {}".format(total_failures)
        print "No. of non executed cases: {}".format(total_errors)
        print "No. of skipped cases: {}".format(total_skips)
        for name, total in addtional_totals.iteritems():
            try:
                print "No. of additional {} cases: {}".format(name, total)
            except Exception as e:
                print 'Failed to print data:{0}, error message:{1}'.name(name, repr(e))
        print "No. of passed cases: {}".format(total_pass)

    # Generate HTML table.
    html_results = '<table id="report"><tr class="back"><td><b>Test Case</b></td><td><b>Test Result</b></td></tr>'
    for i, name in enumerate(case_result, 1):
        result, class_name = case_result[name]
        print "{:2d} - {:30} : {:15}".format(i, name, result)
        # Generate Jenkins link.
        reason_link = ''
        if class_name in ['fail', 'error', 'skipped'] and os.environ.get('BUILD_URL'): # Only available in Jenkins.
            reason_link = '<a href="{0}testReport/(root)/{1}/{2}/">'.format(
                os.environ['BUILD_URL'], suite_name, re.sub(r'[^a-zA-Z0-9]', '_', name)) # Only test name need to replace space by "_".
        html_results += '<tr><td class="{0}">{1}</td><td class="{0}">{3}{2}</td></tr>'.format(class_name, name, result, reason_link)
    html_results += '</table>'

    _save_result_to_file(total_cases, total_pass, total_failures, total_errors, total_skips, html_results,
        addtional_totals=addtional_totals)


if __name__ == "__main__":
    parser_xml_result()
