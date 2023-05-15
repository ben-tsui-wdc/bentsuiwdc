# -*- coding: utf-8 -*-
""" kpi test includes uboot_time, boot_time, and "device connected to cloud" check.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import json, sys, time

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.ssh_client import SSHClient
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat


class RestapiRerfSteve(KDPTestCase):
    TEST_SUITE = 'Performance_Tests'
    TEST_NAME = 'restapi_perf_steve'
    SETTINGS = {'uut_owner' : True # Disbale restAPI
    }


    # Pre-defined parameters for IntegrationTest
    def declare(self):
        self.test_folder = 'restapi_perf_steve'
        self.test_result_list = []
        self.html_format = '2'

    def init(self):
        pass

    def before_loop(self):
        # Check rest_sdk version
        self.restsdk_version = self.get_restsdk_version()
        # Connect to MAC client
        self.mac_ssh = SSHClient(self.mac_server_ip, self.mac_username, self.mac_password)
        self.mac_ssh.connect()
        # Clear the old metadata of keystone.sh
        stdout, stderr = self.mac_ssh.execute_cmd('rm -rf /tmp/keystone')
        # Renew requisite
        stdout, stderr = self.mac_ssh.execute_cmd('rm -fr ~/{}'.format(self.test_folder))
        stdout, stderr = self.mac_ssh.execute_cmd('mkdir ~/{}'.format(self.test_folder))
        stdout, stderr = self.mac_ssh.execute_cmd('curl ftp:ftppw@{}/test/restapi_perf_steve/keystone.sh --output ~/{}/keystone.sh'.format(self.file_server_ip, self.test_folder))
        stdout, stderr = self.mac_ssh.execute_cmd('curl ftp:ftppw@{}/test/restapi_perf_steve/VTS_01_1.VOB --output ~/{}/VTS_01_1.VOB'.format(self.file_server_ip, self.test_folder))
        uut_info = self.uut_owner.get_uut_info()
        self.device_id = uut_info.get('id', None)
        if not self.device_id:
            raise self.err.TestError("There is no device_id while executing device rest api.")

    def test(self):
        if self.protocol_type == 'http':
            file_create_command = 'file-create'
        elif self.protocol_type == 'https':
            file_create_command = 'file-create-https'
        stdout, stderr = self.mac_ssh.execute_cmd('export OWNER_EMAIL="{}"; export PASSWORD="{}"; export DEVICEID="{}"; \
            bash  ~/{}/keystone.sh  {} root  test  ~/{}/VTS_01_1.VOB'.format(self.env.username, self.env.password, self.device_id, self.test_folder, file_create_command, self.test_folder))
        curl_final_result = stderr.split("\r").pop()
        up_avg_spd = curl_final_result.split()[7]
        self.log.warning('up_avg_spd: {}'.format(up_avg_spd))
        # Update test_result
        self.data.test_result['TotalBytes'] = curl_final_result.split()[1]
        self.data.test_result['UpAvgSpd'] = up_avg_spd.split('M')[0]
        self.data.test_result['TargetUpAvgSpd'] = self.target_up_avg_spd
        self.data.test_result['RestSDK'] = self.restsdk_version
        # Update test_result for csv
        self.data.test_result['Client'] = "Mac"
        self.data.test_result['Protocol'] = self.protocol_type
        self.data.test_result['FileType'] = "SingleFile"
        self.data.test_result['Direction'] = 'Upload'
        # For Popcorn
        self.data.test_result['TransferRate_unit'] = 'Mbps'
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # millisecond
        
    def after_test(self):
        self.test_result_list.append(self.data.test_result)

    def after_loop(self):
        #stdout, stderr = self.mac_ssh.execute_cmd('rm -fr ~/{}'.format(self.test_folder))
        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'RestSDK', 'iteration', 'Direction', 'Protocol', 'FileType', 'Client', 'TotalBytes', 'UpAvgSpd','TargetUpAvgSpd']
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)
        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'build', 'Direction', 'Client', 'Protocol', 'FileType', 'TotalBytes', 'UpAvgSpd', 'TransferRate_unit', 'count', 'executionTime']
        csv_inst.csv_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)
        # Determine if the test is passed or not.
        if not pass_status_summary:
            raise self.err.TestFailure("At leaset one value doesn't meet the target/pass criteria.")

    def get_restsdk_version(self):
        stdout, stderr = self.ssh_client.execute_cmd("curl localhost:{}/sdk/v1/device".format(self.ssh_client.get_restsdk_httpPort()))
        return json.loads(stdout).get('version')


if __name__ == '__main__':

    parser = KDPInputArgumentParser("""\
        *** time_machine_throughput test on Kamino Android ***
        Examples: ./run.sh performance_tests/boot_time.py --uut_ip 10.92.224.13 \
        --cloud_env qa1 --loop_times 4 --debug_middleware --dry_run\
        """)
    parser.add_argument('--wifi_mode', help='type of wifi mode, by default is None', choices=['None','2.4G', '5G'], default='None')
    parser.add_argument('--mac_server_ip', help='mac_server_ip which is used to be as client.' , default='192.168.0.58')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='wdcautotw1')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac clientt', default='Wdctest1234')
    parser.add_argument('--protocol_type', help='upload file via http or https', choices=["http", "https"], default='http')
    parser.add_argument('--file_server_ip', help='file_server_ip_mvwarrior', default='10.200.141.26')
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--target_up_avg_spd', help='Target of upload average speed.', default='11')

    test = RestapiRerfSteve(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)