# -*- coding: utf-8 -*-

__author1__ = "Ben Tsui <ben.tsui@wdc.com>"
__author2__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import sys
import os
import time

from multiprocessing import Process

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP
from platform_libraries.ssh_client import SSHClient

class PowerOnOffRWTest(KDPTestCase):

    TEST_SUITE = 'Power_Loss_Read_Write_Tests'
    TEST_NAME = 'Power_Loss_Read_Write_Tests'
    # Popcorn
    TEST_JIRA_ID = 'KAM-10020'
    REPORT_NAME = 'Stress'

    def init(self):
        if self.uut['model'] in ['monarch2', 'pelican2', 'yodaplus2']:
            self.root_folder = KDP.USER_ROOT_PATH
            self.rest_db_path = '/data/wd/diskVolume0/restsdk/data/db'
        elif self.uut['model'] in ['rocket', 'drax']:
            self.root_folder = '/Volume1/userStorage'
            self.rest_db_path = '/Volume1/restsdk-data/data/db'
        self.test_folder = 'test_folder'
        self.upload_file = 'upload_file.jpg'
        self.download_file = 'download_file.jpg'
        self.existed_file_num = int(self.existed_files)
        self.existed_files_md5_list = dict()
        self.owner_id = self.uut_owner.get_user_id(escape=True)

    def before_loop(self):
        self.log.info("Create {0} files in folder {1} and upload them into test device".
                      format(self.existed_file_num, self.test_folder))
        if not self.check_file_exist_in_nas(self.owner_id, self.test_folder):
            self.uut_owner.commit_folder(folder_name=self.test_folder)
        else:
            self.log.info("Folder: {} already exist!".format(self.test_folder))
        for file_num in range(self.existed_file_num):
            file_name = 'file{}.jpg'.format(file_num)
            if not self.check_file_exist_in_nas(self.owner_id, os.path.join(self.test_folder, file_name)):
                if not os.path.isfile(file_name):
                    self.create_random_file(file_name)
                with open(file_name, 'rb') as f:
                    self.log.info("Uploading file: {0} into test folder {1}".format(file_name, self.test_folder))
                    self.uut_owner.chuck_upload_file(file_object=f, file_name=file_name, parent_folder=self.test_folder)
            else:
                self.log.info("File: {} already exist!".format(file_name))
            if file_name not in self.existed_files_md5_list.keys():
                self.log.info('Getting the checksum of {}...'.format(file_name))
                checksum = self.md5_checksum(self.owner_id, os.path.join(self.test_folder, file_name))
                if checksum:
                    self.existed_files_md5_list[file_name] = checksum
                else:
                    error_message = 'Cannot get MD5 checksum of existed file: {}'.format(file_name)
                    self.err.TestFailure(error_message)
            else:
                self.log.info('Checksum of {} already exist'.format(file_name))
        self.log.info("Create file: {} for uploading test".format(self.upload_file))
        if not os.path.isfile(self.upload_file):
            self.create_random_file(self.upload_file, file_size=self.test_file_size)
        # Remove upload file content for checking upload process in the next steps
        if os.path.isfile('uploadFile'):
            os.remove('uploadFile')

    def before_test(self):
        pass

    def test(self):
        p1 = Process(target=self.upload_new_file, args=(self.owner_id, ))
        p2 = Process(target=self.power_on_off, args=('Upload', ))
        # Test power loss during uploading file
        p1.start()
        p2.start()
        p2.join()  # Wait for the reboot process complete
        # Check if the daemons are alive
        self.check_device_is_ready()
        self.check_fsck_log()
        self.check_md_raid()
        self.check_daemons()
        result = self.compare_md5(self.owner_id)
        if not result:
            upload_result = 'Failed'
            self.log.error("Power loss write test failed!")
        else:
            upload_result = 'Passed'
            self.log.info("Power loss write test passed!")
        p3 = Process(target=self.download_new_file, args=())
        p4 = Process(target=self.power_on_off, args=('Download', ))
        # Test power loss during downloading file
        p3.start()
        p4.start()
        p4.join()  # Wait for the reboot process complete
        # Check if the daemons are alive
        self.check_device_is_ready()
        self.check_fsck_log()
        self.check_md_raid()
        self.check_daemons()
        result = self.compare_md5(self.owner_id)
        if not result:
            download_result = 'Failed'
            self.log.error("Power loss read test failed!")
        else:
            download_result = 'Passed'
            self.log.info("Power loss read test passed!")
        self.data.test_result['powerULTestResult'] = upload_result
        self.data.test_result['powerDLTestResult'] = download_result
        # Send error exit code when failure to stop jenkins long turn job
        if upload_result == 'Failed':
            raise self.err.TestFailure("The upload test failed.")
        if download_result == 'Failed':
            raise self.err.TestFailure("The download test failed.")

    def after_test(self):
        pass

    def after_loop(self):
        def _delete_local_file(path):
            if os.path.isfile(path):
                self.log.info('Deleting file: {}'.format(path))
                os.remove(path)

        self.log.info('Cleaning local environment...')
        _delete_local_file(self.download_file)
        _delete_local_file('uploadFolder')
        _delete_local_file('uploadFile')
        #self.log.info('Cleaning NAS environment...')
        # Delete whole folder if delete_nas_files is True, otherwise just delete the upload_file and keep the rests
        #folder_id = self.uut_owner.get_data_id_list(type='folder', data_name=self.test_folder)
        #self.uut_owner.delete_file(folder_id)
        self.log.info('Clean up finished!')

    def check_file_exist_in_nas(self, user_id, file_path, retry=False):
        self.ssh_client_cfein = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_cfein.connect()
        path = '{0}/{1}/{2}'.format(self.root_folder, user_id, file_path)
        max_retries = 3
        for retries in range(max_retries):
            stdout, stderr = self.ssh_client_cfein.execute_cmd('[ -e {} ] && echo "Found" || echo "Not Found"'.format(path))
            result = stdout.strip()
            if result == "Found":
                self.ssh_client_cfein.close()
                return True
            else:
                if retry:
                    # Sleep 30 secs and retry
                    self.log.info('Cannot find file:{}, retry after 30 secs'.format(file_path))
                    time.sleep(30)
                else:
                    self.ssh_client_cfein.close()
                    return False
        self.ssh_client_cfein.close()
        return False

    def create_random_file(self, file_name, local_path='', file_size=''):
        self.log.info("Creating file: {}...".format(file_name))
        if not file_size:
            file_size = self.test_file_size
        try:
            with open(os.path.join(local_path, file_name), 'wb') as f:
                f.write(os.urandom(int(file_size)))
        except Exception as e:
            self.err.TestError("Failed to create file: {0}, error message: {1}".format(local_path, repr(e)))

    def md5_checksum(self, user_id, file_path):
        self.ssh_client_mc = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_mc.connect()
        path = os.path.join(self.root_folder, user_id, file_path)
        stdout, stderr = self.ssh_client_mc.execute_cmd('busybox md5sum {}'.format(path))
        result = stdout.strip().split()[0]
        self.ssh_client_mc.close()
        return result

    def compare_md5(self, owner_id):
        result = True
        for file_num in range(self.existed_file_num):
            file_name = 'file{}.jpg'.format(file_num)
            if not self.check_file_exist_in_nas(owner_id, os.path.join(self.test_folder, file_name), retry=True):
                self.log.error('File: {} is missing!'.format(file_name))
                result = False
            else:
                checksum = self.md5_checksum(owner_id, os.path.join(self.test_folder, file_name))
                self.log.info('##### File: {} md5 checksum result #####'.format(file_name))
                self.log.info('Before: {}'.format(self.existed_files_md5_list[file_name]))
                self.log.info('After: {}'.format(checksum))
                if checksum != self.existed_files_md5_list[file_name]:
                    self.log.error('{} md5 comparison failed!'.format(file_name))
                    result = False
        return result

    def upload_new_file(self, owner_id):
        self.ssh_client_unf = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_unf.connect()
        if self.check_file_exist_in_nas(owner_id, os.path.join(self.test_folder, self.upload_file)):
            path = os.path.join(self.root_folder, owner_id, self.test_folder, self.upload_file)
            stdout, stderr = self.ssh_client_unf.execute_cmd('rm -f {}'.format(path))
        try:
            with open(self.upload_file, 'rb') as f:
                self.log.info("Start uploading file to test device...")
                self.uut_owner.chuck_upload_file(file_object=f, file_name=self.upload_file, parent_folder=self.test_folder)
                self.log.error("Upload file complete, but should be interrupted by power loss")
        except Exception as e:
            self.log.info("Expected exception due to power loss, message:{}".format(repr(e)))
            pass
        self.ssh_client_unf.close()

    def download_new_file(self):
        if os.path.isfile(self.download_file):
            os.remove(self.download_file)
        folder_id = self.uut_owner.get_data_id_list(type='folder', data_name=self.test_folder)
        file_id = self.uut_owner.get_data_id_list(type='file', parent_id=folder_id, data_name='file0.jpg')
        try:
            self.log.info("Start downloading file from test device...")
            content = self.uut_owner.get_file_content_v3(file_id).content
            with open(self.download_file, 'wb') as f:
                f.write(content)
            self.log.error("Download file complete, but should be interrupted by power loss")
        except Exception as e:
            self.log.info("Expected exception due to power loss, message:{}".format(repr(e)))
            pass

    def power_on_off(self, test_type):
        timeout = 300
        self.log.warning("\n\n Reboot UUT roughly... (Execute 'reboot' rather than 'do_reboot')\n\n")
        self.ssh_client_poo = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_poo.connect()
        start_time = time.time()
        self.ssh_client_poo.execute_background('reboot')
        if not self.ssh_client_poo.wait_for_device_to_shutdown(timeout=timeout):
            raise self.err.TestFailure('Device was not shut down successfully!')
        if 'yodaplus' in self.uut.get('model') and hasattr(self, 'serial_client'):
            self.serial_client.wait_for_boot_complete_kdp(timeout=timeout)
        if not self.ssh_client_poo.wait_for_device_boot_completed(timeout=timeout):
            raise self.err.TestFailure('Device was not boot up successfully!')
        self.ssh_client_poo.close()
        self.log.warning("Reboot complete in {} seconds".format(time.time() - start_time))

    def check_fsck_log(self):
        self.ssh_client_cfl = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_cfl.connect()
        stdout, stderr = self.ssh_client_cfl.execute_cmd('ls /var/log/analyticpublic.log')
        if "No such file or directory" in stderr:
            self.log.warning("There is no /var/log/analyticpublic.log, maybe it's due to logrotate.")
        else:
            fs_chk_flag = False
            fs_chk_complete_flag = False
            auto_mount_flag = False
            stdout, stderr = self.ssh_client_cfl.execute_cmd('cat /var/log/analyticpublic.log | grep -i DiskManager')
            diskmanager_log_list = stdout.split('\n')
            for line in diskmanager_log_list:
                if "Perform filesystem check for non-clean shutdown." in line:
                    fs_chk_flag = True
                    print line
                if fs_chk_flag:
                    if "It took" and "seconds to finish filesystem check" in line:
                        fs_chk_complete_flag = True
                        print line
                if fs_chk_complete_flag:
                    if "auto mounting finish" in line:
                        auto_mount_flag = True
                        print line
            if not fs_chk_flag:
                self.log.warning("cat /var/log/analyticpublic.log if there is no 'filesystem check'.")
                stdout, stderr = self.ssh_client_cfl.execute_cmd('cat /var/log/analyticpublic.log')
                stdout, stderr = self.ssh_client_cfl.execute_cmd('dumpe2fs -h /dev/md1')
                #raise self.err.TestError("There is no 'filesystem check' log in analyticpublic.log after abnormal reboot.")
                self.log.warning("There is no 'filesystem_check' log in analyticpublic.log after abnormal reboot.")
            if not fs_chk_complete_flag:
                #raise self.err.TestError("There is no 'filesystem check finish' log in analyticpublic.log after starting filesystem check.")
                self.log.warning("There is no 'filesystem_check finish' log in analyticpublic.log after starting filesystem check.")
            if not auto_mount_flag:
                #raise self.err.TestError("There is no 'auto mounting finish' in analyticpublic.log")
                self.log.warning("There is no 'auto mounting finish' in analyticpublic.log")
        self.ssh_client_cfl.close()

    def check_daemons(self):
        self.ssh_client_cd = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_cd.connect()
        daemon_alive = True
        self.log.info('Checking daemon status')
        retry_count = 10
        retry_interval = 10   # seconds 
        for x in xrange(retry_count):
            stdout, stderr = self.ssh_client_cd.execute_cmd('ps | grep restsdk')
            if 'restsdk-server' in stdout:
                self.log.info('RestSDK daemon: Passed')
                restsdk_result = 'Passed'
                break
            else:
                if x == retry_count - 1:
                    self.log.error('RestSDK daemon: Failed')
                    restsdk_result = 'Failed'
                    daemon_alive = False
                    self.log.warning("The restsdk-server is not launched after retrying for {} seconds \r\n".format(x * retry_interval))
                else:
                    self.log.info('Retry for "grep restsdk" #{}'.format(x+1))
                    time.sleep(retry_interval)
        if self.uut_owner.get_uut_info():
            self.log.info('RestAPI: Passed')
            restapi_result = 'Passed'
        else:
            self.log.error('RestAPI: Failed')
            restapi_result = 'Failed'
            daemon_alive = False
        stdout, stderr = self.ssh_client_cd.execute_cmd('ls -l {}'.format(self.rest_db_path))                                                     
        if 'index.db' not in stdout:
            self.log.error('RestSDK DB daemon: Failed, index.db not exist')
            rest_db = 'Failed'
            daemon_alive = False
        elif 'index.db-shm' not in stdout:
            self.log.error('RestSDK DB daemon: Failed, index.db-shm not exist')
            rest_db = 'Failed'
            daemon_alive = False
        elif 'index.db-wal' not in stdout:
            self.log.error('RestSDK DB daemon: Failed, index.db-wal not exist')
            rest_db = 'Failed'
            daemon_alive = False
        else:
            self.log.info('RestSDK DB daemon: Passed')
            rest_db = 'Passed'
        stdout, stderr = self.ssh_client_cd.execute_cmd('ps | grep otaclient')
        if 'otaclient -configPath' in stdout:
            self.log.info('OTA client daemon: Passed')
            ota_client = 'Passed'
        else:
            self.log.error('OTA client daemon: Failed')
            ota_client = 'Failed'
            daemon_alive = False
        if self.uut['model'] in ['yodaplus2']:
            self.log.info('Avahi is not supported so skip Avahi testing')
        else:         
            stdout, stderr = self.ssh_client_cd.execute_cmd('ps | grep avahi')
            if 'avahi-daemon: running' in stdout:
                self.log.info('Avahi daemon: Passed')
                avahi = 'Passed'
            else:
                self.log.error('Avahi daemon: Failed')
                avahi = 'Failed'
                daemon_alive = False
        stdout, stderr = self.ssh_client_cd.execute_cmd('ps | grep appmgr')
        if 'kdpappmgr' in stdout:
            self.log.info('Appmgr daemon: Passed')
            appmgr = 'Passed'
        else:
            self.log.error('Appmgr daemon: Failed')
            appmgr = 'Failed'
            daemon_alive = False
        if self.uut['model'] in ['rocket', 'drax']:
            stdout, stderr = self.ssh_client_cd.execute_cmd('ps | grep nasadmin')
            if 'nasadmin -configPath' in stdout:
                self.log.info('nasadmin daemon: Passed')
                nasadmin = 'Passed'
            else:
                self.log.error('nasadmin daemon: Failed')
                nasadmin = 'Failed'
                daemon_alive = False

        '''
        # Need to confirm if there is satalink message in KDP
        result = self.adb.executeShellCommand('logcat -d | grep "SATA link down"', consoleOutput=False, timeout=60*2)[0]
        if 'SATA link down' not in result:
            self.log.info('SATA link: Passed')
            sata_link = 'Passed'
        else:
            self.log.error('SATA link: Failed')
            sata_link = 'Failed'
            daemon_alive = False
        '''
        self.data.test_result['restsdk'] = restsdk_result
        self.data.test_result['restapi'] = restapi_result
        self.data.test_result['rest_db'] = rest_db
        self.data.test_result['otaclient'] = ota_client
        self.data.test_result['appmgr'] = appmgr
        if self.uut['model'] in ['rocket', 'drax']:
            self.data.test_result['nasadmin'] = nasadmin
        #self.data.test_result['sata_link'] = sata_link
        if self.uut['model'] not in ['yodaplus2']:
            self.data.test_result['avahi'] = avahi
        self.ssh_client_cd.close()
        if not daemon_alive:
            raise self.err.TestFailure('At least one daemon check failed, stop the test!')

    def check_md_raid(self):
        if self.uut['model'] in ['pelican2', 'drax']:
            self.ssh_client_cmr = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
            self.ssh_client_cmr.connect()
            stdout, stderr = self.ssh_client_cmr.execute_cmd('mdadm --detail /dev/md1')
            if 'State : clean, degraded' in stdout or 'State : active, degraded' in stdout:
                raise self.err.TestFailure('The md raid is degraded.')
            if 'Active Devices : 2' not in stdout or 'Working Devices : 2' not in stdout:
                raise self.err.TestFailure('The "Active/Working Devices" is not 2.')
            self.timing.reset_start_time()
            while not self.timing.is_timeout(300): # Wait for getprop wd.volume.state
                stdout, stderr = self.ssh_client_cmr.execute_cmd('getprop wd.volume.state')
                if stdout.strip() != 'clean': 
                    self.log.warning('"getprop wd.volume.state" is not clean, wait for 30 secs and try again...')
                    time.sleep(30)
                else:
                    break
            else:
                raise self.err.TestFailure('"getprop wd.volume.state" is not clean.')
            self.ssh_client_cmr.close()

    def check_device_is_ready(self):
        self.log.info('Checking if device is ready and proxyConnect is True')
        self.ssh_client_cdi = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_cdi.connect()
        self.timing.reset_start_time()
        while not self.timing.is_timeout(300):
            try:
                if self.ssh_client_cdi.get_device_ready_status() and self.ssh_client_cdi.get_device_proxy_connect_status():
                    self.log.info('Device is ready and proxyConnect is True.')
                    break
                else:
                    self.log.warning('Device is not ready, wait for 5 secs and try again ...')
                    time.sleep(5)
            except RuntimeError as e:
                self.log.warning(e)
        else:
            raise self.err.TestFailure('Device status is not ready after retry for 300 secs!')
        self.ssh_client_cdi.close()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Read Write data during power loss test ***\
        """)
    parser.add_argument('--existed_files', help='How many files created in device before running tests', default=5)
    parser.add_argument('--test_file_size', help='How many bytes for test file', default=524288000)

    test = PowerOnOffRWTest(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1) 
