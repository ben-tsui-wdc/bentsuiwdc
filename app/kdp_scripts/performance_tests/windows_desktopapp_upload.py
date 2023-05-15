# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
from xmlrpclib import ServerProxy
import json, re, socket, sys, time


# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat


class windowsDesktopAppUpload(KDPTestCase):

    TEST_SUITE = 'KDP KPI'
    TEST_NAME = 'KDP KPI Test case - Windows SMB upload'
    # Popcorn
    TEST_JIRA_ID = ''

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }


    def declare(self):
        self.windows_client_ip = None
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

        #self.log.info("Wait 240 seconds for Disk Initialization after factory_reset and sometimes the cloud will take more than 3 minutes to mount CBFS drive.")
        #time.sleep(240)


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


        
        # Create uut_share name with timestamp
        self.uut_share = self.uut_share_original + '_{}'.format(int(time.time()))
        self.log.info("uut_share name: {}".format(self.uut_share))

        self.log.info("Wait for 60 seconds before starting test iteration...")
        time.sleep(60)


    def test(self):
        cmd = "robocopy {} {}:\\{} /E /NP /NS /NC /NFL /NDL /R:1 /W:1 /copy:DT".format(self.windows_dataset_path, self.windows_mount_point, self.uut_share)
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

        # Update test_result for html
        self.data.test_result['TotalRealFiles'] = self.total_real_files
        self.data.test_result['TotalBytes'] = self.total_bytes
        self.data.test_result['UpAvgSpd'] = MB_per_second
        self.data.test_result['TargetUpAvgSpd'] = self.target_up_avg_spd
        self.data.test_result['RestSDK'] = self.restsdk_version

        # Update test_result for csv
        self.data.test_result['Client'] = "Win"
        self.data.test_result['Protocol'] = 'DesktopApp'
        self.data.test_result['FileType'] = self.windows_dataset_path
        self.data.test_result['Direction'] = 'Upload'
        self.data.test_result['Wifi'] = self.wifi_mode
        self.data.test_result['DesktopApp'] = self.desktopapp_version

        # For Popcorn
        self.data.test_result['TransferRate_unit'] = 'Mbps'
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # millisecond


    def after_test(self):
        self.test_result_list.append(self.data.test_result)
        # Delete the dataset folder which is uploded to KDP device by
        # removing SMBTestFolders through Windows mount point.
        try:
            cmd = "Remove-Item -Recurse -Force {}:\\{}; ".format(self.windows_mount_point, self.uut_share) 
            result = self.XMLRPCclient(cmd)
        except Exception as e:
            print e
            self.log.warning("Waiting for 300 seconds is workaround in order to avoid unknown error that caused incomplete deletion.")
            time.sleep(300)


    def after_loop(self):
        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'RestSDK', 'iteration', 'TotalBytes', 'TotalRealFiles', 'UpAvgSpd','TargetUpAvgSpd','Wifi','DesktopApp']
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'Direction', 'Client', "Protocol", "FileType", 'TotalRealFiles', 'TotalBytes', 'build', 'UpAvgSpd', 'TransferRate_unit', 'count', 'executionTime','Wifi','DesktopApp']
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
        stdout, stderr = self.ssh_client.execute_cmd("curl localhost/sdk/v1/device")
        return json.loads(stdout).get('version')


    def reboot_client(self):
        result = XMLRPCclient("Restart-Computer")
        temp = time.time()
        while True:
            time.sleep(30)
            result = XMLRPCclient('ipconfig')  # Just check if the XMLRPCserver is running.
            if "Connection refused" in result or "No route to host" in result or "Connection timed out" in result:
                print '\nWait for Windows rebooting\n'
            else:
                break
            if (time.time() - temp) > 300:
                self.log.error("Windows cannot be rebooted or XMLRPCserver is failed to launch.")
                break
        self.log.info("Windows rebooting finished")

        result = XMLRPCclient('Start-Process ".\WD-Discovery\WD Discovery\Launch WD Discovery.exe"')
        time.sleep(30)  # Wait until WD Discovery is launched.

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
    parser = KDPInputArgumentParser("""\
        *** Desktop_Sync_BAT on Kamino Android ***
        Examples: ./run.sh kdp_scripts/performance_tests/windows_smb_upload.py  --uut_ip 192.168.0.42:8001 --cloud_env dev1 --ssh_ip 192.168.0.42 --ssh_user sshd --ssh_password 123456 --debug  --loop_times 1  --dry_run  --stream_log_level INFO  --windows_client_ip 192.168.0.33 --windows_dataset_path C:\\5G_Standard_test1 --uut_share windows_smb  -dupr
        """)
    parser.add_argument('--windows_client_ip', help='windows_client_ip', default='192.168.0.13')
    parser.add_argument('--windows_mount_point', help='mount point on Windows client which is for mounting UUT share folder by DesktopApp.', default='Z')
    parser.add_argument('--windows_dataset_path', help='dataset path on Windows client.', default=None)
    parser.add_argument('--uut_share', help='the share folder in target device which could be accessed by SMB', default='desktopapp_upload')
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--target_up_avg_spd', help='Target of upload average speed.', default='11')
    parser.add_argument('--wifi_mode', help='type of wifi mode, by default is None', choices=['None','2.4G', '5G'], default='None')
    parser.add_argument('--desktopapp_version', help='desktopapp version ,by default is None', default='None')

    test = windowsDesktopAppUpload(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
