# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings
from bat_scripts_new.reboot import Reboot


class MobileWiFiReconnect(TestCase):

    TEST_SUITE = "Mobile Testing"
    TEST_NAME = "Wi-Fi_Reconnect_Check"

    '''
        Only run for yoda/yoda+
    '''
    
    SETTINGS = {
        'uut_owner': True,
    }

    def init(self):
        self.timeout = 60*5
        self.count = 50
        self.filename = 'test{}MB'.format(self.count)
        self.remote_path = '/data/wd/diskVolume0/restsdk/data/mnt/'

    def test(self):
        self.log.info('Step 1: Rebooting the device')
        """
        self.serial_client.serial_write('busybox nohup reboot')
        self.serial_client.wait_for_boot_complete(timeout=60*10)
        if not self.adb.wait_for_device_boot_completed(max_retries=3):
            raise self.err.TestFailure('Device seems down, device boot not completed')
        
        # Todo: Using rest api will see 
        # "SSLError: [Errno 1] _ssl.c:510: error:14077410:SSL routines:SSL23_GET_SERVER_HELLO:sslv3 alert handshake failure"
        """

        env_dict = self.env.dump_to_dict()
        reboot = Reboot(env_dict)
        reboot.wait_device = True
        reboot.no_rest_api = False
        reboot.disable_ota = True
        reboot.init()
        reboot.test()

        self.log.info('Step 2: Check Wi-Fi auto reconnect and upload some files into device')
        wifi_status = self.serial_client.get_network(ssid=self.wifi_ssid)
        if not (wifi_status and '[CURRENT]' in wifi_status):
            raise self.err.TestFailure("Wi-Fi reconnect check failed! Specified Wi-Fi is not connected!")

        # Generate file
        self.adb.executeCommand('dd if=/dev/urandom of={0} bs=1M count={1}'.format(self.filename, self.count))
        file1 = self.adb.executeCommand('md5sum {0}'.format(self.filename))[0]
        self.adb.push(local=self.filename, remote=self.remote_path+self.filename+'_push', timeout=self.timeout)
        file2 = self.adb.executeShellCommand('md5sum {}{}'.format(self.remote_path, self.filename+'_push'))[0]
        self.adb.pull(remote=self.remote_path+self.filename+'_push', local=self.filename+'_pull', timeout=self.timeout)
        file3 = self.adb.executeCommand('md5sum {0}'.format(self.filename+'_pull'))[0]
        if not file1.split()[0] == file2.split()[0] == file3.split()[0]:
            raise self.err.TestFailure('Push file to device, and compare failed !!')
        
    def after_test(self):
        # Remove files
        self.adb.executeCommand('rm {} {}'.format(self.filename, self.filename+'_pull'))
        self.adb.executeShellCommand('rm {}{}'.format(self.remote_path, self.filename+'_push'))

if __name__ == '__main__':
    parser = InputArgumentParser("""
        *** Wi-Fi Reconnect Check test ***
        """)
    parser.add_argument('--wifi_ssid', help="", default='integration_2.4G')
    
    test = MobileWiFiReconnect(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)