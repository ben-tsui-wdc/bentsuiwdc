# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
from xmlrpclib import ServerProxy
import json, re, socket, sys, time


# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.restAPI import RestAPI
from platform_libraries.ssh_client import SSHClient
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat


class MacUpload(GodzillaTestCase):

    TEST_SUITE = 'Godzilla KPI'
    TEST_NAME = 'GZA KPI Test case - Mac upload'
    # Popcorn
    TEST_JIRA_ID = ''


    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True
    }


    def declare(self):
        self.mac_client_ip = None
        self.usb_filesystem_id = None
        self.create_filesystem = 'off'
        self.test_result_list = []
        self.html_format = '2'
        self.mac_mount_share = '~/mac_GZA_mountpoint'
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

            # Delete all existing testing USB filesystem
            self.log.info("Delete all existing testing USB filesystem.")
            for fs in self.uut_owner.get_filesystem().get('filesystems', []):
                if fs.get('name', '').startswith('USB-'): self.uut_owner.delete_filesystem(filesystem_id=fs['id'])

            self.log.info("Add USB drive to restsdk indexing filesystem.")
            # Create usb share name with time
            self.usb_filesystem_name = 'USB-{}'.format(time.strftime("%Y%m%d-%H%M%S", time.gmtime()))
            self.log.info("USB filesystem name: {}".format(self.usb_filesystem_name))

            # Get vol id of USB
            usb_vol = self.uut_owner.get_volumes_by(cmp_vl=lambda vl: vl.get('mountPoint', '').startswith('/mnt/USB/USB'))
            if not usb_vol:
                raise self.err.StopTest("USB drive attached, but no USB volume found")
            self.usb_vol_id = usb_vol['volID']
            self.usb_mount_point = usb_vol['mountPoint']
            self.log.info("USB Vol id: {}".format(self.usb_vol_id))
            self.log.info("USB Vol mount point: {}".format(self.usb_mount_point))

            # Create filesystem with vol
            self.usb_filesystem_id = self.uut_owner.create_filesystem(vol_id=self.usb_vol_id, name=self.usb_filesystem_name)
            self.log.info("USB filesystem id: {}".format(self.usb_filesystem_id))

        # To make the new created folder can be accessed via afp
        stdout, stderr = self.ssh_client.execute_cmd("afpcom")

        # Create a SSH session with MacOS
        self.mac_ssh = SSHClient(self.mac_client_ip, self.mac_username, self.mac_password)
        self.mac_ssh.connect()


    def before_test(self):
        '''
        self.mac_ssh.unmount_folder(self.mac_mount_share, force=True)
        time.sleep(30)
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

        # Mount the share of GZA from Mac client
        self.mac_ssh.unmount_folder(self.mac_mount_share, force=True)
        self.mac_ssh.delete_folder(self.mac_mount_share)
        self.mac_ssh.create_folder(self.mac_mount_share)
        self.mac_ssh.mount_folder(self.transfer_protocol, self.env.ssh_ip, self.specific_folder, self.mac_mount_share)
        if self.mac_ssh.check_folder_mounted(self.specific_folder, protocol=self.transfer_protocol):
            pass
        else:
            raise self.err.TestError('GZA Share [{}] is NOT mounted on {}'.format(self.specific_folder, self.mac_mount_share))

        # Create uut_share name with timestamp on GZA device
        self.uut_share = self.uut_share_original + '_{}'.format(int(time.time()))
        self.log.info("uut_share name: {}".format(self.uut_share))

        self.log.info("Wait for 30 seconds before starting test iteration.")
        time.sleep(30)


    def test(self):
        total_bytes = self._get_file_size(file_path=self.mac_dataset_path)
        total_real_files = self._get_number_of_files(file_path=self.mac_dataset_path)
        MB_per_second = self._file_transfer(source_path=self.mac_dataset_path, dest_path="{}/{}".format(self.mac_mount_share, self.uut_share))
        
        # Update test_result
        self.data.test_result['Protocol'] = self.transfer_protocol.upper()
        self.data.test_result['TotalBytes'] = '{} MB'.format(total_bytes)
        self.data.test_result['TotalRealFiles'] = total_real_files
        self.data.test_result['UpAvgSpd'] = MB_per_second
        self.data.test_result['TargetUpAvgSpd'] = self.target_up_avg_spd
        self.data.test_result['RestSDK'] = self.restsdk_version

        # Update test_result for csv
        self.data.test_result['ShareAccess'] = self.create_filesystem
        self.data.test_result['Client'] = "Mac"
        self.data.test_result['FileType'] = self.mac_dataset_path
        self.data.test_result['Direction'] = 'Upload'

        # For Popcorn
        self.data.test_result['TransferRate_unit'] = 'Mbps'
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # milliseco


    def after_test(self):
        self.test_result_list.append(self.data.test_result)

        # Delete the dataset folder which is uploded to GZA device
        if self.delete_share_and_filesystem:
            # Remove TestFolders of testing device by Mac mount point.
            self.mac_ssh.delete_folder("{}/{}".format(self.mac_mount_share, self.uut_share))

                                   
    def after_loop(self):
        # Umount share from MacOS client
        self.mac_ssh.unmount_folder(self.mac_mount_share, force=True)
        self.mac_ssh.delete_folder(self.mac_mount_share)

        if self.delete_share_and_filesystem:
            if self.create_filesystem == 'on' and self.uut.get('firmware').startswith('5.'):
                if self.usb_filesystem_id:
                    self.log.warning('Delete test usb_filesystem_id.')
                    self.uut_owner.delete_filesystem(filesystem_id=self.usb_filesystem_id)

        # Restore the environment of device
        #stdout, stderr = self.ssh_client.execute_cmd("sudo -u restsdk otaclient.sh start", timeout=10)
        if self.create_filesystem == 'off':
            if self.uut.get('firmware').startswith('5.'):
                stdout, stderr = self.ssh_client.execute_cmd("sudo -u restsdk restsdk.sh start", timeout=10)
            elif self.uut.get('firmware').startswith('2.'):
                self.ssh_client.execute_cmd('/etc/init.d/wdphotodbmergerd start')
                self.ssh_client.execute_cmd('/etc/init.d/wdmcserverd start')
                self.ssh_client.execute_cmd('/etc/init.d/wdnotifierd start')

        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'RestSDK', 'Protocol', 'iteration', 'TotalBytes', 'TotalRealFiles', 'UpAvgSpd','TargetUpAvgSpd',]
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'Direction', 'ShareAccess', 'Client', "Protocol", "FileType", 'TotalRealFiles', 'TotalBytes', 'build', 'UpAvgSpd', 'TransferRate_unit', 'count', 'executionTime']
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


    def _get_file_size(self, file_path=None, unit='m', **kwarg):
        # unit='g', unit is GB
        # unit='m', unit is MB
        # unit='k', unit is KB
        total_file_size = None
        status, stdout = self.mac_ssh.execute('du -cs{} {}'.format(unit, file_path))
        if 'total' not in stdout.split('\n')[-1]:
            print '### WARNING: There is no "total" label in stdout. ###'
        else:
            total_file_size = float(stdout.split('\n')[-1].split()[0])
        return total_file_size


    def _file_transfer(self, source_path=None, dest_path=None, **kwarg):
        # start to transfer file
        upload_speed = 0
        status, stdout = self.mac_ssh.execute('time cp -fr {} {}'.format(source_path, dest_path), timeout=3600)
        if self.file_transfer_old_format:
            seconds = float(re.findall('real\t\d+m.+s', stdout)[0].split('real\t')[1].split('m')[0]) * 60 + \
                          float(re.findall('real\t\d+m.+s', stdout)[0].split('m')[1].split('s')[0])
            upload_speed = (self._get_file_size(file_path=source_path))/seconds  # This unit is MB after calculating.
        else:
            time_hms = stdout.split('cpu')[1].split('total')[0].strip()
            seconds = None
            for index, item in enumerate(list(reversed(time_hms.split(':')))):
                if index == 0:  # second
                    seconds = float(item)
                elif index == 1:  # minute
                    seconds += float(item) * 60
                elif index == 2:  # hour
                    seconds += float(item) * 3600
            upload_speed = (self._get_file_size(file_path=source_path))/seconds  # This unit is MB after calculating.    
        
        return upload_speed


    def _get_number_of_files(self, file_path=None):
        status, stdout = self.mac_ssh.execute("find {} -type f | wc -l".format(file_path))
        return stdout


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
        Examples: ./run.sh godzilla_scripts/performance_tests/mac_upload.py  --uut_ip 192.168.0.42:8001 --cloud_env dev1 --ssh_ip 192.168.0.42 --ssh_user sshd --ssh_password 123456 --debug  --loop_times 1  --dry_run  --stream_log_level INFO  --mac_client_ip 192.168.0.33 --uut_share mac_protocol  -dupr
        """)
    parser.add_argument('--mac_client_ip', help='mac_client_ip', default='192.168.0.19')
    parser.add_argument('--mac_username', help='mac_client_username', default='jc1000234162')
    parser.add_argument('--mac_password', help='mac_client_password', default='!QAZ2wsx3edc')
    parser.add_argument('--mac_dataset_path', help='dataset path on Mac client.', default='~/dataset_mix_test')
    parser.add_argument('--uut_share', help='the share folder in target device which could be accessed by SMB', default='mac_for_upload_test')
    parser.add_argument('--transfer_protocol', help='transfer_protocol, AFP/SMB', choices=['afp', 'smb'], default='afp')
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--target_up_avg_spd', help='Target of upload average speed.', default='11')
    parser.add_argument('--delete_share_and_filesystem', help='Delete share folder and filesystem_id in GZA', action='store_true')
    parser.add_argument('--create_filesystem', help='choose whether the folder is added to restsdk filesystem or not', choices=['on', 'off'], default='off')
    parser.add_argument('--specific_folder', help='Public or TimeMachineBackup', default='Public')
    parser.add_argument('--file_transfer_old_format', help='file_transfer_old_format', action='store_true')
    

    test = MacUpload(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
