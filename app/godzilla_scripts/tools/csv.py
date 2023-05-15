# -*- coding: utf-8 -*-
""" kpi test for usb import throughput.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import numpy

# platform modules
from platform_libraries import common_utils


class CsvFormat():
    
    def __init__(self):
        self.log = common_utils.create_logger(stream_log_level=10)
        self.csv_title_column = None
        self.integer_item = ['executionTime', 'count']


    def csv_table(self, test_result_list=None, results_folder=None):
        result_csv = ''

        for item in self.csv_title_column:
            value = 0


            for element in test_result_list:
                # To sum all values up for identical 'item's if element.get(item) is float 
                try:
                    value += float(element.get(item))
                # Otherwise, element.get(item) is not a float. Maybe it is string or None.
                except Exception as e:
                    if item =='FileType':
                        if '5gb_single_file' in element.get(item):
                            value = 'Single Large'
                        elif '5gb_mix_dvd_file' in element.get(item):
                            value = 'Multiple Large Files'
                        elif '5GB_pics_benchmark' in element.get(item):
                            value = 'Photos'
                        else:
                            value = element.get(item)
                    else:
                        value = element.get(item)
                    break

     
            # Output to csv file
            if isinstance(value, float):
                real_value_average = value/len(test_result_list)  # Since this table is for summary, calculate the average
                if item in self.integer_item:
                    result_csv +=  '{:.0f},'.format(real_value_average)  # round off to integer
                else:
                    result_csv +=  '{:.1f},'.format(real_value_average)  # round off to the 1st decimal place
            else:   
                result_csv +=  '{},'.format(value)  # String

        # Output a HTML file
        with open('{}/result.csv'.format(results_folder), 'a') as f:
            f.write(result_csv + '\r\n')