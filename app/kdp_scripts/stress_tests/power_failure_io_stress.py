# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import os
import time

from multiprocessing import Process

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.compare import compare_images
from platform_libraries.pyutils import save_to_file
from platform_libraries.ssh_client import SSHClient

class PowerOnOffRWTest(KDPTestCase):

    TEST_SUITE = 'Power_Loss_Read_Write_Tests'
    TEST_NAME = 'Power_Loss_Read_Write_Tests'
    # Popcorn
    TEST_JIRA_ID = 'KAM-10020'
    REPORT_NAME = 'Stress'

    def init(self):
        self.root_folder = '/var/run/restsdk/userRoots/'
        self.test_folder = 'test_folder'
        self.upload_file = 'upload_file.jpg'
        self.download_file = 'download_file.jpg'
        self.existed_file_num = int(self.existed_files)
        self.existed_files_md5_list = dict()
        self.owner_id = self.uut_owner.get_user_id(escape=True)

    def _check_file_exist_in_nas(self, user_id, file_path, retry=False):
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

    def _create_random_file(self, file_name, local_path='', file_size=''):
        self.log.info("Creating file: {}...".format(file_name))
        if not file_size:
            file_size = self.test_file_size
        try:
            with open(os.path.join(local_path, file_name), 'wb') as f:
                f.write(os.urandom(int(file_size)))
        except Exception as e:
            self.err.TestError("Failed to create file: {0}, error message: {1}".format(local_path, repr(e)))

    def _md5_checksum(self, user_id, file_path):
        self.ssh_client_mc = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_mc.connect()
        path = os.path.join(self.root_folder, user_id, file_path)
        stdout, stderr = self.ssh_client_mc.execute_cmd('busybox md5sum {}'.format(path))
        result = stdout.strip().split()[0]
        self.ssh_client_mc.close()
        return result

    def _compare_md5(self, owner_id):
        result = True
        for file_num in range(self.existed_file_num):
            file_name = 'file{}.jpg'.format(file_num)
            if not self._check_file_exist_in_nas(owner_id, os.path.join(self.test_folder, file_name), retry=True):
                self.log.error('File: {} is missing!'.format(file_name))
                result = False
            else:
                checksum = self._md5_checksum(owner_id, os.path.join(self.test_folder, file_name))
                self.log.info('##### File: {} md5 checksum result #####'.format(file_name))
                self.log.info('Before: {}'.format(self.existed_files_md5_list[file_name]))
                self.log.info('After: {}'.format(checksum))
                if checksum != self.existed_files_md5_list[file_name]:
                    self.log.error('{} md5 comparison failed!'.format(file_name))
                    result = False
        return result

    def _upload_new_file(self, owner_id):
        self.ssh_client_unf = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_unf.connect()
        if self._check_file_exist_in_nas(owner_id, os.path.join(self.test_folder, self.upload_file)):
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

    def _download_new_file(self):
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

    def _power_on_off(self, test_type):
        if test_type == 'Upload':
            timer = 0
            while timer < 60:
                if os.path.isfile('uploadFile'):
                    upload_file_size = os.path.getsize('uploadFile')
                    self.log.info("current_upload_binary_size:{}".format(upload_file_size))
                    if int(upload_file_size) >= int(self.test_file_size):
                        # Wait for 3 secs after starting upload data
                        time.sleep(3)
                        break
                timer += 1
                time.sleep(1)
        elif test_type == 'Download':
            # Todo: find a better way to check download start
            time.sleep(1)
        else:
            self.log.error('Unknown test type: {}!'.format(test_type))

        self.log.info("Powering off the device")
        self.power_switch.power_off(self.env.power_switch_port)
        time.sleep(10)  # interval between power off and on
        self.log.info("Powering on the device")
        self.power_switch.power_on(self.env.power_switch_port)
        self.log.info("Wait for reboot process complete")
        time.sleep(90)  # Sleep 90 secs and then check the bootable flag

        self.ssh_client_poo = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_poo.connect()
        if not self.ssh_client_poo.wait_for_device_boot_completed(timeout=300):
            self.log.error('Device seems down.')
            raise self.err.TestFailure('Timeout({}secs) to wait device boot completed.'.format(300))
        self.ssh_client_poo.close()

    def _check_daemons(self):
        self.ssh_client_cd = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_cd.connect()

        daemon_alive = True
        self.log.info('Checking daemon status')
        stdout, stderr = self.ssh_client_cd.execute_cmd('ps | grep restsdk')
        if 'restsdk-server' in stdout:
            self.log.info('RestSDK daemon: Passed')
            restsdk_result = 'Passed'
        else:
            self.log.error('RestSDK daemon: Failed')
            restsdk_result = 'Failed'
            daemon_alive = False

        if self.uut_owner.get_uut_info():
            self.log.info('RestAPI: Passed')
            restapi_result = 'Passed'
        else:
            self.log.error('RestAPI: Failed')
            restapi_result = 'Failed'
            daemon_alive = False

        stdout, stderr = self.ssh_client_cd.execute_cmd('ls -l /data/wd/diskVolume0/restsdk/data/db')
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
        #self.data.test_result['sata_link'] = sata_link
        if self.uut['model'] not in ['yodaplus2']:
            self.data.test_result['avahi'] = avahi

        self.ssh_client_cd.close()

        return daemon_alive

    def before_loop(self):

        self.log.info("Create {0} files in folder {1} and upload them into test device".
                      format(self.existed_file_num, self.test_folder))

        if not self._check_file_exist_in_nas(self.owner_id, self.test_folder):
            self.uut_owner.commit_folder(folder_name=self.test_folder)
        else:
            self.log.info("Folder: {} already exist!".format(self.test_folder))

        for file_num in range(self.existed_file_num):
            file_name = 'file{}.jpg'.format(file_num)
            if not self._check_file_exist_in_nas(self.owner_id, os.path.join(self.test_folder, file_name)):
                if not os.path.isfile(file_name):
                    self._create_random_file(file_name)

                with open(file_name, 'rb') as f:
                    self.log.info("Uploading file: {0} into test folder {1}".format(file_name, self.test_folder))
                    self.uut_owner.chuck_upload_file(file_object=f, file_name=file_name, parent_folder=self.test_folder)
            else:
                self.log.info("File: {} already exist!".format(file_name))

            if file_name not in self.existed_files_md5_list.keys():
                self.log.info('Getting the checksum of {}...'.format(file_name))
                checksum = self._md5_checksum(self.owner_id, os.path.join(self.test_folder, file_name))
                if checksum:
                    self.existed_files_md5_list[file_name] = checksum
                else:
                    error_message = 'Cannot get MD5 checksum of existed file: {}'.format(file_name)
                    self.err.TestFailure(error_message)
            else:
                self.log.info('Checksum of {} already exist'.format(file_name))

        self.log.info("Create file: {} for uploading test".format(self.upload_file))
        if not os.path.isfile(self.upload_file):
            self._create_random_file(self.upload_file, file_size=self.test_file_size)

        # Remove upload file content for checking upload process in the next steps
        if os.path.isfile('uploadFile'):
            os.remove('uploadFile')

    def before_test(self):
        pass

    def test(self):
        p1 = Process(target=self._upload_new_file, args=(self.owner_id, ))
        p2 = Process(target=self._power_on_off, args=('Upload', ))
        # Test power loss during uploading file
        p1.start()
        p2.start()
        p2.join()  # Wait for the reboot process complete

        # Check if the daemons are alive
        self._check_daemons()
        result = self._compare_md5(self.owner_id)
        if not result:
            upload_result = 'Failed'
            self.log.error("Power loss write test failed!")
        else:
            upload_result = 'Passed'
            self.log.info("Power loss write test passed!")

        p3 = Process(target=self._download_new_file, args=())
        p4 = Process(target=self._power_on_off, args=('Download', ))
        # Test power loss during downloading file
        p3.start()
        p4.start()
        p4.join()  # Wait for the reboot process complete

        # Check if the daemons are alive
        daemon_alive = self._check_daemons()

        result = self._compare_md5(self.owner_id)
        if not result:
            download_result = 'Failed'
            self.log.error("Power loss read test failed!")
        else:
            download_result = 'Passed'
            self.log.info("Power loss read test passed!")

        self.data.test_result['powerULTestResult'] = upload_result
        self.data.test_result['powerDLTestResult'] = download_result

        # Send error exit code when failure to stop jenkins long turn job
        if upload_result == 'Failed' or download_result == 'Failed':
            sys.exit(1)

        if not daemon_alive:
            self.log.error('At least one daemon check failed, stop the test!')
            sys.exit(1)

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
        self.log.info('Cleaning NAS environment...')
        # Delete whole folder if delete_nas_files is True, otherwise just delete the upload_file and keep the rests
        folder_id = self.uut_owner.get_data_id_list(type='folder', data_name=self.test_folder)
        self.uut_owner.delete_file(folder_id)
        self.log.info('Clean up finished!')

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