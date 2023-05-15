# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
from xmlrpclib import ServerProxy
import json, re, socket, sys, time

# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.restAPI import RestAPI
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat


class WindowsDownload(GodzillaTestCase):

    TEST_SUITE = 'Godzilla KPI'
    TEST_NAME = 'GZA KPI Test case - Windows SMB upload'
    # Popcorn
    TEST_JIRA_ID = ''


    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True
    }


    def declare(self):
        self.windows_client_ip = None
        self.filesystem_id = None
        self.create_filesystem = 'off'
        self.test_result_list = []
        self.html_format = '2'
        # Popcorn
        self.VERSION= 'InternalBeta'


    def init(self):
        self.uut_share_original = self.uut_share


    def before_loop(self):
        # Check rest_sdk version
        self.restsdk_version = self.get_restsdk_version()

        timeout = 7200
        # Cancel "socket" timeout because the reponse time via socket is not the same.
        self.log.info('Set global timeout: {}s'.format(timeout))
        socket.setdefaulttimeout(timeout)

        # Onboarding GZA and add self.specific_folder to filesystem for OS5
        if self.create_filesystem == 'on' and self.uut.get('firmware').startswith('5.'):
            if self.env.cloud_env == 'prod':
                with_cloud_connected = False
            else:
                with_cloud_connected = True
            self.uut_owner = RestAPI(uut_ip='{}:8001'.format(self.env.uut_ip), env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
            self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']}, with_cloud_connected=with_cloud_connected)

            # Create filesystem with new share folder
            self.uut_owner.create_filesystem(folder_path='/mnt/HD/HD_a2/{}'.format(self.specific_folder))

            # Find out the filesystem_id of new share folder
            result = self.uut_owner.get_filesystem()
            for filesystem in result.get('filesystems'):  # result.get('filesystems') is a list
                if filesystem.get('path') == '/mnt/HD/HD_a2/{}'.format(self.specific_folder):
                    self.filesystem_id = filesystem.get('id')
            self.log.info('uut_share:/mnt/HD/HD_a2/{}, latest_filesystem_id:{}'.format(self.specific_folder, self.filesystem_id))

        # Umount the old SMB share from Windows client
        self._umount(self.windows_mount_point)
        
        # Create uut_share name with timestamp
        self.uut_share = self.uut_share_original + '_{}'.format(int(time.time()))
        self.log.info("uut_share name: {}".format(self.uut_share))

        # Mount the SMB share from Windows client
        self._mount(self.windows_mount_point, self.env.uut_ip.split(':')[0], self.specific_folder)

        # Pre-upload
        self.log.info("First, upload dataset to GZA device...")
        cmd = "robocopy {} {}:\\{} /E /NP /NS /NC /NFL /NDL /R:1 /W:1 /copy:DT".format(self.windows_dataset_path, self.windows_mount_point, self.uut_share)
        result = self.XMLRPCclient(cmd)
        match = re.search('(\d+)\sBytes/sec', result)
        if match:
            pass
        else:
            self.log.warning('Error occurred while pre-uploading, there is no XXX Bytes/sec displayed.')
            return


    def before_test(self):
        '''
        self._umount(self.windows_mount_point)
        time.sleep(120)
        self.log.info("Rebooting the device at the beginning of test iteration...")
        self.ssh_client.reboot_device()
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=60*20):
            raise self.err.TestFailure('Device was not shut down successfully!')
        if not self.ssh_client.wait_for_device_boot_completed(timeout=60*20):
            raise self.err.TestFailure('Device was not boot up successfully!')
        '''
        # Stop otaclient
        stdout, stderr = self.ssh_client.execute_cmd("otaclient.sh stop")

        # Stoping OS3 transcoding by Luis's request
        if self.create_filesystem == 'off':
            if self.uut.get('firmware').startswith('5.'):
                stdout, stderr = self.ssh_client.execute_cmd("restsdk.sh stop", timeout=10)
            elif self.uut.get('firmware').startswith('2.'):
                self.ssh_client.execute_cmd('/etc/init.d/wdphotodbmergerd stop')
                self.ssh_client.execute_cmd('/etc/init.d/wdmcserverd stop')
                self.ssh_client.execute_cmd('/etc/init.d/wdnotifierd stop')
        elif self.create_filesystem == 'on':
            if self.uut.get('firmware').startswith('2.'):
                self.ssh_client.execute_cmd('/etc/init.d/wdphotodbmergerd start')
                self.ssh_client.execute_cmd('/etc/init.d/wdmcserverd start')
                self.ssh_client.execute_cmd('/etc/init.d/wdnotifierd start')

        self.log.info("Umount then mount again in order to avoid WindowsOS cache effect before downloading.")
        self._umount(self.windows_mount_point)
        self._mount(self.windows_mount_point, self.env.uut_ip.split(':')[0], self.specific_folder)

        #self.windows_client_folder = 'Windows_download_client_{}'.format(self.env.iteration)
        self.windows_client_folder = 'Windows_download_client_{}'.format(int(time.time()))

        # Remove SMBTestFolders from Windows client.
        cmd = "Remove-Item -Recurse -Force {}:\\{}; ".format(self.windows_dataset_path.split(":")[0], self.windows_client_folder) 
        result = self.XMLRPCclient(cmd)

        # Create test folder on Windows client.
        cmd = "New-Item -type directory {}:\\{}; ".format(self.windows_dataset_path.split(":")[0], self.windows_client_folder)
        result = self.XMLRPCclient(cmd)

        self.log.info("Wait for 120 seconds before starting test iteration.")
        time.sleep(120)


    def test(self):
        self.log.info("Downloading dataset from target device to Windows client...")
        cmd = "robocopy {}:\\{} {}:\\{} /E /NP /NS /NC /NFL /NDL /R:1 /W:1 /copy:DT".format(self.windows_mount_point, self.uut_share, self.windows_dataset_path.split(":")[0], self.windows_client_folder)
        result = self.XMLRPCclient(cmd)
        for element in result.split('\n'):
            if 'Files :' in element and 'Files : *.*' not in element:
                total_real_files_temp = re.findall('Files :\s*\d*', element)[0]
                self.total_real_files = int(total_real_files_temp.split(':')[1])
            if 'Bytes :' in element:
                total_bytes_temp = re.findall('Bytes :\s*\S* \S* ', element)[0]
                self.total_bytes = (total_bytes_temp.split(':')[1]).strip()

        match = re.search('(\d+)\sBytes/sec', result)
        if match:
            speed = match.group(1)
            speed = float(speed) / float(1024*1024)  # Convert Bytes/sec to MB/sec.
            MB_per_second = '{}'.format(round(speed, 3))
        else:
            self.log.warning('Error occurred while robocopy, there is no XXX Bytes/sec displayed.')
            return

        # Update test_result
        self.data.test_result['TotalRealFiles'] = self.total_real_files
        self.data.test_result['TotalBytes'] = self.total_bytes
        self.data.test_result['DownAvgSpd'] = MB_per_second
        self.data.test_result['TargetDownAvgSpd'] = self.target_down_avg_spd
        self.data.test_result['RestSDK'] = self.restsdk_version

        # Update test_result for csv
        self.data.test_result['ShareAccess'] = self.create_filesystem
        self.data.test_result['Client'] = "Win"
        self.data.test_result['Protocol'] = 'SMB'
        self.data.test_result['FileType'] = self.windows_dataset_path
        self.data.test_result['Direction'] = 'Download'

        # For Popcorn
        self.data.test_result['TransferRate_unit'] = 'Mbps'
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # millisecond


    def after_test(self):
        self.test_result_list.append(self.data.test_result)

        # Remove SMBTestFolders from Windows client.
        cmd = "Remove-Item -Recurse -Force {}:\\{}; ".format(self.windows_dataset_path.split(":")[0], self.windows_client_folder) 
        result = self.XMLRPCclient(cmd)


    def after_loop(self):
        # Delete the dataset folder which is uploded to GZA device
        if self.delete_share_and_filesystem:
            self.log.warning('Delete test filesystem_id and uut_share.')
            # Delete filesystem_id
            if self.create_filesystem == 'on' and self.uut.get('firmware').startswith('5.'):
                if self.filesystem_id:
                    self.uut_owner.delete_filesystem(filesystem_id=self.filesystem_id)

            # Remove SMBTestFolders in GZA device from Windows client.
            cmd = "Remove-Item -Recurse -Force {}:\\{}; ".format(self.windows_mount_point, self.uut_share) 
            result = self.XMLRPCclient(cmd)

        # Umount the SMB folder from Windows client
        self._umount(self.windows_mount_point)

        # Restore the environment of device
        #stdout, stderr = self.ssh_client.execute_cmd("sudo -u restsdk otaclient.sh start", timeout=10)
        if self.create_filesystem == 'off':
            stdout, stderr = self.ssh_client.execute_cmd("sudo -u restsdk restsdk.sh start", timeout=10)

        if self.create_filesystem == 'off' and self.uut.get('firmware').startswith('2.'):
            self.ssh_client.execute_cmd('/etc/init.d/wdphotodbmergerd start')
            self.ssh_client.execute_cmd('/etc/init.d/wdmcserverd start')
            self.ssh_client.execute_cmd('/etc/init.d/wdnotifierd start')

        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'RestSDK', 'iteration', 'TotalBytes', 'TotalRealFiles', 'DownAvgSpd','TargetDownAvgSpd',]
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'Direction', 'ShareAccess', 'Client', "Protocol", "FileType", 'TotalRealFiles', 'TotalBytes', 'build', 'DownAvgSpd', 'TransferRate_unit', 'count', 'executionTime']
        csv_inst.csv_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # Determine if the test is passed or not.
        if not pass_status_summary:
            '''
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
            '''
            raise self.err.TestFailure("At leaset one value doesn't meet the target/pass criteria.")



    def _mount(self, windows_mount_point, uut_ip, uut_share):
        print "\n### mount ###\n"
        #cmd = 'NET USE {}: \\\\{}\Public /user:guest'.format(windows_mount_point, uut_ip)
        cmd = 'NET USE {}: \\\\{}\{}'.format(windows_mount_point, uut_ip, uut_share)
        result = self.XMLRPCclient(cmd)


    def _umount(self, windows_mount_point):
        print "\n### umount ###\n"
        cmd = 'NET USE /delete {}: /y;'.format(windows_mount_point)
        result = self.XMLRPCclient(cmd)
        

    def XMLRPCclient(self, cmd):
        try:
            server = ServerProxy("http://{}:12345/".format(self.windows_client_ip))
            result = server.command(cmd)  # server.command() return the result which is in string type.
            print "{}".format(cmd)
            print result
            return result
        except socket.error as e:
            e = str(e)
            print "socket.error: {}\nCould not connect with the socket-server: {}".format(e, self.windows_client_ip)


    def get_restsdk_version(self):
        if self.uut.get('firmware').startswith('5.'):
            stdout, stderr = self.ssh_client.execute_cmd("curl localhost:8001/sdk/v1/device")
            return json.loads(stdout).get('version')
        else:
            return None


    '''
    def _device_size(self):
        resp = self.uut_owner.get_device()
        if resp.status_code == 200:
            temp = resp.json().get('storage').get('capacity')  #temp is device_size in bytes.
            return '{0:.0f}'.format(float(temp)/1000000000000)
        else:
            return None
    '''


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Desktop_Sync_BAT on Kamino Android ***
        Examples: ./run.sh godzilla_scripts/performance_tests/windows_smb_upload.py  --uut_ip 192.168.0.42:8001 --cloud_env dev1 --ssh_ip 192.168.0.42 --ssh_user sshd --ssh_password 123456 --debug  --loop_times 1  --dry_run  --stream_log_level INFO  --windows_client_ip 192.168.0.33 --windows_dataset_path C:\\5G_Standard_test1 --uut_share windows_smb  -dupr
        """)
    parser.add_argument('--windows_client_ip', help='windows_client_ip', default='192.168.0.33')
    parser.add_argument('--windows_mount_point', help='mount point on Windows client which is for mounting UUT share folder by SMB.', default='R')
    parser.add_argument('--windows_dataset_path', help='dataset path on Windows client.', default=None)
    parser.add_argument('--uut_share', help='the share folder in target device which could be accessed by SMB', default='windows_download')
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--target_down_avg_spd', help='Target of download average speed.', default='11')
    parser.add_argument('--delete_share_and_filesystem', help='Delete share folder and filesystem_id in GZA', action='store_true')
    parser.add_argument('--create_filesystem', help='choose whether the folder is added to restsdk filesystem or not', choices=['on', 'off'], default='off')
    parser.add_argument('--specific_folder', help='Public or TimeMachineBackup', default='Public')


    test = WindowsDownload(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
