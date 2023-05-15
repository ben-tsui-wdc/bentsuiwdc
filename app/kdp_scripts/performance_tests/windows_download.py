# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
from xmlrpclib import ServerProxy
import json, re, socket, sys, time

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.restAPI import RestAPI
from platform_libraries.nasadmin_client import NasAdminClient
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat


class WindowsDownload(KDPTestCase):

    TEST_SUITE = 'KDP KPI'
    TEST_NAME = 'KDP KPI Test case - Windows SMB download'
    # Popcorn
    TEST_JIRA_ID = ''

    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True,
    }

    def declare(self):
        self.windows_client_ip = None
        self.test_result_list = []
        self.html_format = '2'
        self.specific_folder = 'Public'
        self.nasadmin_username = 'owner'
        self.nasadmin_password = 'password'
        # Popcorn
        self.VERSION= 'InternalBeta'


    def init(self):
        self.uut_share_original = self.uut_share
        if self.nasadmin == 'on':
            self.specific_folder = 'nasadmin_share'

    def before_loop(self):
        # Check rest_sdk version
        self.restsdk_version = self.get_restsdk_version()

        timeout = 7200
        # Cancel "socket" timeout because the reponse time via socket is not the same.
        self.log.info('Set global timeout: {}s'.format(timeout))
        socket.setdefaulttimeout(timeout)

        nasadmin_client = NasAdminClient(self.env.uut_ip)
        if self.nasadmin == 'on' and nasadmin_client.is_nasAdmin_working():
            self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
            if self.env.cloud_env == 'prod':
                with_cloud_connected = False
            else:
                with_cloud_connected = True
            self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']}, with_cloud_connected=with_cloud_connected)
            nasadmin_client.set_rest_client(self.uut_owner)
            # Wait for restsdk aknowledging nasadmin that the owner is attached to UUT.
            if not nasadmin_client.wait_for_nasAdmin_works():
                raise self.err.TestError("nasAdmin does't work")
            if not nasadmin_client.is_owner_attached_restsdk():
                raise self.err.TestError("First user is not attached by RestSDK.")
            if not nasadmin_client.wait_for_owner_attached():
                raise self.err.TestError("Owner isn't attached by nasadmin.")
            '''
            # For rocket/drax
            for space in nasadmin_client.get_spaces():
                if space['name'] == self.specific_folder:
                    nasadmin_client.delete_spaces(space['id'])
                    break
            space = nasadmin_client.create_space(name=self.specific_folder, allUsers=True, localPublic=False)
            nasadmin_users = nasadmin_client.get_users()
            for user in nasadmin_users:
                if user.get('cloudID') == self.uut_owner.get_user_id():
                    nasadmin_user = user
                    break
            '''
            token = nasadmin_client.login_owner()
            self.log.warning('nasadmin_token:{}'.format(token))
            nasadmin_user = nasadmin_client.get_user(token['userID'])            
            self.log.warning('nasadmin_user:{}'.format(nasadmin_user))
            nasadmin_client.update_user(nasadmin_user['id'], localAccess=True, username=self.nasadmin_username, password=self.nasadmin_password, spaceName=self.specific_folder)
        # Umount the old SMB share from Windows client
        self._umount(self.windows_mount_point)
        # Mount the SMB share from Windows client
        self._mount(self.windows_mount_point, self.env.uut_ip.split(':')[0], self.specific_folder)
        # Create uut_share name with timestamp
        self.uut_share = self.uut_share_original + '_{}'.format(int(time.time()))
        self.log.info("uut_share name: {}".format(self.uut_share))
        # Pre-upload
        self.log.info("First, upload dataset to UUT ...")
        cmd = "robocopy {} {}:\\{} /E /NP /NS /NC /NFL /NDL /R:1 /W:1 /copy:DT".format(self.windows_dataset_path, self.windows_mount_point, self.uut_share)
        result = self.XMLRPCclient(cmd)
        match = re.search('(\d+)\sBytes/sec', result)
        if match:
            pass
        else:
            self.log.warning('Error occurred while pre-uploading, there is no XXX Bytes/sec displayed.')
            return
        self.log.info("Wait for 30 seconds before starting test iteration.")
        time.sleep(30)

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
        self.log.info("Umount then mount again in order to avoid WindowsOS cache effect before downloading.")
        self._umount(self.windows_mount_point)
        self._mount(self.windows_mount_point, self.env.uut_ip.split(':')[0], self.specific_folder)
        self.windows_client_folder = 'Windows_download_client_{}'.format(int(time.time()))
        # Remove SMBTestFolders from Windows client.
        cmd = "Remove-Item -Recurse -Force {}:\\{}; ".format(self.windows_dataset_path.split(":")[0], self.windows_client_folder) 
        result = self.XMLRPCclient(cmd)
        # Create test folder on Windows client.
        cmd = "New-Item -type directory {}:\\{}; ".format(self.windows_dataset_path.split(":")[0], self.windows_client_folder)
        result = self.XMLRPCclient(cmd)

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
        self.data.test_result['NasAdmin'] = self.nasadmin
        self.data.test_result['WiFiMode'] = self.wifi_mode
        # Update test_result for csv
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
        # Delete the dataset folder(SMBTestFolders) in KDP device via Windows client.
        cmd = "Remove-Item -Recurse -Force {}:\\{}; ".format(self.windows_mount_point, self.uut_share) 
        result = self.XMLRPCclient(cmd)
        # Umount the SMB folder from Windows client
        self._umount(self.windows_mount_point)
        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'RestSDK', 'iteration', 'TotalBytes', 'TotalRealFiles', 'NasAdmin', 'WiFiMode', 'DownAvgSpd','TargetDownAvgSpd',]
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)
        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'Direction', 'Client', "Protocol", "FileType", 'TotalRealFiles', 'TotalBytes', 'build', 'NasAdmin', 'WiFiMode', 'DownAvgSpd', 'TransferRate_unit', 'count', 'executionTime']
        csv_inst.csv_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)
        # Determine if the test is passed or not.
        if not pass_status_summary:
            raise self.err.TestFailure("At leaset one value doesn't meet the target/pass criteria.")

    def _mount(self, windows_mount_point, uut_ip, uut_share):
        print "\n### mount ###\n"
        # net use  Z:  \\192.168.50.196\Public   12345678 /user:owner
        cmd = 'NET USE {}: \\\\{}\{} '.format(windows_mount_point, uut_ip, uut_share)
        if self.nasadmin == 'on':
            cmd = cmd + '{} /user:{} '.format(self.nasadmin_password, self.nasadmin_username)
        result = self.XMLRPCclient(cmd)

    def _umount(self, windows_mount_point):
        print "\n### umount ###\n"
        cmd = 'NET USE /delete {}: /y'.format(windows_mount_point)
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
        stdout, stderr = self.ssh_client.execute_cmd("curl localhost:{}/sdk/v1/device".format(self.ssh_client.get_restsdk_httpPort()))
        return json.loads(stdout).get('version')

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Desktop_Sync_BAT on Kamino Android ***
        Examples: ./run.sh kdp_scripts/performance_tests/windows_smb_download.py  --uut_ip 192.168.0.42:8001 --cloud_env dev1 --ssh_ip 192.168.0.42 --ssh_user sshd --ssh_password 123456 --debug  --loop_times 1  --dry_run  --stream_log_level INFO  --windows_client_ip 192.168.0.33 --windows_dataset_path C:\\5G_Standard_test1 --uut_share windows_smb  -dupr
        """)
    parser.add_argument('--windows_client_ip', help='windows_client_ip', default='192.168.0.13')
    parser.add_argument('--windows_mount_point', help='mount point on Windows client which is for mounting UUT share folder by SMB.', default='R')
    parser.add_argument('--windows_dataset_path', help='dataset path on Windows client.', default=None)
    parser.add_argument('--uut_share', help='the share folder in target device which could be accessed by SMB', default='windows_download')
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--target_down_avg_spd', help='Target of download average speed.', default='11')
    parser.add_argument('--specific_folder', help='Public or TimeMachineBackup', default='Public')
    parser.add_argument('--nasadmin', help='To use userStorage share which belongs to live file system', default='off')
    parser.add_argument('--wifi_mode', help='type of wifi mode, by default is None', choices=['None','2.4G', '5G'], default='None')

    test = WindowsDownload(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
