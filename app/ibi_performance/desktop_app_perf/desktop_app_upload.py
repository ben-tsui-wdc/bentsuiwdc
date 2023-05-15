# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import ast
import os
import subprocess
import sys
import time


# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.desktop_sync import DESKTOP_SYNC
from platform_libraries.restAPI import RestAPI
from ibi_performance.tool.html import HtmlFormat


class DesktopAppPerf(TestCase):

    TEST_SUITE = 'desktop_app_perf'
    TEST_NAME = 'desktop_app_perf'
    SETTINGS = {
        'uut_owner': False, # Disbale restAPI.
        'adb': False,
        'power_switch': False,
    }


    def declare(self):
        self.test_result_list = []
        self.html_format = 1


    def init(self):
        if not self.mac_address:
            raise self.err.StopTest("Please specify device mac address.")
        self.uut['mac_address'] = self.mac_address

        self.uut_owner = RestAPI(uut_ip=None, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
        self.kdd_obj = DESKTOP_SYNC(client_os=self.client_os,
                                      client_ip=self.client_ip.strip(),
                                      client_username=self.client_username,
                                      client_password=self.client_password,
                                      rest_obj=self.uut_owner)
        
        self.uut_owner.environment.update_service_urls()
        self.uut_owner.set_global_timeout(timeout=7200)

        temp =  self.uut_owner.get_devices_info_per_specific_user()        
        if temp:
            for i in temp:
                if i.get("mac") == self.uut.get('mac_address').lower():
                    print i
                    self.uut['firmware'] = i.get('firmware').get('wiri')
                    self.uut['model'] = i.get('type')
                    self.uut['environment'] = self.env.cloud_env
                    self.uut['device_id'] = i.get('deviceId')
                    self.proxy_url = i.get('network').get('proxyURL') 
                    self.port_forward_url = i.get('network').get('portForwardURL')
                    self.internal_url = i.get('network').get('internalURL')
                    print "\n"
                    print 'firmware: {}'.format(self.uut['firmware'])
                    print 'model: {}'.format(self.uut['model'])
                    print 'mac_address: {}'.format(i.get("mac"))
                    print 'device_id: {}'.format(self.uut['device_id'])
                    print 'proxyURL: {}'.format(self.proxy_url)
                    print 'portForwardURL: {}'.format(self.port_forward_url)
                    print 'internalURL: {}'.format(self.internal_url)
                    #print 'The connection_type for this run is: {}'.format(self.connection_type)
                    print "\n"
                    break
            self.uut_owner.url_prefix = self.proxy_url  ######## Important
        else:
            pass  # Need to do error handle


    def before_loop(self):
        self.kdd_obj.connect()
        # The mount path of virtual drive provided by Desktop App
        self.drive_mount_path = self.kdd_obj.get_mount_path(device_id=self.uut['device_id'])
        if not self.drive_mount_path:
            raise self.err.TestError('There is no designated drive mounted on {} client({})\n'.format(self.client_os, self.client_ip.strip()))
        print '\ndrive_mount_path by Desktop App: "{}" on {} client({})\n'.format(self.drive_mount_path, self.client_os, self.client_ip.strip())

        # Configuration for different client_os
        if self.client_os == 'MAC':
            self.dest_path = "{}/{}".format(self.drive_mount_path, self.source_path.split("/")[-1])
            self.DataType = self.source_path.split("/")[-1]  # Not sure if "DataType" is necessary.
        elif self.client_os == 'WIN':
            self.dest_path = "{}:\\{}".format(self.drive_mount_path, self.source_path.split("\\")[-1])  
            self.DataType = self.source_path.split("\\")[-1]  # Not sure if "DataType" is necessary.


    def before_test(self):
        # Delete testing file in target device before transferring started.
        self.kdd_obj.delete_folder(self.dest_path)


    def test(self):
        FileSz = self.kdd_obj.get_file_size(file_path=self.source_path)  # By default the unit is MB
        UpAvgSpd = self.kdd_obj.file_transfer(source_path=self.source_path, dest_path=self.dest_path)  # MB/s
        UpElapsT = FileSz/UpAvgSpd

        print "XX Overall Upload Result " * 10
        print "FileSz: {0:.2f} MB".format(FileSz)
        print "UpElapsT: {0:.2f} seconds".format(UpElapsT)
        print "UpAvgSpd: {0:.2f} MB/s".format(UpAvgSpd)
        print  "XX Overall Upload Result  " * 10

        self.data.test_result['DataType'] = self.DataType
        self.data.test_result['DeviceSz'] = self._device_size()
        self.data.test_result['Client'] = self.client_os
        self.data.test_result['ConType'] = self.connection_type
        self.data.test_result['FileNum'] = 'reserved'
        # self.data.test_result['FileNum'] = len(self.file_path_list)
        self.data.test_result['FileSz'] = '{0:.2f}'.format(FileSz)
        self.data.test_result['UpElapsT'] = '{0:.2f}'.format(UpElapsT)
        self.data.test_result['EnvUpAvgSpd'] = self.environment_upload_avg
        self.data.test_result['UpAvgSpd'] = '{0:.2f}'.format(UpAvgSpd)


    def after_test(self):
        self.test_result_list.append(self.data.test_result)
        # Delete testing file in target device after transferring completed.
        self.kdd_obj.delete_folder(self.dest_path)
        print 'Wait for 300 seconds after deleting testing files'
        time.sleep(300)


    def after_loop(self):        
        # Disconnect testing client at the end
        self.kdd_obj.disconnect()

        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '1':
            html_inst.table_title_column = ['product', 'build', 'DeviceSz', 'Client', 'ConType', 'FileNum', 'FileSz', 'iteration', 'UpElapsT', 'EnvUpAvgSpd', 'UpAvgSpd',]
            html_inst.table_title_column_extend = ['UpAvgSpd']
        elif self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'Client', 'ConType', 'iteration', 'EnvUpAvgSpd', 'UpAvgSpd',]
            html_inst.table_title_column_extend = ['result']
        html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)


    def _device_size(self):
        resp = self.uut_owner.get_device()
        if resp.status_code == 200:
            temp = resp.json().get('storage').get('capacity')  #temp is device_size in bytes.
            return '{0:.0f}'.format(float(temp)/1000000000000)
        else:
            return None


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Desktop_Sync_BAT on Kamino Android ***
        Examples: ./run.sh desktop_sync_tests/integration_tests/kdd_perf_bat.py\
                  --uut_ip 10.136.137.159 --username kdd_perf_bat@test.com \
                  --client_os "MAC" --client_ip 10.92.234.61 --client_username "user" --client_password "pass"\
                  --app_version 1.1.0.14 --dry_run
        """)
    parser.add_argument('--mac_address', help='specify which device to be tested', default=None)
    parser.add_argument('--source_path', help='specify the folder path of source dataset which is transferred.', default=None)
    parser.add_argument('--connection_type', help='specify the connection_type', choices=['proxy', 'port_forward', 'local'], default='proxy')
    parser.add_argument('--kdd_product', help='kdd_product, ibi or WD', default='ibi', choices=['ibi', 'WD'])
    parser.add_argument('--client_os', help='Client OS type', default='MAC', choices=['WIN', 'MAC'])
    parser.add_argument('--client_ip', help='Client OS ip address', default=None)
    parser.add_argument('--client_username', help='Username to login client OS', default='root')  # for MAC
    parser.add_argument('--client_password', help='The password os client user', default="`1q")  # for MAC
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--environment_upload_avg', help='environment_upload_avg', default='3')
    parser.add_argument('--html_format', help='the html format for test result', default='1', choices=['1', '2'])

    test = DesktopAppPerf(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
