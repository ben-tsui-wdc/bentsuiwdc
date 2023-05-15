# -*- coding: utf-8 -*-
""" Test cases to check Wi-Fi 2.4/5 GHz Read/Write test.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from kdp_scripts.bat_scripts.wifi_enable_check import WiFiEnableCheck
from platform_libraries.common_utils import execute_local_cmd
from platform_libraries.constants import KDP


class WiFiRWCheck(WiFiEnableCheck):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'Wi-Fi Read&Write Check'
    TEST_JIRA_ID = 'KDP-295,KDP-292'

    SETTINGS = {
        'uut_owner': False,
        'serial_client': True
    }

    def init(self):
        self.timeout = 60*10
        self.count = 50
        self.filename = 'test{}MB'.format(self.count)
        self.model = self.uut.get('model')
        self.remote_path = '{}/restsdk/data/mnt/'.format(KDP.DATA_VOLUME_PATH.get(self.model))

    def before_test(self):
        super(WiFiRWCheck, self).before_test()
        if not self.ssh_client.scp: self.ssh_client.scp_connect()

    def test(self):
        if not self.serial_client.verify_ssid_is_match(self.env.ap_ssid):
            super(WiFiRWCheck, self).test()
        # Generate file
        execute_local_cmd('dd if=/dev/urandom of={0} bs=1M count={1}'.format(self.filename, self.count))
        file1 = execute_local_cmd('md5sum {0}'.format(self.filename))[0]
        self.ssh_client.scp_upload(localpath=self.filename, remotepath=self.remote_path+self.filename+'_push')
        file2 = self.ssh_client.execute_cmd('md5sum {}{}'.format(self.remote_path, self.filename+'_push'))[0]
        self.ssh_client.scp_download(remotepath=self.remote_path+self.filename+'_push', localpath=self.filename+'_pull')
        file3 = execute_local_cmd('md5sum {0}'.format(self.filename+'_pull'))[0]
        if not file1.split()[0] == file2.split()[0] == file3.split()[0]:
            raise self.err.TestFailure('Push file to device, and compare failed !!')

    def after_test(self):
        # Remove files
        execute_local_cmd('rm {} {}'.format(self.filename, self.filename+'_pull'))
        self.ssh_client.execute_cmd('rm {}{}'.format(self.remote_path, self.filename+'_push'))
        self.ssh_client.scp_close()

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Wi-Fi Read/Write Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/wifi_rw_check.py --uut_ip 10.92.224.68 
                    --ap_ssid private_5G --ap_password automation --ss_ip 10.92.235.234 --ss_port 20048\
        """)

    test = WiFiRWCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
