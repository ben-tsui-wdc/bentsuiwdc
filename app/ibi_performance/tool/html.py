# -*- coding: utf-8 -*-
""" kpi test for usb import throughput.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import numpy

# platform modules
from platform_libraries import common_utils


class HtmlFormat():
    
    def __init__(self):
        self.log = common_utils.create_logger(stream_log_level=10)

        # The following is for html_table
        self.html_style = '<style>#report, th, td {border: 1px solid black;border-collapse: collapse;text-align: left;padding: 7px; font-family: "Arial"; font-size: 14px;}caption{font-weight: bold; text-align: left;padding: 5px; color: #555;text-transform: uppercase;} .report-name{width: 180px;text-align: center;line-height: 46px;font-weight: bold;} .nav{color: #fff;background-color: #1976D2;height: 48px;font-family: "Arial"; font-size: 14px; } .left-column{text-transform: uppercase;background-color: #1976D2;color: #fff;}.right-column{background-color: #fff;color: #1A231E;} table.details th{background-color: #1976D2;color: #fff;} .more-details th{background-color: black!important;border: 1px solid white!important;} .passed{color: #2E8B57;} .passrate{font-weight: bold;} .failed{background-color: #DC143C; color: white;} .skipped{color: #FF7F50;} .failed_style_2{color: red; font-weight: bold;} .passed_style_2{color: green; font-weight: bold;}</style>'
        self.html_head = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Performance Automation Summary Report</title>{}</head>'.format(self.html_style)
        self.html_table_id = '<table id="report" class="details">'
        self.html_acronym = ''
        self.html_acronym_dict = {
                'DeviceSz':'device disk size', 
                'ConType':'connection type',
                'SlurpType':'USB slurp type',
                'Thread':'number of thread when transferring files', 
                'ChunkSz':'chunck size (KB)', 
                'FileNum': 'number of testing files', 
                'FileSz':'testing file size (MB)',
                'UpElapsT':'upload elapsed time (sec)', 
                'EnvUpAvgSpd':'upload average speed (MB/s) for environment',
                'TargetUpAvgSpd':'target of upload average speed (MB/s)',
                'UpAvgSpd':'upload average speed (MB/s)', 
                'Max':'maximum', 
                'Min':'minimum', 
                'Stdev':'standard deviation',
                'DownElapsT':'download elapsed time (sec)',
                'EnvDownAvgSpd':'download average speed (MB/s) for environment',
                'TargetDownAvgSpd':'target of download average speed (MB/s)',
                'DownAvgSpd':'download average speed (MB/s)',
                'ErrCnt':'errorCount in REST response', 
                'EnvElapsT':'elapsed time (sec) for environment',
                'TargetElapsT':'target of elapsed time (sec)', 
                'ElapsT':'elapsed time (sec)', 
                'EnvAvgSpd':'average speed (MB/s) for environment',
                'TargetAvgSpd':'target of average speed (MB/s)',
                'AvgSpd':'average speed (MB/s)',
                'CopyAvgSpd':'file copied average speed (MB/s)',
                # For restsdk index
                'TotalIndexedFiles': 'indexed files by filesystem',
                'TotalSkipped': 'skipped files by filesystem when indexing',
                'IndexSpeed': 'average index time per file (seccond/file)',
                }
        self.html_acronym_desc = ''  # Additional information which can be input by user
        self.table_title_column = ''
        self.table_title_column_extend = ''


    def max(self, test_result_list=None, keyword=None):
        temp = []
        for element in test_result_list:
            temp.append(float(element.get(keyword, 0)))
        return '{0:.2f}'.format(max(temp))

    def min(self, test_result_list=None, keyword=None):
        temp = []
        for element in test_result_list:
            temp.append(float(element.get(keyword, 0)))
        return '{0:.2f}'.format(min(temp))

    def std(self, test_result_list=None, keyword=None):
        temp = []
        for element in test_result_list:
            temp.append(float(element.get(keyword, 0)))

        return '{0:.2f}'.format(numpy.std(temp))


    def html_table(self, test_result_list=None, results_folder=None):
        '''
            ### Generate a simple HTML report and title column list ###
        '''

        #print '\nGenerate a HTML report.\n'
        self.log.warning('Generate a HTML report.')

        # Title column, it is hard code. tds will be filled table out by html_table_th.
        # This fields here are the same as the test_result_list which is raw data.
        table_title_column = self.table_title_column

        # html_table_th is the title column.
        temp = ''
        for item in table_title_column:
            temp += '<th>{}</th>'.format(item)
        html_table_th = temp
        
        # html_table_tds is the content of test result
        temp = ''
        for element in test_result_list:
            temp += '<tr>'
            for item in table_title_column:
                pass_fail_status = ''  # To decide pass or fail

                # 1) If the value is float/integer, compare with target if target exists
                target_value = None  # Target value for comparison
                if element.get('Env{}'.format(item), None):
                    target_value = element.get('Env{}'.format(item))  # Target of something. For example, "EnvUpAvgSpd"
                elif element.get('Target{}'.format(item), None):
                    target_value = element.get('Target{}'.format(item))  # Target of something. For example, "TargetAvgSpd"
                if target_value:
                    real_value = element.get(item)
                    # Confirm if the item of table_title_column is "elapsed_time" or something else.
                    if item == 'ElapsT':
                        if float(real_value) > float(target_value):  # real elasped time is more than target_elapsed _time
                            pass_fail_status = ' class="failed"'
                    else:
                        if float(real_value) < float(target_value):  # real performance number is lower than target
                            pass_fail_status = ' class="failed"'

                # 2) if the element.get(item) is a string, check if there is a keyword for fail
                if isinstance(element.get(item), str) and 'fail' in element.get(item).lower():
                    pass_fail_status = ' class="failed"'

                temp += '<td{}>{}</td>'.format(pass_fail_status, element.get(item, None))

            temp += '</tr>'
        html_table_tds = temp




        #########################   table summary   ##############################

        # html_table_th_summary is the title column for summary.
        table_title_column_extend = self.table_title_column_extend

        temp = ''
        # for <th> of table_title_column
        for item in table_title_column:
            temp += '<th>{}</th>'.format(item)
        # for <th> of table_title_column_extend
        for item in table_title_column_extend:
            if item in ['Result', 'result']:
                temp += '<th>{}</th>'.format(item)
            else:
                for sub_item in ['Max', 'Min', 'Std']:  #This is hardcode. Need to think how to make it better. 
                    temp += '<th>{} ({})</th>'.format(item, sub_item)

        html_table_th_summary = temp


        # html_table_tds_summary is the content of test result for summary
        temp = ''
        # for <td> of table_title_column
        pass_status_summary = True  # To decide pass or fail for summary table
        for item in table_title_column:
            value = 0
            pass_fail_status = ''  # To decide pass or fail
            target_value = None  # Target value for comparison

            for element in test_result_list:

                # To sum all values up for identical 'item's if element.get(item) is float 
                try:
                    value += float(element.get(item))
                    if element.get('Env{}'.format(item), None):
                        target_value = element.get('Env{}'.format(item))  # Target of something. For example, "EnvUpAvgSpd"
                    elif element.get('Target{}'.format(item), None):
                        target_value = element.get('Target{}'.format(item))  # Target of something. For example, "TargetUpAvgSpd"
                # Otherwise, element.get(item) is not a float. Maybe it is string or None.
                except Exception as e:
                    if item == 'iteration':
                        value = element.get(item).split('_itr_')[1]
                    else:
                        value = element.get(item)
                        if isinstance(value, str) and 'fail' in value.lower():
                            break

            if isinstance(value, float):
                # To compare real_value_average with target_value
                real_value_average = value/len(test_result_list)  # Since this table is for summary, calculate the average
                if target_value:
                    if item == 'ElapsT':
                        if float(real_value_average) > float(target_value):  # real elasped time is more than target_elapsed _time
                            pass_fail_status = 'class="failed"'
                            pass_status_summary = False
                    else:
                        if float(real_value_average) < float(target_value):  # real performance number is lower than target
                            pass_fail_status = 'class="failed"'
                            pass_status_summary = False
                temp += '<td {}>{:.1f}</td>'.format(pass_fail_status, real_value_average)
            elif isinstance(value, str) and 'fail' in value.lower():
                pass_fail_status = 'class="failed"'
                pass_status_summary = False
                temp += '<td {}>{}</td>'.format(pass_fail_status, value)
            else:
                temp += '<td {}>{}</td>'.format(pass_fail_status, value)

        # for <td> of table_title_column_extend
        for keyword in table_title_column_extend:
            if keyword in ['Result', 'result']:
                if not pass_status_summary:
                    temp += '<td {}>{}</td>'.format('class="failed_style_2"', 'FAIL')
                else:
                    temp += '<td {}>{}</td>'.format('class="passed_style_2"', 'PASS')
            else:
                for element in ['Max', 'Min', 'Std']:  #This is hardcode. Need to think how to make it better. 
                    if element == 'Max':
                        temp += '<td>{}</td>'.format(self.max(test_result_list=test_result_list, keyword=keyword))
                    elif element == 'Min':
                        temp += '<td>{}</td>'.format(self.min(test_result_list=test_result_list, keyword=keyword))
                    elif element == 'Std':
                        temp += '<td>{}</td>'.format(self.std(test_result_list=test_result_list, keyword=keyword))
        html_table_tds_summary = temp

        # Two tables.
        html_table_all = self.html_table_id + '<tr>{}</tr>'.format(html_table_th) + html_table_tds + '</table>'
        html_table_summary = self.html_table_id + '<tr>{}</tr>'.format(html_table_th_summary) + '<tr>{}</tr>'.format(html_table_tds_summary) + '</table>'

        # Merge all tables into a html file
        if not self.html_acronym:
            for keyword in self.table_title_column:
                value = self.html_acronym_dict.get(keyword, None)
                if value:
                    self.html_acronym += '<br><b>{}: </b>{}'.format(keyword, value)
        for keyword in table_title_column_extend:
            if keyword not in ['Result', 'result']:
                self.html_acronym +='<br><b>Max: </b>maximum<br><b>Min: </b>minimum<br><b>Std: </b>standard deviation'
                break
        if self.html_acronym_desc:
            self.html_acronym = '<br><b>{}</b>{}'.format(self.html_acronym_desc, self.html_acronym)

        result_html = self.html_head + '\n\n' + self.html_acronym + html_table_all + '\n\n' + '<div>&nbsp;</div><b>Summary</b>' + html_table_summary

        # Output a HTML file
        with open('{}/html_acronym'.format(results_folder), 'a') as f:
            f.write(self.html_acronym)
        with open('{}/html_table_th'.format(results_folder), 'a') as f:
            f.write(html_table_th)
        with open('{}/html_table_tds'.format(results_folder), 'a') as f:
            f.write(html_table_tds)
        with open('{}/html_table_th_summary'.format(results_folder), 'a') as f:
            f.write(html_table_th_summary)
        with open('{}/html_table_tds_summary'.format(results_folder), 'a') as f:
            f.write(html_table_tds_summary)
        with open('{}/result_html'.format(results_folder), 'a') as f:
            f.write(result_html)
        with open('{}/result_html.html'.format(results_folder), 'a') as f:
            f.write(result_html)

        return pass_status_summary