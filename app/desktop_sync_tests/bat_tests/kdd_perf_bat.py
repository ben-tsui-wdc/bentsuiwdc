# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import ast
import os
import subprocess
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.desktop_sync import DESKTOP_SYNC
from platform_libraries.inventoryAPI import InventoryAPI, InventoryException


class KDDPerfBAT(TestCase):

    TEST_SUITE = 'kdd_perf_BAT'
    TEST_NAME = 'kdd_perf_BAT'

    def declare(self):
        self.ftp_username = 'ftp'
        self.ftp_password = 'ftppw'
        self.ftp_file_path = 'fileserver.hgst.com/temp'
        self.inventory_server_ip = None
        self.kdd_base_url = "http://repo.wdc.com/content/repositories/desktop/kamino_desktop/desktop_daemon"
        self.kdd_version_prefix = "2.1.0"
        self.kdd_build_number_url = "{}/{}/desktop_daemon-{}.txt".format(self.kdd_base_url, self.kdd_version_prefix, self.kdd_version_prefix)
        self.sin_w_list = []
        self.sin_r_list = []
        self.std_w_list = []
        self.std_r_list = []


    def init(self):
        if self.inventory_server_ip and self.inventory_server_ip != 'None':
            self.inventory = InventoryAPI('http://{}:8010/InventoryServer'.format(self.inventory_server_ip), debug=True)
            self.device_in_inventory = self._checkout_device(device_ip=self.client_ip)
            if not self.device_in_inventory:
                raise self.err.TestSkipped('There is no spare device can be checked out from Inventory Server.')

        self.uut_owner.set_global_timeout(timeout=None)  # Set the module "socket timeout" as None.
        self.share['desktop_app_obj'] = DESKTOP_SYNC(client_os=self.client_os,
                                                      client_ip=self.client_ip,
                                                      client_username=self.client_username,
                                                      client_password=self.client_password,
                                                      rest_obj=self.uut_owner,
                                                      kdd_product=self.kdd_product)
        self.kdd_obj = self.share.get("desktop_app_obj")


    def before_test(self):
        self.kdd_obj.connect()

        if not self.kdd_obj.stop_kdd_process():
            raise self.err.TestFailure('Falied to stop kdd_process.')
        if not self.kdd_obj.replace_kdd(self.build_kdd_url()):
            raise self.err.TestFailure('Failed to replace kdd.')
        if not self.kdd_obj.start_kdd_process():
            raise self.err.TestFailure('Failed to start kdd process.')
        if not self.kdd_obj.check_kdd_version(self.kdd_version):
            raise self.err.TestFailure('kdd version is wrong.')


    def test(self):
        print "# " * 30
        self.log.info("Wait 15 seconds for drive mounted after starting kdd process")
        time.sleep(15)

        for i in xrange(int(self.iteration)):
            print "\n######  start iteration {}  ######\n".format(i)
            sin_w, sin_r, std_w, std_r = self.kdd_obj.read_write_perf()
            self.sin_w_list.append(float("%.2f" % float(sin_w)))
            self.sin_r_list.append(float("%.2f" % float(sin_r)))
            self.std_w_list.append(float("%.2f" % float(std_w)))
            self.std_r_list.append(float("%.2f" % float(std_r)))
        
        self.sin_w_avg = sum(self.sin_w_list)/len(self.sin_w_list)
        self.sin_r_avg = sum(self.sin_r_list)/len(self.sin_r_list)
        self.std_w_avg = sum(self.std_w_list)/len(self.std_w_list)
        self.std_r_avg = sum(self.std_r_list)/len(self.std_r_list)


    def after_test(self):
        '''
            ### 1. Disconnect testing client ###
        '''
        self.kdd_obj.disconnect()

        '''
            ### 2. checkin_device ###
        '''
        if self.inventory_server_ip and self.inventory_server_ip != 'None':
            self._checkin_device()

        '''
            ### 3. Download the last result from file server and merge into HTML report. ###
        '''
        result = subprocess.check_output('curl http://{}/{}_kdd_kpi_result_{}'.format(self.ftp_file_path, self.kdd_product, self.client_os), shell=True)
        if "404 Not Found" in result:
            self.log.warning('curl http://{}/{}_kdd_kpi_result_{}: 404 Not Found'.format(self.ftp_file_path, self.kdd_product, self.client_os))
            kdd_version_history = None
            sin_w_history = None
            sin_r_history = None
            std_w_history = None
            std_r_history = None
        else:
            ## Get the last KPI result
            last_kpi_dict = ast.literal_eval(result.strip().split('\n')[-1])
            kdd_version_history = last_kpi_dict.get('kdd_version')
            sin_w_history = last_kpi_dict.get('sin_w_avg')
            sin_r_history = last_kpi_dict.get('sin_r_avg')
            std_w_history = last_kpi_dict.get('std_w_avg')
            std_r_history = last_kpi_dict.get('std_r_avg')

        '''
            ### 4. Generate a HTML report ###
        '''
        self.log.warning('Generate a HTML report.')
        HTML_RESULT = '<table id="report" class="basic_table">'
        HTML_RESULT += '<tr><th>Iteration</th><th>Single Read (6.46GB)</th><th>Single Write (6.46GB)</th><th>Multiple Read (5.09GB)</th><th>Multiple Write (5.09GB)</th></tr>'  # Title column
        # Different test items
        for i in xrange(len(self.sin_w_list)):
            HTML_RESULT += '<tr>'
            HTML_RESULT += "<td>{}</td><td class='pass'>{}</td><td class='pass'>{}</td><td class='pass'>{}</td><td class='pass'>{}</td>".format(i+1, self.sin_r_list[i], self.sin_w_list[i], self.std_r_list[i], self.std_w_list[i])
            HTML_RESULT += '</tr>'
        # The average
        HTML_RESULT += '<tr>'
        HTML_RESULT += "<td><b>Average</b></td><td class='pass'>{} <font color=000000>MB/s</font></td><td class='pass'>{} <font color=000000>MB/s</font></td><td class='pass'>{} <font color=000000>MB/s</font></td><td class='pass'>{} <font color=000000>MB/s</font></td>".format(self.sin_r_avg, self.sin_w_avg, self.std_r_avg, self.std_w_avg)
        HTML_RESULT += '</tr>'
        HTML_RESULT += '<tr><td><b>last KDD build: {}</b></td><td>{} MB/s</td><td>{} MB/s</td><td>{} MB/s</td><td>{} MB/s</td></tr>'.format(kdd_version_history, sin_r_history, sin_w_history, std_r_history, std_w_history) # For KPI target of the table
        # HTML_RESULT += '<tr><td><b>Target</b></td><td>50 MB/s</td><td>50 MB/s</td><td>Not defined</td><td>Not defined</td></tr>' # For KPI target of the table
        HTML_RESULT += '</table>'  # table finished

        MTBF_RESULT_jenkins_property = "kdd_perf_html_result={}\n".format(HTML_RESULT)
        try:
            with open('/root/app/output/kdd_perf_html_result', 'w') as f:
                f.write(MTBF_RESULT_jenkins_property)
        except:
            with open('kdd_perf_html_result', 'w') as f:
                f.write(MTBF_RESULT_jenkins_property)

        '''
            ### 5. Upload the latest result to file server  ###
        '''
        kpi_result = {}
        kpi_result['kdd_product'] = self.kdd_product
        kpi_result['kdd_version'] = self.kdd_version
        kpi_result['sin_w_avg'] = self.sin_w_avg 
        kpi_result['sin_r_avg'] = self.sin_r_avg
        kpi_result['std_w_avg'] = self.std_w_avg
        kpi_result['std_r_avg'] = self.std_r_avg
        with open('{}_kdd_kpi_result_{}'.format(self.kdd_product, self.client_os), 'w') as f:
            f.write('{}\n'.format(str(kpi_result)))
        print '\ncurl -u {}:{} -T {}_kdd_kpi_result_{} ftp://{}/\n'.format(self.ftp_username, self.ftp_password, self.kdd_product, self.client_os, self.ftp_file_path)
        try:
            subprocess.check_output('curl -u {}:{} -T {}_kdd_kpi_result_{} ftp://{}/'.format(self.ftp_username, self.ftp_password, self.kdd_product, self.client_os, self.ftp_file_path), shell=True)
        except Exception as e:
            self.log.warning('{}'.format(e))


    def build_kdd_url(self):
        # To acquire the latest kdd_build_version
        if not self.kdd_version:
            stdout, stderr = self.adb.executeCommand(cmd='curl -s {}'.format(self.kdd_build_number_url))
            self.kdd_version = "{}-{}".format(self.kdd_version_prefix, stdout).strip()

        if self.kdd_product == 'WD':
            project_name="Kamino"
            if self.client_os == 'MAC':
                os_product_folder="darwinwd"
            elif self.client_os == 'WIN':
                os_product_folder="windowswdx64"
            kdd_executable="kdd"
            app_name="WDDesktop"
        elif self.kdd_product == 'ibi':
            project_name='ibi'
            if self.client_os == 'MAC':
                os_product_folder="darwinibi"
            elif self.client_os == 'WIN':
                os_product_folder="windowsibix64"
            kdd_executable="ibikdd"
            app_name="ibiDesktop"
        
        kdd_url="{}/{}/{}/{}".format(self.kdd_base_url, self.kdd_version, os_product_folder, kdd_executable)
        print "# " * 20
        print "kdd_url:    {}".format(kdd_url)
        print "# " * 20
        return kdd_url


    def _checkout_device(self, device_ip=None, uut_platform=None, firmware=None):
        jenkins_job = '{0}-{1}-{2}'.format(os.getenv('JOB_NAME', ''), os.getenv('BUILD_NUMBER', ''), self.__class__.__name__) # Values auto set by jenkins.
        if device_ip: # Device IP has first priority to use.
            self.log.info('Check out a device with IP: {}.'.format(device_ip))
            device = self.inventory.device.get_device_by_ip(device_ip)
            if not device:
                raise self.err.StopTest('Failed to find out the device with specified IP({}).'.format(device_ip))
            checkout_device = self.inventory.device.check_out(device['id'], jenkins_job, force=False)
        elif uut_platform: # Find device with matching below conditions.
            self.log.info('Looking for a available device.')
            checkout_device = self.inventory.device.matching_check_out_retry(
                uut_platform, tag='', firmware=firmware, variant='', environment='', uboot='',
                location='', site='', jenkins_job=jenkins_job, retry_counts=24,
                retry_delay=300, force=False
            )
            # retry_delay 180 seconds, retry_count 120 times.
        else:
            raise self.err.StopTest('Device Platform or Device IP is required.')
        return checkout_device


    def _checkin_device(self):
        if not self.inventory.device.check_in(self.device_in_inventory['device']['id'], is_operational=True):
            raise self.err.StopTest('Failed to check in the device.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Desktop_Sync_BAT on Kamino Android ***
        Examples: ./run.sh desktop_sync_tests/integration_tests/kdd_perf_bat.py\
                  --uut_ip 10.136.137.159 --username kdd_perf_bat@test.com \
                  --client_os "MAC" --client_ip 10.92.234.61 --client_username "user" --client_password "pass"\
                  --app_version 1.1.0.14 --dry_run
        """)
    #parser.add_argument('--inventory_server_ip', help='inventory_server_ip', default='sevtw-inventory-server.hgst.com')
    parser.add_argument('--inventory_server_ip', help='inventory_server_ip', default=None)
    parser.add_argument('--kdd_product', help='kdd_product, ibi or WD', default='ibi', choices=['ibi', 'WD'])
    parser.add_argument('--kdd_version', help='Desktop KDD version', default='')
    parser.add_argument('--client_os', help='Client OS type', default='MAC', choices=['WIN', 'MAC'])
    parser.add_argument('--client_ip', help='Client OS ip address', default=None)
    parser.add_argument('--client_username', help='Username to login client OS', default='root')  # for MAC
    parser.add_argument('--client_password', help='The password os client user', default="`1q")  # for MAC
    parser.add_argument('--windows_drive_letter', help='The location of dataset, by default is C', default='C')
    parser.add_argument('--windows_mount_point', help='Windows mount point of NAS share, by default is Z', default='Z')
    parser.add_argument('--file_server_ip', help='File server IP Address', default='fileserver.hgst.com')
    parser.add_argument('--iteration', help='number of iteration', default="5")

    test = KDDPerfBAT(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
