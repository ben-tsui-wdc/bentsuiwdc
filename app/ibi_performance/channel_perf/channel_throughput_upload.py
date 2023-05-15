# -*- coding: utf-8 -*-
""" kpi test for multiprocess uploading by REST API.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import multiprocessing
import numpy
import os
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.restAPI import RestAPI
from ibi_performance.tool.html import HtmlFormat


class channel_throughput_upload(TestCase):
    TEST_SUITE = 'Performance_Tests'
    TEST_NAME = 'kpi_channel_throughput_upload'
    SETTINGS = {
        'uut_owner': False, # Disbale restAPI.
        'adb': False,
        'power_switch': False,
    }


    # Pre-defined parameters for IntegrationTest
    def declare(self):

        self.mac_address = None
        self.folder_path = None
        self.connection_type = None
        self.thread_number = None      
        self.chunk_size = None
        self.timeout = 14400
        self.environment_elapsed_time = 7200
        self.test_result_list = []
        self.html_format = 1

        self.total_FileSz = 0
        self.total_upload_ElapsT = 0
        self.total_file_id_list = []
        self.total_file_name_list = []


    def _upload(self, file_path=None, file_name=None, parent_folder=None, upload_chunk_size=None):
        with open(file_path, 'rb') as file_object:
            file_object.seek(0, 2) # Seek to end of file.
            FileSz = file_object.tell()

            start_time = time.time()
            print "file_path: {}".format(file_path)
            file_id, temp = self.uut_owner.chuck_upload_file(file_object=file_object, file_name=file_name, parent_folder=parent_folder, upload_chunk_size=int(upload_chunk_size))
            ending_time = time.time()
            ElapsT = ending_time - start_time

            #print '@ # $ ' * 10
            print "file_id: {}".format(file_id)
            print "FileSz: {} MB".format(FileSz/(1024*1024))
            print "ElapsT: {0:.2f} sec".format(ending_time - start_time)
            print "AvgUploadSpd_per_file: {0:.2f} MB/s".format((FileSz/(1024*1024))/ElapsT)
            #print '@ # $ ' * 10

        #self.total_FileSz += FileSz
        #self.total_upload_ElapsT += ElapsT
        #self.total_file_id_list.append(file_id)
        #self.total_file_name_list.append(file_path.split('/')[-1])


    def start_upload(self, parent_folder=None, upload_chunk_size=None, index=None, multiprocessing_file_path_list=None, lock=None):
        while True:
            if multiprocessing_file_path_list:
                print '\n'
                #print "file_path_list_original: {}".format(multiprocessing_file_path_list) 
                lock.acquire()
                file_path = multiprocessing_file_path_list[0]
                multiprocessing_file_path_list.pop(0)
                lock.release()
                #print "file_path_list_remain: {}".format(multiprocessing_file_path_list) 
                file_name = file_path.split('/')[-1]
                print "Process index: {}".format(index)
                self._upload(file_path=file_path, file_name=file_name, parent_folder=parent_folder, upload_chunk_size=upload_chunk_size)
                print '\n'
            else:
                break


    def before_loop(self):
        if not self.thread_number:
            raise self.err.StopTest("Please sepcify thread_number.")
        if not self.mac_address:
            raise self.err.StopTest("Please sepcify device mac address.")
        self.uut['mac_address'] = self.mac_address

        '''
            Get self.uut_owner.url_prefix
        '''
        self.uut_owner = RestAPI(uut_ip=None, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
        self.uut_owner.environment.update_service_urls()

        # Set socket timeout as 10 seconds
        self.uut_owner.set_global_timeout(timeout=10)

        # Set retry delay of http request: 1 second
        self.uut_owner.set_retry_delay(retry_delay=1)

        # To make conncetion persistent.
        self.uut_owner._persistent_connection = False

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
                    self.internal_url = i.get('network').get('internalURL')
                    print "\n"
                    print 'firmware: {}'.format(self.uut['firmware'])
                    print 'model: {}'.format(self.uut['model'])
                    print 'mac_address: {}'.format(i.get("mac"))
                    print 'proxyURL: {}'.format(self.proxy_url)
                    print 'portForwardURL: {}'.format(self.port_forward_url)
                    print 'internalURL: {}'.format(self.internal_url)
                    print 'The connection_type for this run is: {}'.format(self.connection_type)
                    print "\n"
                    break
            if self.connection_type == 'proxy':
                self.uut_owner.url_prefix = self.proxy_url  ######## Important
            elif self.connection_type == 'port_forward':
                self.uut_owner.url_prefix = self.port_forward_url
            elif self.connection_type == 'local':
                self.uut_owner.url_prefix = self.internal_url  # For local run
        else:
            pass  # Need to do error handle


    def before_test(self):
        # Delete the old dataset folder
        folder_name = self.folder_path.split('/')[-1]
        data_id_dict = None
        try:
            data_id_dict, page_token = self.uut_owner.get_data_id_list(type='folder', parent_id='root')
        except Exception as e:  # The folder may be already deleted.
            print e
        if data_id_dict:
            data_id = data_id_dict.get(folder_name, None)
            if data_id:
                self.uut_owner.delete_file(data_id)

        # Create a new dataset folder
        folder_id = self.uut_owner.commit_folder(folder_name)
        self.folder_name = folder_name

        # Create a list including all file paths
        self.file_path_list = []
        #for root, dirs, files in os.walk(self.folder_path):  # For ./run.sh
        for root, dirs, files in os.walk(folder_name):  # For ./start.sh
            for f in files:
                file_path = os.path.join(root, f)
                # print(fullpath)
                self.file_path_list.append(file_path)


    def _test(self):
        print 'YYY ' * 20
        print 'YYY ' * 20
        pass


    # main function
    def test(self):
        total_FileSz = 0  # byte

        # Create lock for multiprocessing
        lock = multiprocessing.Lock()
        # Create shared resource for multiprocessing
        multiprocessing_file_path_list = multiprocessing.Manager().list() 
        for file_path in self.file_path_list:
            multiprocessing_file_path_list.append(file_path)
            # sum up the size of all files
            with open(file_path, 'rb') as file_object:
                file_object.seek(0, 2) # Seek to end of file.
                total_FileSz += file_object.tell()

        process_list = []
        for index in xrange(int(self.thread_number)):
            process_list.append(multiprocessing.Process(target=self.start_upload, args=(self.folder_name, self.chunk_size, index, multiprocessing_file_path_list, lock)))


        start_time = time.time()
        for process in process_list:
            process.start()
        for process in process_list:
            process.join()
        ending_time = time.time()

        FileSz = total_FileSz/float(1024*1024)
        UpElapsT = ending_time - start_time
        UpAvgSpd = FileSz/UpElapsT
        print "XX Overall Result " * 10
        print "FileSz: {0:.2f} MB".format(FileSz)
        print "UpElapsT: {} seconds".format(UpElapsT)
        print "UpAvgSpd: {} MB/s".format(UpAvgSpd)
        print  "XX Overall Result  " * 10

        self.data.test_result['DataType'] = self.folder_path.split('/')[-1]
        self.data.test_result['DeviceSz'] = self.device_size()
        self.data.test_result['ConType'] = self.connection_type
        self.data.test_result['Thread'] = self.thread_number
        self.data.test_result['ChunkSz'] = int(self.chunk_size)/1024
        self.data.test_result['FileNum'] = len(self.file_path_list)
        self.data.test_result['FileSz'] = '{0:.2f}'.format(FileSz)
        self.data.test_result['UpElapsT'] = '{0:.2f}'.format(UpElapsT)
        self.data.test_result['EnvUpAvgSpd'] = self.environment_upload_avg
        self.data.test_result['UpAvgSpd'] = '{0:.2f}'.format(UpAvgSpd)


    def device_size(self):
        resp = self.uut_owner.get_device()
        if resp.status_code == 200:
            temp = resp.json().get('storage').get('capacity')  #temp is device_size in bytes.
            return '{0:.0f}'.format(float(temp)/1000000000000)
        else:
            return None


    def _after_test(self):
        self.test_result_list.append(self.data.test_result)

    def after_test(self):
        # Append every test result of iteration
        self.test_result_list.append(self.data.test_result)

        # Delete the old dataset folder
        folder_name = self.folder_path.split('/')[-1]
        data_id_dict = None
        try:
            data_id_dict, page_token = self.uut_owner.get_data_id_list(type='folder', parent_id='root')
        except Exception as e:  # The folder may be already deleted.
            print e
        if data_id_dict:
            data_id = data_id_dict.get(folder_name, None)
            if data_id:
                self.uut_owner.delete_file(data_id)


    def after_loop(self):
        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '1':
            html_inst.table_title_column = ['product', 'build', 'DeviceSz', 'ConType', 'Thread', 'ChunkSz', 'FileNum', 'FileSz', 'iteration', 'UpElapsT', 'EnvUpAvgSpd', 'UpAvgSpd',]
            html_inst.table_title_column_extend = ['UpAvgSpd']
        elif self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'ConType', 'Thread', 'iteration', 'EnvUpAvgSpd', 'UpAvgSpd',]
            html_inst.table_title_column_extend = ['result']
        html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)


if __name__ == '__main__':

    parser = InputArgumentParser("""\
        Examples: ./run.sh ibi_performance/channel_perf/channel_perf/channel_throughput_upload.py \
        --mac_address 00:14:EE:0C:6C:37 --folder_path dataset_mix_test --connection_type local  \
        --thread_number 8  --chunk_size 8388608 --environment_download_avg 3 --loop_times 2  \
        --cloud_env qa1 --username jason.chiang@wdc.com --password 'Wdctest1234' \
        --disable_get_log_metrics --disable_export_logcat_log --disable_upload_logs --dry_run \
        --debug_middleware --stream_log_level DEBUG   --html_acronym_desc  "Jason test"
        """)

    # Note that SERIAL CLIENT is necessary if usb_slurp_type == 'to_drive' 
    parser.add_argument('--mac_address', help='specify which device to be tested', default=None)
    parser.add_argument('--folder_path', help='specify the folder_path of source dataset which is transferred.', default=None)
    parser.add_argument('--connection_type', help='specify the connection_type', choices=['proxy', 'port_forward', 'local'], default='proxy')
    parser.add_argument('--thread_number', help='the number of thread for transferring files', default=None)
    parser.add_argument('--chunk_size', help='the chunk_size (bytes) of transferring files, default is 8388608 bytes(8MB)', default=8388608)
    parser.add_argument('--timeout', help='specify the timeout of usb import.', default=14400)
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--environment_upload_avg', help='environment_upload_avg', default='3')
    parser.add_argument('--html_format', help='the html format for test result', default='1', choices=['1', '2'])


    test = channel_throughput_upload(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)