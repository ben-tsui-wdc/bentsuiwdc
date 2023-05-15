# -*- coding: utf-8 -*-
""" kpi test for usb import throughput.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import numpy
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.restAPI import RestAPI
from bat_scripts_new.factory_reset import FactoryReset
from ibi_performance.tool.html import HtmlFormat

class usb_slurp_throughput(TestCase):
    TEST_SUITE = 'Performance_Tests'
    TEST_NAME = 'kpi_usb_slurp_throughput'
    SETTINGS = {
        'uut_owner': False, # Disbale restAPI.
        'adb': False,
        'power_switch': False,
    }

    # Pre-defined parameters for IntegrationTest
    def declare(self):
        self.usb_slurp_type = None      
        self.folder_name = None
        self.timeout = 28800
        self.no_factory_reset = False
        self.environment_elapsed_time = 7200
        self.environment_usb_slurp_avg = 20
        self.test_result_list = []
        self.clear_data_after_test = False
        self.StopTest_flag = False
        self.html_format = 1


    def before_loop(self):
        if not self.usb_slurp_type:
            raise self.err.StopTest("Please sepcify usb_slurp_type & device mac address.")

        '''
            Get self.uut_owner.url_prefix
        '''
        self.uut['mac_address'] = self.mac_address
        self.uut_owner = RestAPI(uut_ip=None, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
        
        self.uut_owner.environment.update_service_urls()

        temp =  self.uut_owner.get_devices_info_per_specific_user()        
        if temp:
            for i in temp:
                if i.get("mac") == self.uut.get('mac_address').lower():
                    print i
                    self.uut['firmware'] = i.get('firmware').get('wiri')
                    self.uut['model'] = i.get('type')
                    self.uut['environment'] = self.env.cloud_env
                    self.proxy_url = i.get('network').get('proxyURL') 
                    self.port_forward_url = i.get('network').get('portForwardURL')
                    print "\n"
                    print 'firmware: {}'.format(self.uut['firmware'])
                    print 'model: {}'.format(self.uut['model'])
                    print 'mac_address: {}'.format(i.get("mac"))
                    print 'proxyURL: {}'.format(i.get('network').get('proxyURL'))
                    print 'portForwardURL: {}'.format(i.get('network').get('portForwardURL'))
                    print "\n"
                    break
            self.uut_owner.url_prefix = self.proxy_url  ######## Important
        else:
            pass  # Need to do error handle
        
        # Get usb_info
        self.usb_info = self.uut_owner.get_usb_info()

        # This a workaround for https://jira.wdmv.wdc.com/browse/IBIX-1392
        if not self.usb_info:
            self.log.warning('Start to use REST API to reboot device because USB storage is not found.')
            try:
                self.uut_owner.reboot_device()
                self.log.info('Device rebooting..')
                self.log.info('Wait 360 seconds for device rebooting')
                time.sleep(360)
            except:
                raise self.err.StopTest('Reboot device via restapi failed!!')

        # Get usb_info again
        self.usb_info = self.uut_owner.get_usb_info()

        print "usb_info['name']: {}".format(self.usb_info['name'])
        print "usb_info['id']: {}".format(self.usb_info['id'])


    def before_test(self):
        '''
            # Delete the folder which is already slurped into device.
        '''
        if self.usb_slurp_type == 'from_drive':  # Data slurp is from usb drive to target device
            # Delete the dataset in target device.
            for element in [self.usb_info['name'], self.folder_name]:
                data_id_dict = None
                try:
                    data_id_dict, page_token = self.uut_owner.get_data_id_list(type='folder', parent_id='root')
                except Exception as e:  # The folder may be already deleted.
                    print e
                if data_id_dict:
                    data_id = data_id_dict.get(element, None)
                    if data_id:
                        self.uut_owner.delete_file(data_id)
        elif self.usb_slurp_type == 'to_drive':  # Data slurp is from target device to usb drive
            # Check if there is dataset in target device. If so, continue test. If not, skip whole test.
          
            data_id_dict = None
            try:
                data_id_dict, page_token = self.uut_owner.get_data_id_list(type='folder', parent_id='root')
            except:  # The folder may be already deleted.
                pass
            if data_id_dict and data_id_dict.get(self.folder_name, None):
                pass                
            else:
                self.StopTest_flag = True
                raise self.err.StopTest('There is no dataset in target device.')

            # Delete the dataset in USB drive.
            retry_number = 5
            for i in xrange(retry_number):
                try:
                    # Get usb_path
                    self.serial_client.serial_write('usbpath=usbpathis`df | grep /mnt/media_rw` && echo $usbpath')
                    self.serial_client.serial_wait_for_string('usbpathis', timeout=360)
                    stdout = self.serial_client.serial_filter_read('/mnt/media_rw')
                    print '11111' * 30
                    usb_path = stdout[0].split('usbpathis')[1].split()[0]
                    print 'usb_path: {}'.format(usb_path)
                    print '11111' * 30
                    # remount usb_path
                    self.serial_client.serial_write('mount -o remount,rw {} && echo FINISHED'.format(usb_path))
                    self.serial_client.serial_wait_for_string('FINISHED', timeout=360)
                    # rm -fr self.folder_name
                    self.serial_client.serial_write('rm -fr {}/{} && echo FINISHED'.format(usb_path, self.folder_name))
                    self.serial_client.serial_wait_for_string('FINISHED', timeout=360)
                    print "time.sleep(30) after 'rm -fr {}/{} in USB drive'".format(usb_path, self.folder_name)
                    time.sleep(30)
                    break
                    # reboot device
                    #self.serial_client.serial_write('busybox nohup reboot')
                    #self.serial_client.wait_for_boot_complete(timeout=300)
                    #print "time.sleep(30) after rebooting device"
                    #time.sleep(30)
                except Exception as e:
                    print '@ # $ ' * 20
                    print 'There is a exception occurred. retry: {}'.format(i)
                    print e
                    print '@ # $ ' * 20
                    if i == retry_number - 1:
                        raise


    # main function
    def test(self):
        # Trigger usb import
        try:
            if self.usb_slurp_type == 'from_drive':
                copy_id, usb_info, result = self.uut_owner.usb_slurp(usb_name=None, folder_name=self.folder_name, dest_parent_id='root', timeout=self.timeout, wait_until_done=True)
            elif self.usb_slurp_type == 'to_drive':
                copy_id, usb_info, result = self.uut_owner.usb_export(usb_name=None, folder_name=self.folder_name, timeout=self.timeout, wait_until_done=True)
        except Exception as ex:
            raise self.err.TestError('trigger_usb_import({}) Failed!! Err: {}'.format(self.usb_slurp_type, ex))

        usb_import_elapsed_time = result['elapsedDuration']
        usb_import_total_byte = result['totalBytes']
        usb_import_total_size = int(usb_import_total_byte)/1024/1024
        usb_import_avg = usb_import_total_size/usb_import_elapsed_time
        self.data.test_result['data_type'] = self.folder_name
        self.data.test_result['SlurpType'] = self.usb_slurp_type
        self.data.test_result['DeviceSz'] = self.device_size()
        self.data.test_result['ErrCnt'] = result['errorCount']
        self.data.test_result['FileNum'] = result['copiedCount']
        self.data.test_result['FileSz'] = '{0:.2f}'.format(usb_import_total_size)
        self.data.test_result['ElapsT'] = '{0:.2f}'.format(usb_import_elapsed_time)
        self.data.test_result['AvgSpd'] = '{0:.2f}'.format(usb_import_avg)
        self.data.test_result['EnvElapsT'] = int(self.environment_elapsed_time)
        self.data.test_result['EnvAvgSpd'] = int(self.environment_usb_slurp_avg)
        

    def device_size(self):
        resp = self.uut_owner.get_device()
        if resp.status_code == 200:
            temp = resp.json().get('storage').get('capacity')  #temp is device_size in bytes.
            return '{0:.0f}'.format(float(temp)/1000000000000)
        else:
            return None


    def after_test(self):
        # Append every test result of iteration
        self.test_result_list.append(self.data.test_result)

        if self.clear_data_after_test:
            '''
                # Delete the folder which is already slurped into target device.
            '''
            if self.usb_slurp_type == 'from_drive':
                for element in [self.usb_info['name'], self.folder_name]:
                    data_id_dict = None
                    try:
                        data_id_dict, page_token = self.uut_owner.get_data_id_list(type='folder', parent_id='root')
                    except Exception as e:  # The folder may be already deleted.
                        print e
                    if data_id_dict:
                        data_id = data_id_dict.get(element, None)
                        if data_id:
                            self.uut_owner.delete_file(data_id)
            elif self.usb_slurp_type == 'to_drive':
                pass


    def after_loop(self):
        if self.StopTest_flag:
            return

        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '1':
            html_inst.table_title_column = ['product', 'build', 'DeviceSz', 'SlurpType', 'FileNum', 'FileSz', 'iteration', 'ErrCnt', 'EnvElapsT', 'ElapsT', 'EnvAvgSpd', 'AvgSpd',]
            html_inst.table_title_column_extend = ['AvgSpd']
        elif self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'iteration', 'SlurpType', 'ErrCnt', 'EnvAvgSpd', 'AvgSpd',]
            html_inst.table_title_column_extend = ['result']
        html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)


if __name__ == '__main__':

    parser = InputArgumentParser("""\
        *** USB slurp test on Kamino Android ***
        Examples: ./run.sh performance_tests/usb_slurp_throughput.py --uut_ip 10.92.224.13 \
        --cloud_env qa1 --data_type single --loop_times 3 --debug_middleware --dry_run\
        (optional)--serial_server_ip fileserver.hgst.com --serial_server_port 20015
        """)
    # Note that SERIAL CLIENT is necessary if usb_slurp_type == 'to_drive' 
    parser.add_argument('--usb_slurp_type', help='from_drive/to_drive', default=None)
    parser.add_argument('--mac_address', help='specify which device to be tested', default=None)
    parser.add_argument('--folder_name', help='specify the folder_name which is usb imported.', default=None)
    parser.add_argument('--timeout', help='specify the timeout of usb import.', default=28800)
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--no_factory_reset', help='Don\'t execute factory_reset.', action='store_true')
    parser.add_argument('--environment_elapsed_time', help='environment_elapsed_time', default='7200')
    parser.add_argument('--environment_usb_slurp_avg', help='environment_usb_slurp_avg', default='20')
    parser.add_argument('--clear_data_after_test', help='clear dataset after test finished', action='store_true')
    parser.add_argument('--html_format', help='the html format for test result', default='1', choices=['1', '2'])

    test = usb_slurp_throughput(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)