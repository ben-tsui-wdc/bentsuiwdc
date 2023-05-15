# -*- coding: utf-8 -*-
""" Test case for device boot time
"""
__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
from xmlrpclib import ServerProxy
import re
import socket
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from ibi_performance.tool.html import HtmlFormat
from platform_libraries.restAPI import RestAPI
from godzilla_scripts.bat_scripts.firmware_update import FirmwareUpdate
from godzilla_scripts.bat_scripts.factory_reset import FactoryReset



class RestSDKIndex(GodzillaTestCase):

    TEST_SUITE = 'Godzilla RestSDKIndex'
    TEST_NAME = 'restsdk index after factory_reset'
    # Popcorn
    TEST_JIRA_ID = 'GZA-XXXX'
    REPORT_NAME = 'Stability'


    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True
    }


    def declare(self):
        self.test_result_list = []
        self.timeout = 60*3
        self.html_format = '2'
        self.dataset_folder = '/mnt/HD/HD_a2/5G_Standard'
        # Popcorn
        self.VERSION= 'InternalBeta'


    def init(self):
        pass


    def before_loop(self):
        self.env_dict = self.env.dump_to_dict()


    def before_test(self):
        self.filesystem_id = None
        self.target_total_indexed_file_with_hidden = None
        self.target_total_indexed_folder_with_hidden = None
        self.index_info_in_log = None
        
        firmware_update = FirmwareUpdate(self.env_dict)
        firmware_update.disable_ota = 'True'
        firmware_update.overwrite = 'True'

        self.log.warning('start factory_reset to remove restsdk component from GZA')
        factory_reset = FactoryReset(self.env_dict)
        factory_reset.before_test()
        factory_reset.test()
        factory_reset.after_test()

        self.target_total_indexed_file_with_hidden_os3, stderr = self.ssh_client.execute_cmd("find {} -type f |wc -l".format(self.dataset_folder))
        self.target_total_indexed_folder_with_hidden_os3, stderr = self.ssh_client.execute_cmd("find {} -type d |wc -l".format(self.dataset_folder))

        '''
        # Comment following code due to reduction of test elapsed time 
        self.log.warning('start downgrading firmware from GZA to OS3')
        firmware_update.fw_version = self.os3_firmware
        firmware_update.before_test()
        firmware_update.test()
        firmware_update.after_test()

        self.log.warning("Target device is in OS3 FW:{} now.".format(self.os3_firmware))
        # Calculate the number of files whn device is in OS3
        self.target_total_indexed_file_with_hidden_os3, stderr = self.ssh_client.execute_cmd("find {} -type f |wc -l".format(self.dataset_folder))
        self.target_total_indexed_folder_with_hidden_os3, stderr = self.ssh_client.execute_cmd("find {} -type d |wc -l".format(self.dataset_folder))
        self.log.info("Clean RestSDK data in OS3")
        stdout, stderr = self.ssh_client.execute_cmd("rm -rf /mnt/HD/HD_a2/restsdk-data")
        if stderr:
            raise self.err.TestError("Clean RestSDK data in OS3 failed!")
        self.log.info("Clean RestSDK info in OS3")
        stdout, stderr = self.ssh_client.execute_cmd("rm -rf /mnt/HD/HD_a2/restsdk-info")
        if stderr:
            raise self.err.TestError("Clean RestSDK info in OS3 failed!")

        self.log.warning('start upgrading firmware from OS3 to bridge_firmware')
        firmware_update.fw_version = self.bridge_firmware
        firmware_update.before_test()
        firmware_update.test()
        firmware_update.after_test()
        self.log.warning("Target device is in bridge FW:{} now.".format(self.bridge_firmware))

        self.log.warning('start upgrading firmware from bridge_firmware to GZA')
        firmware_update.fw_version = self.gza_firmware
        firmware_update.before_test()
        firmware_update.test()
        firmware_update.after_test()
        self.log.warning("Target device is in GZA FW:{} now.".format(self.gza_firmware))   
        '''

        # Calculate the amount of files and folders
        self.target_total_indexed_file_with_hidden, stderr = self.ssh_client.execute_cmd("find {} -type f |wc -l".format(self.dataset_folder))
        self.target_total_indexed_folder_with_hidden, stderr = self.ssh_client.execute_cmd("find {} -type d |wc -l".format(self.dataset_folder))

        # Compare the amount of files and folders betweeen OS3 and GZA
        if self.target_total_indexed_file_with_hidden != self.target_total_indexed_file_with_hidden_os3:
            self.log.warning("Total files in dataset_folder in GZA: {}".format(self.target_total_indexed_file_with_hidden))
            self.log.warning("Total files in dataset_folder in OS3: {}".format(self.target_total_indexed_file_with_hidden_os3))
            raise self.err.TestFailure("The number of files in dataset is not the same after upgrading GZA from OS3.")
        if self.target_total_indexed_folder_with_hidden != self.target_total_indexed_folder_with_hidden_os3:
            self.log.warning("Total folders in dataset_folder in GZA: {}".format(self.target_total_indexed_folder_with_hidden))
            self.log.warning("Total folders in dataset_folder in OS3: {}".format(self.target_total_indexed_folder_with_hidden_os3))
            raise self.err.TestFailure("The number of folders in dataset is not the same after upgrading GZA from OS3.")

        print '\n##################\n'
        print "with_hidden"
        print self.target_total_indexed_file_with_hidden
        print self.target_total_indexed_folder_with_hidden
        print '\n##################\n'

        # Onboarding GZA
        if self.env.cloud_env == 'prod':
            with_cloud_connected = False
        else:
            with_cloud_connected = True
        self.uut_owner = RestAPI(uut_ip='{}:8001'.format(self.env.uut_ip), env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
        self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']}, with_cloud_connected=with_cloud_connected)

        # Clean iptables to disable limitation of number of IP connection.
        stdout, stderr = self.ssh_client.execute_cmd('iptables -F')
        time.sleep(2)
        
        # Monitor RESTSDK indexing for GZA
        '''
        # Old code -> Socker is closed.
        # self.ssh_client.push_sqlite3_utils()
        '''
        self.uut_owner.set_global_timeout(timeout=None) 
        # Upload small tools for calculating the number of files in sqlite db 
        self.ssh_client.sftp_connect()
        if self.PLATFORM in ['PR2100', 'PR4100', 'DL2100','DL4100',]:
            print 'INTEL chipset'
            self.ssh_client.sftp_upload('./godzilla_scripts/tools/sqlite3_intel', 'sqlite3')
        else:
            print 'Marvel chipset'
            self.ssh_client.sftp_upload('./godzilla_scripts/tools/sqlite3_arm', 'sqlite3')
        self.ssh_client.sftp_upload('./godzilla_scripts/tools/sqlite_godzilla.sh', 'sqlite_godzilla.sh')
        stdout, stderr = self.ssh_client.execute_cmd("chmod 777 ~/sqlite*")


    def test(self):
        total_files_in_sqlite_before = self.ssh_client.wait_for_sqlite_no_change(time_of_no_change=30)

        # Record restsdk_pid
        stdout, stderr = self.ssh_client.execute_cmd('ps | grep restsdk-serverd | grep -v grep')
        initial_restsdk_pid = stdout.split()[0]
        self.log.info("initial restsdk_pid: {}".format(initial_restsdk_pid))

        # Record start time
        start_machine_time = self.ssh_client.get_local_machine_time_in_log_format()
        self.log.info("Start machine time: {}".format(start_machine_time))

        # Create filesystem and wait until indexing completed.
        restsdk_index_start_time = time.time()
        self.filesystem_id = self.uut_owner.create_filesystem(folder_path=self.dataset_folder, name=self.dataset_folder)
        total_index_files_in_call = int(self.wait_for_indexing_complete_by_call(self.filesystem_id)) # files + folders
        restsdk_index_finish_time = time.time()

        total_files_in_sqlite_after = self.ssh_client.wait_for_sqlite_no_change(time_of_no_change=30)
        total_files_in_sqlite = int(total_files_in_sqlite_after) - int(total_files_in_sqlite_before)

        # Fetch the index log from var/log/wdlog.log in target device
        index_log_dict = self.wait_for_indexing_complete_by_logs(self.dataset_folder, start_machine_time) # files + folder
        print '\n##################'
        self.log.warning("Restsdk indexing duration: {} seconds".format(restsdk_index_finish_time - restsdk_index_start_time))
        print 'index_log_dict:{}'.format(index_log_dict)
        print "total_index_files_in_call: {}".format(total_index_files_in_call)
        print "total_files_in_sqlite: {}".format(total_files_in_sqlite)
        print "target_total_indexed_file_with_hidden: {}".format(self.target_total_indexed_file_with_hidden)
        print "target_total_indexed_folder_with_hidden: {}".format(self.target_total_indexed_folder_with_hidden)
        print '################## \n'
        
        # sqlilte db will count one more than REST call because restsdk doesn't count the filesystem_id of dataset folder itself.
        if total_index_files_in_call != total_files_in_sqlite - 1 and total_index_files_in_call != total_files_in_sqlite:
            raise self.err.TestFailure("The number of REST call response is not the same as the number of sqlite db.")
        # Real number of "files+folders" will count one more than REST call becasue restsdk doesn't count dataset folder itself.
        if index_log_dict and int(index_log_dict['totalIndexedFiles']):
            if int(index_log_dict['totalIndexedFiles']) + int(index_log_dict['totalSkipped']) !=  \
                int(self.target_total_indexed_file_with_hidden) + int(self.target_total_indexed_folder_with_hidden) - 1:
                self.log.warning("The real number of files and folders is not the same as index log.")
                #raise self.err.TestFailure("The real number of files and folders is not the same as index log.")
        else:
            self.log.error('No index log found!')


        # Confirm if restsdk_pid is the same
        stdout, stderr = self.ssh_client.execute_cmd('ps | grep restsdk-serverd | grep -v grep')
        final_restsdk_pid = stdout.split()[0]
        self.log.info("final restsdk_pid: {}".format(final_restsdk_pid))
        if final_restsdk_pid != initial_restsdk_pid:
            raise self.err.TestFailure("RestSDK PID changed after indexing.")


    def after_test(self):
        if self.filesystem_id:
            self.uut_owner.delete_filesystem(filesystem_id=self.filesystem_id)


    def after_loop(self):
        pass


    def wait_for_indexing_complete_by_call(self, filesystem_id, max_waiting_time=60*1440):
        self.log.info('Wait for indexing complete by REST SDK call...')
        start_time = time.time()
        filesystem = None
        while time.time() - start_time < max_waiting_time:
            filesystem = self.uut_owner.get_filesystem(filesystem_id)
            print filesystem
            if 'stats' in filesystem and filesystem['stats'].get('firstScanStatus') == 'complete' \
                    and filesystem['stats']['firstScanFilesCount'] == filesystem['stats']['firstScanTotalFilesCountExpected']:
                return filesystem['stats']['firstScanFilesCount']
            time.sleep(10)
        if filesystem: self.log.warning('Last filesystem info: {}'.format(filesystem))
        raise self.err.StopTest('Indexing is still not complete after {} secs'.format(max_waiting_time))


    def wait_for_indexing_complete_by_logs(self, path, index_start_machine_time=None):
        self.log.info('Wait for indexing complete log appear...')
        for i in xrange(3):
            index_log = self.ssh_client.get_indexing_log(path, index_start_machine_time)  # The return is a string.
            if index_log:
                self.log.info("Log found: {}".format(index_log))
                return self.ssh_client.fetch_indexing_log(index_log)  # The return is a dictionary.
            time.sleep(5)


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Boot time test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/performance_tests/reboot_time.py --uut_ip 10.0.0.33:8001 \
        --ssh_ip 10.0.0.33 --ssh_user sshd --ssh_password 123456 --dry_run \
        """)

    parser.add_argument('-os3fw', '--os3_firmware', help='OS3 Firmware Version', default='2.31.204')
    parser.add_argument('-bfw', '--bridge_firmware', help='Bridge Firmware Version', default='2.40.132')
    parser.add_argument('-gzafw', '--gza_firmware', help='Bridge Firmware Version', default='5.00.211')
    parser.add_argument('--dataset_folder', help='dataset folder in target device', default='/mnt/HD/HD_a2/dataset')
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')


    test = RestSDKIndex(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
