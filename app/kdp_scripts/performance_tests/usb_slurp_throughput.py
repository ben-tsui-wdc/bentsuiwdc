# -*- coding: utf-8 -*-
""" kpi test for usb slurp throughput.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import calendar
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.restAPI import RestAPI
from kdp_scripts.bat_scripts.factory_reset import FactoryReset
from kdp_scripts.bat_scripts.reboot import Reboot
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat


class usb_slurp_throughput(KDPTestCase):
    TEST_SUITE = 'Performance_Tests'
    TEST_NAME = 'kpi_usb_slurp_throughput'
    # Popcorn
    TEST_JIRA_ID = 'KDP-848,KDP-849'

    SETTINGS = {'uut_owner' : False # Disbale restAPI.
    }

    # Pre-defined parameters for IntegrationTest
    def declare(self):
        self.folder_name = None
        self.wifi_mode = 'None'
        self.timeout = 259200
        self.no_factory_reset = False
        self.api_version = 'v1'
        self.test_result_list = []
        self.html_format = '2'
        # Popcorn
        self.VERSION= 'InternalBeta'

    '''
    # It's obsolete for now.
    def get_usb_name(self):
        usb_info = self.uut_owner.get_usb_info()
        self.usb_id = usb_info.get('id')
        self.usb_name = usb_info.get('name')
        self.log.info('USB Name is: {}'.format(self.usb_name))
        self.log.info('USB id is: {}'.format(self.usb_id))
    '''

    def check_usb(self):
        usb_location = None
        stdout, stderr = self.ssh_client.execute_cmd("df  | grep mnt/USB | awk '{print $6}'")
        if stdout:
            return stdout.strip()
        else:
            self.log.warning("USB drive is not mounted on /mnt/USB.")
            return False
        '''
        # Below is for Android MCH, need to do more investigation for KDP
        stdout, stderr = self.adb.executeShellCommand('ls /dev/block/vold | grep public')
        if stdout:
            usb_location = '/dev/block/vold/{}'.format(stdout.strip())
            self.log.info("usb_location_on_platform: {}".format(usb_location))
        else:
            self.log.warning("There is no USB drive on dev/block/vold.")
            return False
        '''


    def before_test(self):
        if self.no_factory_reset:
            self.log.info('###### no factory_reset ######')
            pass
        else:
            env_dict = self.env.dump_to_dict()
            env_dict['Settings'] = ['uut_owner=False']
            self.log.info('start factory_reset')
            factory_reset = FactoryReset(env_dict)
            factory_reset.run_rest_api = False
            factory_reset.test()
            self.ssh_client.lock_otaclient_service_kdp()
            # Device will spend some times to initialize disk after factory_reset
            self.log.info("Wait 180 seconds for Disk Initialization after factory_reset")
            time.sleep(180)
        if self.env.cloud_env == 'prod':
            with_cloud_connected = False
        else:
            with_cloud_connected = True
        self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
        self.uut_owner.id = 0  # Reset uut_owner.id
        self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']}, with_cloud_connected=with_cloud_connected)

        # Check if the USB drive is mounted by platform
        reboot_limit = 5
        iteration = 0
        # workaround for https://jira.wdmv.wdc.com/browse/IBIX-5628
        while not self.check_usb():
            if iteration == reboot_limit:
                raise self.err.TestError("USB drive is still not found after rebooting target device {} times!".format(reboot_limit))
            iteration += 1
            self.log.warning("Start to reboot target device because there is no USB drive mounted, iteration: {}".format(iteration))
            env_dict = self.env.dump_to_dict()
            env_dict['Settings'] = ['uut_owner=False']
            self.log.info('start reboot device')
            reboot = Reboot(env_dict)
            reboot.no_rest_api = True
            reboot.test()

        self.log.info("Wait more 5 seconds to start USB slurp, in order to avoid that disk is not ready after factory_reset/reboot.")
        time.sleep(5)  


    # main function
    def test(self):
        self.log.info('###### start usb slurp throughput test, iteration: {} ######'
                      .format(self.env.iteration))
        if self.api_version == 'v1':
            # Trigger usb slurp
            try:
                copy_id, usb_info, result = self.uut_owner.usb_slurp(usb_name=None, folder_name=self.folder_name, timeout=self.timeout, wait_until_done=True, api_version=self.api_version)
            except Exception as ex:
                raise self.err.TestError('trigger_usb_slurp Failed!! Err: {}'.format(ex))
            usb_slurp_elapsed_time = result['elapsedDuration']
            usb_slurp_total_byte = result['totalBytes']
            usb_slurp_total_size = int(usb_slurp_total_byte)/1024/1024
            usb_slurp_avg = usb_slurp_total_size/usb_slurp_elapsed_time

        elif self.api_version == 'v2':
            # Following is to find out the sourceID
            usb_drive_path = self.check_usb()
           # Create filesystem with specific folder of USB drive
            self.uut_owner.create_filesystem(folder_path='{}/{}'.format(usb_drive_path, self.folder_name))
            # Find out the filesystem_id of specific folder in USB drive
            result = self.uut_owner.get_filesystem()
            for filesystem in result.get('filesystems'):  # result.get('filesystems') is a list
                if filesystem.get('path') == '{}/{}'.format(usb_drive_path, self.folder_name):
                    source_ids = filesystem.get('rootID')
                    self.log.warning("The rootID of source [path: {}/{}] is {}".format(usb_drive_path, self.folder_name, source_ids))
                    break
            # Following is to find out the targetID which is filesystem_id of uut_onwer folder
            uut_owner_user_id = self.uut_owner.get_user_id()
            result = self.uut_owner.get_filesystem()
            for filesystem in result.get('filesystems'):  # result.get('filesystems') is a list
                if filesystem.get('path') == '/Volume1/userStorage/{}'.format(uut_owner_user_id):
                    target_id = filesystem.get('rootID')
                    self.log.warning("The rootID of target [path: /Volume1/userStorage/{}] is {}".format(uut_owner_user_id, target_id))
                    break
            # Trigger usb slurp
            try:
                copy_id, usb_info, result = self.uut_owner.usb_slurp(data_id=[source_ids], dest_parent_id=target_id, timeout=self.timeout, wait_until_done=True, api_version=self.api_version)
            except Exception as ex:
                raise self.err.TestError('trigger_usb_slurp Failed!! Err: {}'.format(ex))
            '''
             INFO     USB slurp status: {u'status': u'completed', u'finishTime': u'2022-07-04T19:12:48.348770544Z', u'filesSkipped': 0, u'filesErrored': 0, u'bytesCopied': 13619278560, u'filesCopied': 1, u'jobid': u'tu5iranoq4irmfecyxa5horr', u'startTime': u'2022-07-04T19:10:35.742811475Z', u'filesExpected': 1, u'bytesExpected': 13619278560}

            '''
            epoch_start = calendar.timegm(time.strptime(result['startTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S'))
            epoch_finish = calendar.timegm(time.strptime(result['finishTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S'))
            usb_slurp_elapsed_time = int(epoch_finish) - int(epoch_start)
            usb_slurp_total_byte = result['bytesCopied']
            usb_slurp_total_size = float(usb_slurp_total_byte)/1024/1024
            usb_slurp_avg = usb_slurp_total_size/usb_slurp_elapsed_time

        self.data.test_result['FileType'] = self.folder_name
        self.data.test_result['wifi_mode'] = self.wifi_mode
        self.data.test_result['FileSize'] = '{}MB'.format(usb_slurp_total_size)
        self.data.test_result['usb_slurp_elapsed_time'] = usb_slurp_elapsed_time
        self.data.test_result['AvgSpd'] = usb_slurp_avg
        self.data.test_result['TargetAvgSpd'] = self.target_avg_spd
        self.data.test_result['Direction'] = self.direction
        self.data.test_result['USBFileSystem'] = self.usb_file_system
        
        # For Popcorn
        self.data.test_result['TransferRate_unit'] = 'Mbps'
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # millisecond


    def after_test(self):
        self.test_result_list.append(self.data.test_result)


    def after_loop(self):
        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'USBFileSystem', 'Direction', 'FileType', 'FileSize', 'AvgSpd']
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'Direction', 'USBFileSystem', 'FileType', 'FileSize', 'build', 'AvgSpd', 'TransferRate_unit', 'count', 'executionTime']
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




if __name__ == '__main__':

    parser = KDPInputArgumentParser("""\
        *** time_machine_throughput test on Kamino Android ***
        Examples: ./run.sh performance_tests/usb_slurp_throughput_new.py --uut_ip 10.92.224.13 \
        --cloud_env qa1 --folder_name single --loop_times 3 --debug_middleware --dry_run\
        (optional)--serial_server_ip fileserver.hgst.com --serial_server_port 20015
        """)
    parser.add_argument('--wifi_mode', help='type of wifi mode, by default is None', choices=['None','2.4G', '5G'], default='None')
    parser.add_argument('--folder_name', help='specify the folder_name which is usb slurped.', default=None)
    parser.add_argument('--timeout', help='specify the timeout of usb slurp.', default=259200)
    parser.add_argument('--no_factory_reset', help='Don\'t execute factory_reset.', action='store_true')
    parser.add_argument('--target_avg_spd', help='Target of usb sluro average speed.', default='11')
    parser.add_argument('--direction', help='import/export.', default='import')
    parser.add_argument('--usb_file_system', help='file system of USB drive', default='NTFS')
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--api_version', help='RESTSDK API version for USB slurp', default='v1')


    test = usb_slurp_throughput(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)