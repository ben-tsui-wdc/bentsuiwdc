# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
from xmlrpclib import ServerProxy
import json, re, socket, sys, time

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.restAPI import RestAPI
#from kdp_scripts.bat_scripts.reboot import Reboot
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat


class BootTimeKPI(KDPTestCase):

    TEST_SUITE = 'KDP KPI'
    TEST_NAME = 'KDP KPI Test case - Boot Time KPI'
    # Popcorn
    TEST_JIRA_ID = ''


    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True
    }


    def declare(self):
        self.test_result_list = []
        self.html_format = '2'
        # Popcorn
        self.VERSION= 'InternalBeta'


    def init(self):
        if self.uut['model'] in ['monarch2', 'pelican2', 'yodaplus2']:
            self.data_volume_path = '/data/wd/diskVolume0'
        elif self.uut['model'] in ['rocket', 'drax']:
            self.data_volume_path = '/Volume1'
        self.main_volume = ''


    def before_loop(self):
        pass


    def before_test(self):
        # Reboot device
        self.log.info("Rebooting the device at the beginning of test iteration...")
        self.ssh_client.reboot_device()
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=60*20):
            raise self.err.TestError('Device was not shut down successfully!')
        
        st = time.time()
        print '@@@@@@ {}'.format(st)
        while True:
            try:    
                #self.ssh_client.connect(timeout=1)
                self.ssh_client.connect()
                break
            except Exception as e:
                #print str(e) + ' -- ' + str(time.time())
                time.sleep(1)
                pass
            if time.time() - st > 180:
                raise self.err.TestError("Device cannot be ssh after rebooting for 180 seconds.")
        et = time.time()
        print '@@@@@@ {}'.format(et)
        print 're-ssh duration after rebooting: {} sec\n\n'.format(et - st)
        '''
        if not self.ssh_client.wait_for_device_boot_completed(timeout=60*5):
            raise self.err.TestError('Device was not boot up successfully after 300 seconds!')
        # Check if flag "system_ready" exist. This check is already included in self.ssh_client.wait_for_device_boot_completed.
        '''

    def test(self):
        timestamp_dict = {}
        start_time = time.time()
        while time.time() - start_time < 300:
            stdout, stderr = self.ssh_client.execute_cmd('ls {}'.format(self.data_volume_path))
            if 'userStorage' not in stdout:
                self.log.warning("The userStorage is not mounted.")
            else:
                self.log.info("The userStorage is mounted successfully.")
                break
            time.sleep(1)
        duration = time.time() - start_time
        self.log.warning("'user root volume' takes additional {} secs to be mounted after rebooting and ssh connection is re-established.".format(duration))
        # EXT4-fs
        cmd = "dmesg | grep EXT4-fs | grep 'mounted filesystem with ordered data mode. Opts: noinit_itable' | grep '({})'".format(self.get_main_volume())
        volume_mounted_time = "{}".format(self.get_dmesg_timestamp_with_keyword(cmd))
        self.log.info('######### volume_mounted_time: {}'.format(volume_mounted_time))
        timestamp_dict.update({"volume_mounted_time":float(volume_mounted_time)})

        if self.uut.get('model') in ('yodaplus2') or self.uut.get('model') in ('rocket', 'drax'):
            # wlan0
            if self.uut['model'] in ('yodaplus2'):
                cmd = "dmesg | grep 'RTW: wlan0 wakeup m0=0x00000002'"
            elif self.uut.get('model') in ('rocket', 'drax'):
                cmd = "dmesg | grep 'RTW: rtw_ndev_init(wlan0)'"
            wlan0_wakeup_time = "{}".format(self.get_dmesg_timestamp_with_keyword(cmd))
            self.log.info('######### wlan0_wakeup_time: {}'.format(wlan0_wakeup_time))
            timestamp_dict.update({"wlan0_wakeup_time":float(wlan0_wakeup_time)})
            # Bluetooth
            cmd = "dmesg | grep 'Bluetooth: hci_uart_register_dev'"
            bluetooth_up_time = "{}".format(self.get_dmesg_timestamp_with_keyword(cmd))
            self.log.info('######### bluetooth_up_time: {}'.format(bluetooth_up_time))
            timestamp_dict.update({"bluetooth_up_time":float(bluetooth_up_time)})
        '''
        # nf_conntrack is a process which is related to docker.
        cmd = "dmesg | grep 'nf_conntrack: default automatic helper assignment has been turned off'"
        nf_conntrack_time = "{}".format(self.get_dmesg_timestamp_with_keyword(cmd))
        self.log.info('######### nf_conntrack_time: {}'.format(nf_conntrack_time))
        timestamp_dict.update({'nf_conntrack_time':float(nf_conntrack_time)})
        '''
        BootTime_avg = 0  # initial value
        maximum_item = None
        for item in timestamp_dict:
            if timestamp_dict.get(item) > BootTime_avg:
                BootTime_avg = timestamp_dict.get(item)
                maximum_item = item
        self.log.warning("The maximum boot time is [{}]: {} seconds".format(maximum_item, BootTime_avg))
        self.data.test_result['BootTime_avg'] = BootTime_avg
        self.data.test_result['MaximumBootTimeItem'] = maximum_item
        self.data.test_result['BootTime_unit'] = 'sec'
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
            html_inst.table_title_column = ['product', 'build', 'BootTime_avg', 'BootTime_unit', 'MaximumBootTimeItem']
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'build', 'BootTime_avg', 'BootTime_unit', 'count', 'executionTime']
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

    def get_dmesg_timestamp_with_keyword(self, cmd):
        stdout, stderr = self.ssh_client.execute_cmd(cmd)
        return  stdout.split('[')[1].split(']')[0].strip()

    def get_main_volume(self):
        if self.uut.get('model') in ('rocket', 'drax'):
            cmd = 'df | grep "/Volume1" | grep -v docker'
        elif self.uut.get('model') in ('monarch2', 'pelican2', 'yodaplus2'):
            cmd = 'df | grep "/data/wd/diskVolume0" | grep -v docker'
        stdout, stderr = self.ssh_client.execute_cmd(cmd)
        main_volume = stdout.split()[0].split('/')[-1]
        self.log.warning('main_volume: {}'.format(main_volume))
        return main_volume


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Desktop_Sync_BAT on Kamino Android ***
        Examples: ./run.sh kdp_scripts/performance_tests/windows_smb_download.py  --uut_ip 192.168.0.42:8001 --cloud_env dev1 --ssh_ip 192.168.0.42 --ssh_user sshd --ssh_password 123456 --debug  --loop_times 1  --dry_run  --stream_log_level INFO  --windows_client_ip 192.168.0.33 --windows_dataset_path C:\\5G_Standard_test1 --uut_share windows_smb  -dupr
        """)
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')



    test = BootTimeKPI(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
