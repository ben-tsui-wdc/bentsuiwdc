# -*- coding: utf-8 -*-
""" Test case for device boot time
"""
__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import re
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from ibi_performance.tool.html import HtmlFormat


class BootTimeKPI(GodzillaTestCase):

    TEST_SUITE = 'Godzilla KPI'
    TEST_NAME = 'boot up time'
    # Popcorn
    PROJECT = 'godzilla'
    TEST_TYPE = 'performance'
    TEST_JIRA_ID = 'GZA-1794'
    PRIORITYT = 'critical'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True
    }


    def declare(self):
        self.test_result_list = []
        self.timeout = 60*3
        self.html_format = '2'


    def init(self):
        pass


    def _test(self):
        print self.data.test_result

    def test(self):
        self.log.info("Reboot device by SSH")
        self.ssh_client.reboot_device()


        if not self.ssh_client.wait_for_device_to_shutdown(timeout=self.timeout):
            raise self.err.TestFailure('Device was not shut down successfully!')


        if not self.ssh_client.wait_for_device_boot_completed(timeout=self.timeout):
            raise self.err.TestFailure('Device was not boot up successfully!')

        stdout, stderr = self.ssh_client.execute_cmd('dmesg')        
        temp = re.findall('\[.*\d*\.\d*\]', stdout.split('\n')[-1])[0]
        kernel_boot_time = float(temp.split('[')[1].split(']')[0])
        


        if not self.ssh_client.get_restsdk_service():
            raise self.err.TestFailure('RestSDK service was not started after device reboot!')

        print '#########'
        print kernel_boot_time


        self.data.test_result['ElapsT'] = kernel_boot_time
        #self.data.test_result['TargetElapsT'] = self.target_elapsed_time
        self.data.test_result['TargetElapsT'] = self.target_elapsed_time
        

    def after_test(self):
        self.test_result_list.append(self.data.test_result)


    def  after_loop(self):
        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'iteration', 'TargetElapsT', 'ElapsT',]
            html_inst.table_title_column_extend = ['result']
        html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

    #def after_test(self):
    #    self.log.info("Reconnect SSH protocol after testing")
    #    self.ssh_client.connect()


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Boot time test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/performance_tests/reboot_time.py --uut_ip 10.0.0.33:8001 \
        --ssh_ip 10.0.0.33 --ssh_user sshd --ssh_password 123456 --dry_run \
        """)
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--target_elapsed_time', help='target of target of elapsed time (sec).', default='65')
    test = BootTimeKPI(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
