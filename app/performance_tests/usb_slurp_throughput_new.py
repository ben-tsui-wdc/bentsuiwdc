# -*- coding: utf-8 -*-
""" kpi test for usb slurp throughput.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.restAPI import RestAPI
from bat_scripts_new.factory_reset import FactoryReset
from bat_scripts_new.reboot import Reboot


class usb_slurp_throughput(TestCase):
    TEST_SUITE = 'Performance_Tests'
    TEST_NAME = 'kpi_usb_slurp_throughput'
    # Popcorn
    TEST_JIRA_ID = 'KAM-13280'

    SETTINGS = {'uut_owner' : False # Disbale restAPI.
    }

    # Pre-defined parameters for IntegrationTest
    def declare(self):
        self.folder_name = None
        self.wifi_mode = 'None'
        self.timeout = 7200
        self.no_factory_reset = False

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
        stdout, stderr = self.adb.executeShellCommand('df | grep /mnt/media_rw/')
        if stdout:
            pass
        else:
            self.log.warning("USB drive is not mounted on /mnt/media_rw/.")
            return False
        stdout, stderr = self.adb.executeShellCommand('ls /dev/block/vold | grep public')
        if stdout:
            usb_location = '/dev/block/vold/{}'.format(stdout.strip())
            self.log.info("usb_location_on_platform: {}".format(usb_location))
        else:
            self.log.warning("There is no USB drive on dev/block/vold.")
            return False
        return True


    def before_test(self):
        if self.no_factory_reset:
            self.log.info('###### no factory_reset ######')
            pass
        else:
            env_dict = self.env.dump_to_dict()
            env_dict['Settings'] = ['uut_owner=False']
            self.log.info('start factory_reset')
            factory_reset = FactoryReset(env_dict)
            factory_reset.no_rest_api = True
            factory_reset.test()
            self.adb.stop_otaclient()
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
        # Trigger usb slurp
        try:
            copy_id, usb_info, result = self.uut_owner.usb_slurp(usb_name=None, folder_name=self.folder_name, timeout=self.timeout, wait_until_done=True)

        except Exception as ex:
            raise self.err.TestError('trigger_usb_slurp Failed!! Err: {}'.format(ex))

        usb_slurp_elapsed_time = result['elapsedDuration']
        usb_slurp_total_byte = result['totalBytes']
        usb_slurp_total_size = int(usb_slurp_total_byte)/1024/1024
        usb_slurp_avg = usb_slurp_total_size/usb_slurp_elapsed_time

        self.data.test_result['data_type'] = self.folder_name
        self.data.test_result['wifi_mode'] = self.wifi_mode
        self.data.test_result['usb_slurp_total_size'] = usb_slurp_total_size
        self.data.test_result['usb_slurp_elapsed_time'] = usb_slurp_elapsed_time
        self.data.test_result['usb_slurp_avg'] = usb_slurp_avg


if __name__ == '__main__':

    parser = InputArgumentParser("""\
        *** time_machine_throughput test on Kamino Android ***
        Examples: ./run.sh performance_tests/usb_slurp_throughput_new.py --uut_ip 10.92.224.13 \
        --cloud_env qa1 --data_type single --loop_times 3 --debug_middleware --dry_run\
        (optional)--serial_server_ip fileserver.hgst.com --serial_server_port 20015
        """)
    parser.add_argument('--wifi_mode', help='type of wifi mode, by default is None', choices=['None','2.4G', '5G'], default='None')
    parser.add_argument('--folder_name', help='specify the folder_name which is usb slurped.', default=None)
    parser.add_argument('--timeout', help='specify the timeout of usb slurp.', default=7200)
    parser.add_argument('--no_factory_reset', help='Don\'t execute factory_reset.', action='store_true')


    test = usb_slurp_throughput(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)