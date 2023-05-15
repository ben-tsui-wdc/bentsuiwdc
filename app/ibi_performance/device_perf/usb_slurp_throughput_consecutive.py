# -*- coding: utf-8 -*-
""" kpi test for usb import throughput consecutively.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import numpy
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.restAPI import RestAPI
from bat_scripts_new.factory_reset import FactoryReset
from ibi_performance.tool.html import HtmlFormat

class usb_slurp_throughput(TestCase):
    TEST_SUITE = 'Performance_Tests'
    TEST_NAME = 'kpi_usb_slurp_throughput'
    SETTINGS = {
        'uut_owner': False, # Disbale restAPI.
        'adb': False,
        'power_switch': False,
    }

    # Pre-defined parameters for IntegrationTest
    def declare(self):
        self.usb_slurp_type = None      
        self.folder_name = None
        self.timeout = 28800
        self.no_factory_reset = False
        self.environment_elapsed_time = 7200
        self.environment_usb_slurp_avg = 20
        self.test_result_list = []
        self.folder_id_list = []
        self.clear_data_after_test = False
        self.html_format = 1


    def before_loop(self):
        if not self.usb_slurp_type:
            raise self.err.StopTest("Please sepcify usb_slurp_type & device mac address.")

        '''
            Get self.uut_owner.url_prefix
        '''
        self.uut['mac_address'] = self.mac_address
        self.uut_owner = RestAPI(uut_ip=None, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
        
        self.uut_owner.environment.update_service_urls()

        temp =  self.uut_owner.get_devices_info_per_specific_user()        
        if temp:
            for i in temp:
                if i.get("mac") == self.uut.get('mac_address').lower():
                    print i
                    self.uut['firmware'] = i.get('firmware').get('wiri')
                    self.uut['model'] = i.get('type')
                    self.uut['environment'] = self.env.cloud_env
                    self.proxy_url = i.get('network').get('proxyURL') 
                    self.port_forward_url = i.get('network').get('portForwardURL')
                    print "\n"
                    print 'firmware: {}'.format(self.uut['firmware'])
                    print 'model: {}'.format(self.uut['model'])
                    print 'mac_address: {}'.format(i.get("mac"))
                    print 'proxyURL: {}'.format(i.get('network').get('proxyURL'))
                    print 'portForwardURL: {}'.format(i.get('network').get('portForwardURL'))
                    print "\n"
                    break
            self.uut_owner.url_prefix = self.proxy_url  ######## Important
        else:
            pass  # Need to do error handle
        
        # Get usb_info
        self.usb_info = self.uut_owner.get_usb_info()
        print "usb_info['name']: {}".format(self.usb_info['name'])
        print "usb_info['id']: {}".format(self.usb_info['id'])


    def before_test(self):
        '''
            # Create the folder which is prepared for slurp.
        '''
        if self.usb_slurp_type == 'from_drive':
            self.folder_id_list.append(self.uut_owner.commit_folder('{}_{}'.format(self.folder_name, self.env.iteration)))
            print "iteration: {}".format(self.env.iteration)
            print 'self.folder_id_list: {}'.format(self.folder_id_list)
        elif self.usb_slurp_type == 'to_drive':
            pass


    # main function
    def test(self):
        # Trigger usb import
        try:
            if self.usb_slurp_type == 'from_drive':
                copy_id, usb_info, result = self.uut_owner.usb_slurp(usb_name=None, folder_name=self.folder_name, dest_parent_id=self.folder_id_list[self.env.iteration-1], timeout=self.timeout, wait_until_done=True)
            elif self.usb_slurp_type == 'to_drive':
                copy_id, usb_info, result = self.uut_owner.usb_export(usb_name=None, folder_name=self.folder_name, timeout=self.timeout, wait_until_done=True)
        except Exception as ex:
            raise self.err.TestError('trigger_usb_import({}) Failed!! Err: {}'.format(self.usb_slurp_type, ex))

        usb_import_elapsed_time = result['elapsedDuration']
        usb_import_total_byte = result['totalBytes']
        usb_import_total_size = int(usb_import_total_byte)/1024/1024
        usb_import_avg = usb_import_total_size/usb_import_elapsed_time
        self.data.test_result['data_type'] = self.folder_name
        self.data.test_result['SlurpType'] = self.usb_slurp_type
        self.data.test_result['DeviceSz'] = self.ibi_size()
        self.data.test_result['ErrCnt'] = result['errorCount']
        self.data.test_result['FileNum'] = result['copiedCount']
        self.data.test_result['FileSz'] = '{0:.2f}'.format(usb_import_total_size)
        self.data.test_result['ElapsT'] = '{0:.2f}'.format(usb_import_elapsed_time)
        self.data.test_result['AvgSpd'] = '{0:.2f}'.format(usb_import_avg)
        self.data.test_result['EnvElapsT'] = int(self.environment_elapsed_time)
        self.data.test_result['EnvAvgSpd'] = int(self.environment_usb_slurp_avg)
        

    def ibi_size(self):
        resp = self.uut_owner.get_device()
        if resp.status_code == 200:
            temp = resp.json().get('storage').get('capacity')  #temp is ibi_size in bytes.
            return '{0:.0f}'.format(float(temp)/1000000000000)
        else:
            return None


    def after_test(self):
        self.test_result_list.append(self.data.test_result)


    def after_loop(self):
        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '1':
            html_inst.table_title_column = ['product', 'build', 'DeviceSz', 'SlurpType', 'FileNum', 'FileSz', 'iteration', 'ErrCnt', 'EnvElapsT', 'ElapsT', 'EnvAvgSpd', 'AvgSpd',]
            html_inst.table_title_column_extend = ['AvgSpd']
        elif self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'iteration', 'SlurpType', 'ErrCnt', 'EnvAvgSpd', 'AvgSpd',]
            html_inst.table_title_column_extend = ['result']
        html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # Delete all folder which are slurped to device
        if self.clear_data_after_test:
            for folder_id in self.folder_id_list:
                self.uut_owner.delete_file(folder_id)


if __name__ == '__main__':

    parser = InputArgumentParser("""\
        *** USB slurp test on Kamino Android ***
        Examples: ./run.sh performance_tests/usb_slurp_throughput.py --uut_ip 10.92.224.13 \
        --cloud_env qa1 --data_type single --loop_times 3 --debug_middleware --dry_run\
        (optional)--serial_server_ip fileserver.hgst.com --serial_server_port 20015
        """)
    # Note that SERIAL CLIENT is necessary if usb_slurp_type == 'to_drive' 
    parser.add_argument('--usb_slurp_type', help='from_drive/to_drive', default=None)
    parser.add_argument('--mac_address', help='specify which device to be tested', default=None)
    parser.add_argument('--folder_name', help='specify the folder_name which is usb imported.', default=None)
    parser.add_argument('--timeout', help='specify the timeout of usb import.', default=28800)
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--no_factory_reset', help='Don\'t execute factory_reset.', action='store_true')
    parser.add_argument('--environment_elapsed_time', help='environment_elapsed_time', default='7200')
    parser.add_argument('--environment_usb_slurp_avg', help='environment_usb_slurp_avg', default='20')
    parser.add_argument('--clear_data_after_test', help='clear dataset after test finished', default='store_true')
    parser.add_argument('--html_format', help='the html format for test result', default='1', choices=['1', '2'])

    test = usb_slurp_throughput(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)