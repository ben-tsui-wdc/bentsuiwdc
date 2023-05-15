# -*- coding: utf-8 -*-
""" Test cases to check Wi-Fi 2.4/5 GHz Read/Write test.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from bat_scripts_new.wifi_enable_check import WiFiEnableCheck


class WiFiRWCheck(WiFiEnableCheck):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Wi-Fi Read&Write Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-23760,KAM-23761'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.timeout = 60*10
        self.count = 50
        self.filename = 'test{}MB'.format(self.count)
        self.remote_path = '/data/wd/diskVolume0/restsdk/data/mnt/'
        super(WiFiRWCheck, self).init()

    def test(self):
        model = self.uut.get('model')
        if model == 'monarch' or model == 'pelican':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(model))
        wifi_status  = self.serial_client.get_network(ssid=self.env.ap_ssid)
        if not (wifi_status and '[CURRENT]' in wifi_status):
            super(WiFiRWCheck, self).test()
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
    parser = InputArgumentParser("""\
        *** Wi-Fi Read/Write Check Script ***
        Examples: ./run.sh bat_scripts_new/wifi_rw_check.py --uut_ip 10.92.224.68 --ap_ssid private_5G\
        """)

    test = WiFiRWCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
