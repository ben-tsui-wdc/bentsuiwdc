# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import sys, time

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
#from kdp_scripts.bat_scripts.reboot import Reboot
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat


class DockerLoad(KDPTestCase):

    TEST_SUITE = 'KDP KPI'
    TEST_NAME = 'KDP KPI Test case - Boot Time KPI'
    # Popcorn
    TEST_JIRA_ID = ''


    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True
    }


    def declare(self):
        self.test_result_list = []
        self.html_format = '2'
        # Popcorn
        self.VERSION= 'InternalBeta'


    def init(self):
        pass


    def before_loop(self):
        stdout, stderr = self.ssh_client.execute_cmd('docker pull nginx')
        # Check
        stdout, stderr = self.ssh_client.execute_cmd('docker images')
        if "nginx" not in stdout:
            raise self.err.StopTest("It's failed to do 'docker pull nginx'.")
        stdout, stderr = self.ssh_client.execute_cmd('docker save nginx -o nginx.tar')
        # Check
        stdout, stderr = self.ssh_client.execute_cmd('ls')
        if "nginx.tar" not in stdout:
            raise self.err.StopTest("It's failed to do 'docker save nginx -o nginx.tar'.")


    def before_test(self):
        stdout, stderr = self.ssh_client.execute_cmd('docker rmi nginx')
        # Check
        stdout, stderr = self.ssh_client.execute_cmd('docker images')
        if "nginx" in stdout:
            raise self.err.StopTest("It's failed to do 'docker rmi nginx'.")


    def test(self):
        start_time = time.time()
        stdout, stderr = self.ssh_client.execute_cmd('docker load -i nginx.tar')
        load_time_avg = time.time() - start_time
        # Check
        stdout, stderr = self.ssh_client.execute_cmd('docker images')
        if "nginx" not in stdout:
            raise self.err.TestFailure("It's failed to do 'docker load -i nginx.tar'.")
        # Update test_result
        self.data.test_result['LoadTime_avg'] = load_time_avg
        self.data.test_result['LoadTime_unit'] = 'sec'
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # millisecond


    def after_test(self):
        self.test_result_list.append(self.data.test_result)


    def after_loop(self):
        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'LoadTime_avg', 'LoadTime_unit', 'executionTime']
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)
        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'build', 'LoadTime_avg', 'LoadTime_unit', 'count', 'executionTime']
        csv_inst.csv_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)
        # Restore testing device
        stdout, stderr = self.ssh_client.execute_cmd('docker rmi nginx')
        stdout, stderr = self.ssh_client.execute_cmd('docker images')
        if "nginx" in stdout:
            self.log.warning("It's failed to do 'docker rmi nginx'.")
        stdout, stderr = self.ssh_client.execute_cmd('rm -f nginx.tar')        


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Desktop_Sync_BAT on Kamino Android ***
        Examples: ./run.sh kdp_scripts/performance_tests/windows_smb_download.py  --uut_ip 192.168.0.42:8001 --cloud_env dev1 --ssh_ip 192.168.0.42 --ssh_user sshd --ssh_password 123456 --debug  --loop_times 1  --dry_run  --stream_log_level INFO  --windows_client_ip 192.168.0.33 --windows_dataset_path C:\\5G_Standard_test1 --uut_share windows_smb  -dupr
        """)
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')



    test = DockerLoad(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
