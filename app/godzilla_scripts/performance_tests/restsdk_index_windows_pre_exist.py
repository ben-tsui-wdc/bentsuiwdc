# -*- coding: utf-8 -*-
""" Test case for device boot time
"""
__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
from xmlrpclib import ServerProxy
import json
import re
import socket
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat


class RestSDKIndex(GodzillaTestCase):

    TEST_SUITE = 'Godzilla KPI'
    TEST_NAME = 'GZA KPI Test case - RESTSDK index time for pre-existent'
    # Popcorn
    TEST_JIRA_ID = 'GZA-2175'


    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }


    def declare(self):
        self.test_result_list = []
        self.timeout = 60*3
        self.html_format = '2'
        self.uut_share = 'pre_existent'
        self.filesystem_id = None
        self.total_real_files = None
        self.copy_time_in_seconds = None
        self.delete_share_and_filesystem = False
        self.delete_uut_share_list = []
        self.delete_filesystem_id_list = []
        # Popcorn
        self.VERSION= 'Godzilla-Phase2-M4'


    def init(self):
        self.uut_share_original = self.uut_share



    def before_loop(self):
        # Stop otaclient
        stdout, stderr = self.ssh_client.execute_cmd("otaclient.sh stop")

        # Cancel "socket" timeout because the reponse time via socket is not the same.
        self.uut_owner.set_global_timeout(timeout=None) 

        # Upload small tools for calculating the number of files in sqlite db 
        self.ssh_client.sftp_connect()
        if self.PLATFORM in ['PR2100', 'PR4100', 'DL2100','DL4100',]:
            print 'INTEL chipset'
            self.ssh_client.sftp_upload('./godzilla_scripts/tools/sqlite3_intel', 'sqlite3')
        else:
            print 'Marvel chipset'
            self.ssh_client.sftp_upload('./godzilla_scripts/tools/sqlite3_arm', 'sqlite3')

        # self.ssh_client.sftp_upload('./godzilla_scripts/tools/sqlite_godzilla.sh', 'sqlite_godzilla.sh')
        self.ssh_client.sftp_upload('./godzilla_scripts/tools/sqlite_godzilla_luis.sh', 'sqlite_godzilla.sh')
        stdout, stderr = self.ssh_client.execute_cmd("chmod 777 ~/sqlite*")


    def before_test(self):
        # sqlite db part. Ensure the number of sqlite db doesn't change anymore
        restsdk_index_finish_time = time.time()
        stdout, stderr = self.ssh_client.execute_cmd(". ~/sqlite_godzilla.sh")
        restsdk_index_number_by_sqlite = stdout
        while True:
            stdout, stderr = self.ssh_client.execute_cmd(". ~/sqlite_godzilla.sh")
            if stdout != restsdk_index_number_by_sqlite:
                restsdk_index_number_by_sqlite = stdout
                restsdk_index_finish_time = time.time()
            else:
                if time.time() - restsdk_index_finish_time > 30:
                    self.log.info('The number of files in db doesn\'t change after 30 seconds. Start test.')
                    break
                time.sleep(5)
        self.restsdk_index_number_by_sqlite_before = restsdk_index_number_by_sqlite

        # thumbmail part
        stdout, stderr = self.ssh_client.execute_cmd("find /mnt/HD/HD_a2/restsdk-data/data/files  -type f ! -size 0|wc -l")
        self.thumbnail_before = stdout

        # Umount the old SMB share from Windows client
        _umount(self.windows_mount_point)

        # Create uut_share name with timestamp
        self.uut_share = self.uut_share_original + '_{}'.format(int(time.time()))
        self.log.info("uut_share name: {}".format(self.uut_share))
        # Create share in GZA device        
        self.ssh_client.create_share(self.uut_share, public=True)
        # Mount the SMB share from Windows client
        time.sleep(3)
        _mount(self.windows_mount_point, self.env.uut_ip.split(':')[0], self.uut_share)

        cmd = "robocopy {} {}:\\ /E /NP /NS /NC /NFL /NDL /R:1 /W:1".format(self.windows_dataset_path, self.windows_mount_point)
        result = XMLRPCclient(cmd)
        # Parse total_real_files from response of robocopy
        for element in result.split('\n'):
            if 'Files :' in element and 'Files : *.*' not in element:
                total_real_files_temp = re.findall('Files :\s*\d*', element)[0]
                self.total_real_files = int(total_real_files_temp.split('Files :')[1])
            elif 'Bytes :' in element:
                total_bytes_temp = re.findall('Bytes :\s*\S* \S* ', element)[0]
                self.total_bytes = (total_bytes_temp.split('Bytes :')[1]).strip()
            elif 'Times :' in element:
                copy_time_temp = re.findall('Times :\s*\S* ', element)[0]
                copy_time = (copy_time_temp.split('Times :')[1]).strip()
                self.copy_time_in_seconds = 0
                for index, item in enumerate(list(reversed(copy_time.split(':')))):
                    if index == 0:  # second
                        self.copy_time_in_seconds = float(item)
                    elif index == 1:  # minute
                        self.copy_time_in_seconds += float(item) * 60
                    elif index == 2:  # hour
                        self.copy_time_in_seconds += float(item) * 3600

        match = re.search('(\d+)\sBytes/sec', result)
        if match:
            speed = match.group(1)
            speed = float(speed) / float(1024*1024)  # Convert Bytes/sec to MB/sec.
            self.data.test_result['CopyAvgSpd'] = '{:.1f}'.format(speed)
            #self.data.test_result['CopyAvgSpd'] = '{}'.format(round(speed, 1))
        else:
            self.log.warning('Error occurred while robocopy, there is no XXX Bytes/sec displayed.')
            return


    def test(self):
        # Local variables
        index_duration_temp = None
        total_indexed_files = None
        total_skipped = None
        latest_timestamp = None

        # Record restsdk_pid
        stdout, stderr = self.ssh_client.execute_cmd('ps aux | grep restsdk-server | grep -v grep | grep -v restsdk-serverd')
        initial_restsdk_pid = stdout.split()[0]
        self.log.info("initial restsdk_pid: {}".format(initial_restsdk_pid))

        # Create filesystem with new share folder
        self.uut_owner.create_filesystem(folder_path='/mnt/HD/HD_a2/{}'.format(self.uut_share))

        # This is used as workaround because there is no restdk log in logcat.
        restsdk_index_start_time = time.time()
        thumbnail_start_time = time.time()

        # Find out the filesystem_id of new share folder
        result = self.uut_owner.get_filesystem()
        for filesystem in result.get('filesystems'):  # result.get('filesystems') is a list
            if filesystem.get('path') == '/mnt/HD/HD_a2/{}'.format(self.uut_share):
                if filesystem.get('cTime') > latest_timestamp:
                    latest_timestamp = filesystem.get('cTime')
                    self.filesystem_id = filesystem.get('id')
        self.log.info('uut_share:/mnt/HD/HD_a2/{}, latest_filesystem_id:{}'.format(self.uut_share, self.filesystem_id))

        # Monitor the number change of sqlite db and thumbnail
        waiting_time = 300
        stop_check_sqlite = False
        stop_check_thumbnail = False
        restsdk_index_finish_time = time.time()
        thumbnail_finish_time = time.time()
        restsdk_index_number_by_sqlite = self.restsdk_index_number_by_sqlite_before
        thumbnail_after = self.thumbnail_before
        while True:
            # sqlite part
            if not stop_check_sqlite:
                stdout, stderr = self.ssh_client.execute_cmd(". ~/sqlite_godzilla.sh")
                if stdout != restsdk_index_number_by_sqlite:
                    restsdk_index_number_by_sqlite = stdout
                    restsdk_index_finish_time = time.time()
                else:
                    if time.time() - restsdk_index_finish_time > waiting_time:
                        self.log.info('The number of files in sqlite doesn\'t change for consecutive {} seconds.'.format(waiting_time))
                        self.log.info('Final self.restsdk_index_number_by_sqlite:{}'.format(restsdk_index_number_by_sqlite))
                        stop_check_sqlite = True

                        # Confirm if restsdk_pid is the same
                        stdout, stderr = self.ssh_client.execute_cmd('ps aux | grep restsdk-server | grep -v grep | grep -v restsdk-serverd')
                        final_restsdk_pid = stdout.split()[0]
                        self.log.info("final restsdk_pid: {}".format(final_restsdk_pid))
                        restsdk_pid_check = 'PASS'
                        if final_restsdk_pid != initial_restsdk_pid:
                            restsdk_pid_check = 'FAIL'

                        # Restart restsdk after sqlite DB is not changed according to Luis's request
                        stdout, stderr = self.ssh_client.execute_cmd("restsdk.sh stop", timeout=10)
                        stdout, stderr = self.ssh_client.execute_cmd("sudo -u restsdk restsdk.sh start", timeout=10)
                        time.sleep(30)

            # thumbnail part
            if not stop_check_thumbnail:
                stdout, stderr = self.ssh_client.execute_cmd("find /mnt/HD/HD_a2/restsdk-data/data/files  -type f ! -size 0|wc -l")
                if stdout != thumbnail_after:
                    thumbnail_after = stdout
                    thumbnail_finish_time = time.time()
                else:
                    if time.time() - thumbnail_finish_time > waiting_time:
                        self.log.info('The number of thumbnails doesn\'t change for consecutive {} seconds.'.format(waiting_time))
                        stop_check_thumbnail = True

            if stop_check_sqlite and stop_check_thumbnail:
                break
            else:
                # Monitor CPU usage
                self.ssh_client.execute_cmd('echo "CPU usage"; echo "  PID  PPID USER     STAT   VSZ %VSZ CPU %CPU COMMAND"; top -n 1 | grep -i restsdk  | grep -v restsdk-serverd')
                time.sleep(5)


        # Update test_result
        self.data.test_result['RestSDK'] = self.get_restsdk_version()
        self.data.test_result['TotalRealFiles'] = self.total_real_files
        self.data.test_result['TotalBytes'] = self.total_bytes
        self.data.test_result['TotalThumbnails'] = int(thumbnail_after) - int(self.thumbnail_before)
        self.data.test_result['ThumbnailElapsTime'] = '{:.1f}'.format(thumbnail_finish_time - thumbnail_start_time)
        if float(self.data.test_result['TotalThumbnails']):
            self.data.test_result['ThumbnailSpeed'] = '{:.1f}'.format(float(self.data.test_result['ThumbnailElapsTime'])/float(self.data.test_result['TotalThumbnails']))
        else:
            self.data.test_result['ThumbnailSpeed'] = 'None'
        self.data.test_result['TotalIndexedFiles'] = int(restsdk_index_number_by_sqlite) - int(self.restsdk_index_number_by_sqlite_before)
        self.data.test_result['TargetTotalIndexedFiles'] = self.target_total_indexed_file
        self.data.test_result['IndexElapsTime'] = '{:.1f}'.format(restsdk_index_finish_time - restsdk_index_start_time)
        self.data.test_result['IndexSpeed'] = '{:.1f}'.format(float(self.data.test_result['IndexElapsTime'])/self.data.test_result['TotalRealFiles'])
        self.data.test_result['RestsdkPIDCheck'] = restsdk_pid_check
        # Update paramter to test_result
        self.data.test_result['FileType'] = self.windows_dataset_path.split("\\")[-1]
        self.data.test_result['IndexType'] = 'pre_existent'
        self.data.test_result['Client'] = "Win"
        self.data.test_result['Protocol'] = 'SMB'
        self.data.test_result['CopyTime'] = self.copy_time_in_seconds


    def after_test(self):
        # Append the test result
        self.test_result_list.append(self.data.test_result)

        # Umount the SMB folder from Windows client
        _umount(self.windows_mount_point)

        self.delete_uut_share_list.append(self.uut_share)
        self.delete_filesystem_id_list.append(self.filesystem_id)

        # There is a timing issue when getting filesystem. Sometimes there is no "firstScanProgress" in REST response if two iterations are too close.
        time.sleep(30)



    def after_loop(self):

        # Delete share and filesystem if the flag is True
        if self.delete_share_and_filesystem:
            self.log.warning('Delete test filesystem_id and uut_share.')
            # Delete filesystem_id
            for filesystem_id in self.delete_filesystem_id_list:
                self.uut_owner.delete_filesystem(filesystem_id=filesystem_id)
            # Delete the share in GZA device
            for uut_share in self.delete_uut_share_list:
                self.ssh_client.delete_share(uut_share)

        # Start otaclient
        #stdout, stderr = self.ssh_client.execute_cmd("sudo -u restsdk otaclient.sh start", timeout=10)

        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'RestSDK', 'iteration', 'CopyAvgSpd', 'TotalRealFiles', 'TotalBytes', 'TotalIndexedFiles', 'TargetTotalIndexedFiles', 'IndexElapsTime', 'IndexSpeed', 'TotalThumbnails', 'ThumbnailElapsTime', 'ThumbnailSpeed', 'RestsdkPIDCheck', ]

            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'build', 'RestSDK', 'IndexType', 'Client', "Protocol", "FileType", 'TotalRealFiles', 'TotalBytes', 'CopyTime','CopyAvgSpd', 'TotalIndexedFiles', 'IndexElapsTime', 'TotalThumbnails', 'ThumbnailElapsTime']
        csv_inst.csv_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # Determine if the test is passed or not.
        if not pass_status_summary:
            # Workaround for popcorn report
            import copy
            result_fake = copy.deepcopy(self.data.loop_results[-1])
            result_fake.TEST_PASS = False
            result_fake['failure_message'] = "At leaset one value doesn't meet the target/pass criteria."
            result_fake.POPCORN_RESULT["result"] = "FAILED"
            result_fake.POPCORN_RESULT["error"] = "At leaset one value doesn't meet the target/pass criteria."
            result_fake.POPCORN_RESULT["start"] = result_fake.POPCORN_RESULT["start"] + 2
            result_fake.POPCORN_RESULT["end"] = result_fake.POPCORN_RESULT["end"] + 3
            self.data.loop_results.append(result_fake)

            raise self.err.TestFailure("At leaset one value doesn't meet the target/pass criteria.")


    def get_restsdk_version(self):
        stdout, stderr = self.ssh_client.execute_cmd("curl localhost:8001/sdk/v1/device")
        return json.loads(stdout).get('version')


def _mount(windows_mount_point, uut_ip, uut_share):
    print "\n### mount ###\n"
    #cmd = 'NET USE {}: \\\\{}\Public /user:guest'.format(windows_mount_point, uut_ip)
    cmd = 'NET USE {}: \\\\{}\{}'.format(windows_mount_point, uut_ip, uut_share)
    result = XMLRPCclient(cmd)
    


def _umount(windows_mount_point):
    print "\n### umount ###\n"
    cmd = 'NET USE /delete {}: /y;'.format(windows_mount_point)
    result = XMLRPCclient(cmd)

    

def XMLRPCclient(cmd):
    try:
        server = ServerProxy("http://{}:12345/".format(windows_client_ip))
        result = server.command(cmd)  # server.command() return the result which is in string type.
        print "{}".format(cmd)
        print result
        return result
    except socket.error as e:
        e = str(e)
        print "socket.error: {}\nCould not connect with the socket-server: {}".format(e, windows_client_ip)



if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Boot time test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/performance_tests/reboot_time.py --uut_ip 10.0.0.33:8001 \
        --ssh_ip 10.0.0.33 --ssh_user sshd --ssh_password 123456 --dry_run \
        """)

    parser.add_argument('--windows_client_ip', help='windows_client_ip', default='192.168.0.33')
    parser.add_argument('--windows_mount_point', help='mount point on Windows client which is for mounting UUT share folder by SMB.', default='R')
    parser.add_argument('--windows_dataset_path', help='dataset path on Windows client.', default='C:\\5G_Standard_test')
    parser.add_argument('--uut_share', help='the share folder in target device which could be accessed by SMB', default='pre_existent')
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--target_total_indexed_file', help='target of number of indexed file', default='54')
    parser.add_argument('--target_total_created_thumbnails', help='target of number of created file', default='190')
    parser.add_argument('--delete_share_and_filesystem', help='Delete share folder and filesystem_id in GZA', action='store_true')
    # Make following variable(s) global
    args = parser.parse_args()
    windows_client_ip = args.windows_client_ip

    test = RestSDKIndex(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
