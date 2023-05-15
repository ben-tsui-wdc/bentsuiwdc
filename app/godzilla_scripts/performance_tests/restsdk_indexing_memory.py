# -*- coding: utf-8 -*-
""" Test case for device boot time
"""
__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import json
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat
from platform_libraries.restAPI import RestAPI
from godzilla_scripts.bat_scripts.firmware_update import FirmwareUpdate
from godzilla_scripts.bat_scripts.factory_reset import FactoryReset


class RestSDKIndex(GodzillaTestCase):

    TEST_SUITE = 'Godzilla RestSDKIndex'
    TEST_NAME = 'restsdk indexing memory usage monitoring'
    # Popcorn
    TEST_JIRA_ID = 'GZA-XXXX'
    REPORT_NAME = 'Performance'

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }


    def declare(self):
        self.test_result_list = []
        self.timeout = 60*3
        self.html_format = '2'
        self.dbCache1_initial_indexing = None
        self.dbCache1_rescan_indexing = None
        self.RSS_initial_list = []
        self.RSS_rescan_list = []
        # Popcorn
        self.VERSION= 'InternalBeta'


    def init(self):
        pass


    def before_loop(self):
        start_time = time.time()
        # Create fake dataset
        stdout, stderr = self.ssh_client.execute_cmd('rm -fr /mnt/HD/HD_a2/{}/restsdk_test'.format(self.specific_folder))
        stdout, stderr = self.ssh_client.execute_cmd('mkdir /mnt/HD/HD_a2/Public/restsdk_test')
        stdout, stderr = self.ssh_client.execute_cmd('dd if=/dev/urandom of=/mnt/HD/HD_a2/Public/restsdk_test/masterfile bs=1 count={}'.format(self.masterfile_size), timeout=600)
        stdout, stderr = self.ssh_client.execute_cmd('split -b 10 -a 10 /mnt/HD/HD_a2/Public/restsdk_test/masterfile /mnt/HD/HD_a2/Public/restsdk_test/' ,timeout=86400)
        self.log.warning('Elapsed time (sec) for dd + split : {}'.format(time.time() - start_time))


    def before_test(self):
        # Add share folder to filesystem
        self.uut_owner.create_filesystem(folder_path='/mnt/HD/HD_a2/{}'.format(self.specific_folder))

        # Find out the filesystem_id of new share folder
        result = self.uut_owner.get_filesystem()
        for filesystem in result.get('filesystems'):  # result.get('filesystems') is a list
            if filesystem.get('path') == '/mnt/HD/HD_a2/{}'.format(self.specific_folder):
                self.filesystem_id = filesystem.get('id')
        self.log.info('uut_share:/mnt/HD/HD_a2/{}, latest_filesystem_id:{}'.format(self.specific_folder, self.filesystem_id))


    def test(self):
        # Wait for initial indexing completed 
        start_time = time.time()
        self.RSS_initial_list, firstScanFilesCount = self.wait_for_indexing_complete_by_call(self.filesystem_id, RSS_list=self.RSS_initial_list)
        self.log.warning('Elapsed time (sec) for initial indexing : {}'.format(time.time() - start_time))

        self.log.warning('After index completed, monitor RSS more 5 minutes.')
        # Wait for more 5 minutes to monitor RSS
        start_time = time.time()
        while time.time() - start_time < 300:
            stdout, stderr = self.ssh_client.execute_cmd("top -m -n 1 -d 1  | grep -i restsdk|grep -v restsdk-serverd")
            RSS_value = stdout.split()[3]
            if 'm' in RSS_value:
                self.RSS_initial_list.append(RSS_value)
            time.sleep(10)
        print '333333' * 20
        self.RSS_initial_avg, self.RSS_initial_max = self.statistics(target_list=self.RSS_initial_list)
        self.dbCache1_initial_indexing = self.check_dbCache1()
        print '333333' * 20

        # Update test_result for html and csv
        self.data.test_result['NumberOfFiles'] = firstScanFilesCount
        self.data.test_result['Type'] = 'Initial'
        self.data.test_result['RSS_avg'] = self.RSS_initial_avg
        self.data.test_result['RSS_max'] = self.RSS_initial_max
        self.data.test_result['dbCache1_avg'] = self.dbCache1_initial_indexing
        self.data.test_result['dbCache1_unit'] = 'MB'
        self.data.test_result['RSS_unit'] = 'MB'

        # Update test_result for Popcorn
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # millisecond

        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'NumberOfFiles', 'Type', 'build', 'RSS_avg', 'RSS_max','dbCache1_avg', 'dbCache1_unit', 'RSS_unit']
            #html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=[self.data.test_result], results_folder=self.env.results_folder)
        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'NumberOfFiles', 'Type', 'build', 'RSS_avg', 'RSS_max','dbCache1_avg', 'dbCache1_unit', 'RSS_unit', 'count', 'executionTime']
        csv_inst.csv_table(test_result_list=[self.data.test_result], results_folder=self.env.results_folder)

        # Restart restsdk-server
        stdout, stderr = self.ssh_client.execute_cmd("restsdk.sh restart", timeout=60)

        # Wait for rescan indexing completed 
        start_time = time.time()
        self.RSS_rescan_list, firstScanFilesCount = self.wait_for_indexing_complete_by_call(self.filesystem_id, RSS_list=self.RSS_rescan_list)
        print '444444' * 20
        self.log.warning('Elapsed time (sec) for rescan indexing : {}'.format(time.time() - start_time))
        self.RSS_rescan_avg, self.RSS_rescan_max = self.statistics(target_list=self.RSS_rescan_list)
        self.dbCache1_rescan_indexing = self.check_dbCache1()
        print '444444' * 20

        # Update test_result for html and csv
        self.data.test_result['NumberOfFiles'] = firstScanFilesCount
        self.data.test_result['Type'] = 'Rescan'
        self.data.test_result['RSS_avg'] = self.RSS_rescan_avg
        self.data.test_result['RSS_max'] = self.RSS_rescan_max
        self.data.test_result['dbCache1_avg'] = self.dbCache1_rescan_indexing
        self.data.test_result['dbCache1_unit'] = 'MB'
        self.data.test_result['RSS_unit'] = 'MB'

        # Update test_result for Popcorn
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # millisecond

        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'NumberOfFiles', 'Type', 'build', 'RSS_avg', 'RSS_max','dbCache1_avg', 'dbCache1_unit', 'RSS_unit']
            #html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=[self.data.test_result], results_folder=self.env.results_folder)
        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'NumberOfFiles', 'Type', 'build', 'RSS_avg', 'RSS_max','dbCache1_avg', 'dbCache1_unit', 'RSS_unit', 'count', 'executionTime']
        csv_inst.csv_table(test_result_list=[self.data.test_result], results_folder=self.env.results_folder)


    def after_test(self):
        if self.filesystem_id:
            self.uut_owner.delete_filesystem(filesystem_id=self.filesystem_id)
        pass        


    def after_loop(self):
        stdout, stderr = self.ssh_client.execute_cmd('rm -fr /mnt/HD/HD_a2/{}/restsdk_test'.format(self.specific_folder))
        

    def wait_for_indexing_complete_by_call(self, filesystem_id, max_waiting_time=432000, RSS_list=None):
        self.log.info('Wait for indexing complete by REST SDK call...')
        start_time = time.time()
        filesystem = None
        while time.time() - start_time < max_waiting_time:
            if RSS_list != None:
                stdout, stderr = self.ssh_client.execute_cmd("top -m -n 1 -d 1  | grep -i restsdk|grep -v restsdk-serverd")
                RSS_value = stdout.split()[3]
                if 'm' in RSS_value:
                    RSS_list.append(RSS_value)
            filesystem = self.uut_owner.get_filesystem(filesystem_id)
            #print filesystem
            if 'stats' in filesystem and filesystem['stats'].get('firstScanStatus') == 'complete':
                return RSS_list, filesystem['stats'].get('firstScanFilesCount')
            time.sleep(10)
        if filesystem: self.log.warning('Last filesystem info: {}'.format(filesystem))
        raise self.err.StopTest('Indexing is still not complete after {} secs'.format(max_waiting_time))


    def check_dbCache1(self):
        stdout, stderr = self.ssh_client.execute_cmd("curl localhost:8001/sdk/debug/vars")
        r = json.loads(stdout)
        if r.get("dbCache1", None):
            dbCache1 = r.get("dbCache1", None).get("SizeMB")
            self.log.debug('dbCache1: {}'.format(r.get("dbCache1")))
            return dbCache1
        else:
            raise self.err.StopTest("dbCache1 is empty by localhost:8001/sdk/debug/vars.")
 

    def statistics(self, target_list=None):
        avg_target = None
        max_target = None

        print target_list
        temp = []
        for element in target_list:
            temp.append(float(element.split('m')[0]))
        if temp:
            avg_target = '{0:.0f}'.format(sum(temp)/len(temp))
            max_target = '{}'.format(max(temp))
        self.log.info('Avg: {}'.format(avg_target))
        self.log.info('Max: {}'.format(max_target))
        return avg_target, max_target


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Boot time test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/performance_tests/reboot_time.py --uut_ip 10.0.0.33:8001 \
        --ssh_ip 10.0.0.33 --ssh_user sshd --ssh_password 123456 --dry_run \
        """)


    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--specific_folder', help='Public or TimeMachineBackup', default='Public')
    parser.add_argument('--masterfile_size', help='the size(byte) of masterfile', default='4000000')


    test = RestSDKIndex(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
