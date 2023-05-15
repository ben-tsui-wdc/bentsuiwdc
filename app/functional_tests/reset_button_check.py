7# -*- coding: utf-8 -*-
""" Test cases to simulate reset_button do factory action
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.constants import Kamino


class ResetButtonCheck(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Reset Button to do Factory Reset Check'
    # Popcorn
    TEST_JIRA_ID = 'KAM-29591'

    def init(self):
        self.adb.clean_logcat()
        self.timeout = 60*30
        self.model = self.uut.get('model')

    def test(self):
        self.adb.executeShellCommand('reset_button.sh short_start')
        time.sleep(30)
        self.adb.executeShellCommand('reset_button.sh middle_start')
        time.sleep(5)
        self.adb.executeShellCommand('reset_button.sh long_start')
        time.sleep(25)
        if self.model == 'yoda' or self.model == 'yodaplus':
            sys_state_log = self.adb.executeShellCommand("logcat -d | grep  'sys state change'")[0]
            check_list = ['(Reset Button Short) -> (Reset Button Middle)', '(Reset Button Middle) -> (Reset Button Long)']
            if not all(word in sys_state_log for word in check_list):
                raise self.err.TestFailure('LED state not change, failed the cases!!')
        self.log.info('Reset button press 60 secs and start to do factory reset ...')
        self.adb.executeShellCommand('busybox nohup reset_button.sh factory')

        self.log.info('Expect device do rebooting ...')
        if not self.adb.wait_for_device_to_shutdown():
            raise self.err.TestFailure('Device rebooting Failed !!')
        self.log.info('Device rebooting ...')
        if self.model == 'yodaplus' or self.model == 'yoda':
            self.serial_client.serial_wait_for_string('Hardware name: Realtek_RTD1295', timeout=60*10, raise_error=False)
            self.serial_client.wait_for_boot_complete(timeout=self.timeout)
            if self.env.ap_ssid:
                ap_ssid = self.env.ap_ssid
                ap_password = self.env.ap_password
            else:
                ap_ssid = 'private_5G'
                ap_password = 'automation'
            self.serial_client.setup_and_connect_WiFi(ssid=ap_ssid, password=ap_password, restart_wifi=True)
        else:
            time.sleep(60*3)  # For Monarch/Pelican, wait for golden mode reboot
        if not self.adb.wait_for_device_boot_completed(self.timeout):
            raise self.err.TestFailure('Device bootup Failed in {}s !!'.format(self.timeout))
        self.log.info('Device bootup completed.')
        self.check_restsdk_service()
        self.check_disk_space()
        self.check_user_root()
        time.sleep(5)

    def check_user_root(self):
        stdout, stderr = self.adb.executeShellCommand('ls -al {} | wc -l'.format(Kamino.USER_ROOT_PATH))
        stdout = stdout.strip()
        if not stdout.isdigit():
            raise self.err.TestFailure('Unknown failure when check user root.')
        if int(stdout):
            raise self.err.TestFailure('Wipe user root failed')
        self.log.info('Wipe user root completed.')

    def check_disk_space(self):
        # check userRoots is mounted
        self.timing.start()
        while not self.timing.is_timeout(60*5):
            userRootsdf = self.adb.executeShellCommand('df | grep userRoots')[0]
            userRootslog = self.adb.executeShellCommand("logcat -d -s restsdk | grep 'fuse filesystem mounted'")[0]
            if '/data/wd/diskVolume0/restsdk/userRoots' in userRootsdf and 'fuse filesystem mounted' in userRootslog:
                break
            time.sleep(2)
            if self.timing.is_timeout(60*5):
                raise self.err.TestFailure('userRoots is not mounted!!!')
        freesize = float(filter(lambda ch: ch in '0123456789.', userRootsdf.split()[3]))
        self.log.info('Free space: {}GB'.format(freesize))
        usesize = float(filter(lambda ch: ch in '0123456789.', userRootsdf.split()[2]))
        self.log.info('Use space: {}GB'.format(usesize))
        totalsize = float(filter(lambda ch: ch in '0123456789.', userRootsdf.split()[1]))
        self.log.info('Total space: {}GB'.format(totalsize))
        if usesize > totalsize*0.022:
            raise self.err.TestFailure('Disk used space is more than {}GB!!'.format(totalsize*0.022))
        elif freesize < totalsize*0.97:
            raise self.err.TestFailure('Free space is less than {}GB!!'.format(totalsize*0.097))
        else:
            self.log.info('Disk Space check passed !!')

    def check_restsdk_service(self):
        self.start = time.time()
        while not self.is_timeout(60*3):
            # Execute command to check restsdk is running
            grepRest = self.adb.executeShellCommand('ps | grep restsdk')[0]
            if 'restsdk-server' in grepRest:
                self.log.info('Restsdk-server is running\n')
                break
            time.sleep(3)
        else:
            raise self.err.TestFailure("Restsdk-server is not running after wait for 3 mins")

        # Sometimes following error occurred if making REST call immediately after restsdk is running.
        # ("stdout: curl: (7) Failed to connect to localhost port 80: Connection refused)
        # Add retry mechanism for get device info check
        self.start = time.time()
        while not self.is_timeout(60*2):
            # Execute sdk/v1/device command to check device info to confirm restsdk service running properly
            curl_localHost = self.adb.executeShellCommand('curl localhost/sdk/v1/device?pretty=true')[0]
            if 'Connection refused' in curl_localHost:
                self.log.warning('Connection refused happened, wait for 5 secs and try again...')
                time.sleep(5)
            else:
                break
        else:
            raise self.err.TestFailure("Connected to localhost failed after retry for 2 mins ...")

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Reset Button do FactoryReset Check Script ***
        Examples: ./run.sh bat_scripts/reset_button_check.py --uut_ip 10.92.224.68\
        """)

    test = ResetButtonCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
