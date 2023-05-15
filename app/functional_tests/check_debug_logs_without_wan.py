# -*- coding: utf-8 -*-
""" Test cases to check debug logs [KAM-22184] #TODO: Need modify script, pass criteria is not correct.
"""
__author__ = "Vodka Chen <vodka.chen@wdc.com>"

# std modules
import sys
import urllib2
import os
import shutil
import tarfile
import stat
import time

# platform modules
from middleware.arguments import InputArgumentParser
from platform_libraries.serial_client import SerialClient
from wifi.ap_connect import APConnect
from platform_libraries.pyutils import retry

class CheckDebugLogsWithoutWan(APConnect):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Check debug logs'
    # Popcorn
    TEST_JIRA_ID = 'KAM-22184'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.serialVerify = False
        self.downloadURL = "http://" + self.env.uut_ip + ":33284/cgi-bin/logs.sh"
        self.downloadDir = os.getcwd() + "/debug_log"
        self.downloadFile = self.downloadDir + "/debug_logs.tar.gz"
        self.dirList = ['crash', 'dmesg', 'kernel', 'main', 'plex', 'system', 'wd']
        self.logDir = '/data/wd/diskVolume0/debug_logs'
        #Set first network , second network environment
        self.ddwrt_ssid = self.test_2_4G_ssid
        self.ddwrt_ssid_pw = self.test_2_4G_password
        self.check_wifi_status = True

    def before_test(self):
        if os.path.exists(self.downloadDir):
            shutil.rmtree(self.downloadDir)
        self.log.info('Check Debug Logs: Clear download folder')

        #Check 2.4G or 5G ap device
        self._disable_wan = False # Flag to record wan status.
        self.log.info('{0}: Check {1} AP device'.format(self.TEST_NAME, self.ddwrt_ssid))
        self.check_wifi_AP(timeout=300, filter_keyword=self.ddwrt_ssid)

    def test(self):
        #Connect to DD-WRT ssid
        self.serial_client.setup_and_connect_WiFi(ssid=self.ddwrt_ssid, password=self.ddwrt_ssid_pw, restart_wifi=True)
        #Check connection status
        wifi_list_1 = self.serial_client.list_network(filter_keyword=self.ddwrt_ssid)
        if not wifi_list_1:
            self.log.error('{0}: Connect to {1} AP fail !!'.format(self.TEST_NAME, self.ddwrt_ssid))
            raise self.err.TestFailure('{0}: Connect to First AP fail'.format(self.TEST_NAME))
        self.log.info('{0}: Network Settings => {1}'.format(self.TEST_NAME, self.serial_client.list_network()))

        #Disable WAN
        self.reset_logcat_start_line()
        self.log.info('{0}: Disable AP WAN'.format(self.TEST_NAME))
        self.log.info('{0}: WAN is shared on br0'.format(self.TEST_NAME))
        self._disable_wan = True
        self.ap.disable_network_interface('br0')

        self.log.info('{0}: Test device disconnect from Wi-Fi'.format(self.TEST_NAME))
        self.log.info('{0}: Here we use devcice shutdown check as Wi-Fi disconnect check...'.format(self.TEST_NAME))
        if not self.adb.wait_for_device_to_shutdown():
            raise self.err.TestFailure('AP Wi-Fi disable failed')

        if self.check_wifi_status: # Logcat logs may missing.
            self.log.test_step('Check system log: "Wifi Disconnected"')
            retry( # Retry 30 mins.
                func=self.check_serial_wifi, wifi_status='Wifi Disconnected',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )

        self.log.info(self.downloadURL)
        if not os.path.exists(self.downloadDir):
            os.makedirs(self.downloadDir)
        #Download log file
        try:
            response = urllib2.urlopen(self.downloadURL)
            fh = open(self.downloadFile, "w")
            fh.write(response.read())
            fh.close()
        except urllib2.URLError as e:
            self.log.error('Check Debug Logs: Download log file (debug_logs.tar.gz) fail')
            self.log.error(e)
            # Verify folder tree by using serial console
            if self.send_serial_verify():
                self.serialVerify = True
            else:
                raise self.err.TestFailure('Check Debug Logs: Download log Failed')

        # If download successfully, run below procedure
        # If download fail, and verify folder tree by using serial console. Skip below procedure
        if not self.serialVerify:
            if os.path.isfile(self.downloadFile):
                try:
                    tar = tarfile.open(self.downloadFile)
                    tar.extractall(path=self.downloadDir)
                    tar.close()
                except:
                    self.log.error('Check Debug Logs: Decompress log file (debug_logs.tar.gz) fail')
                    raise self.err.TestFailure('Check Debug Logs: Decompress log file Failed')
            else:
                self.log.error('Check Debug Logs: log file (debug_logs.tar.gz) missing')
                raise self.err.TestFailure('Check Debug Logs: log file missing')

            #Check log directory content
            saveList = []
            saveFiles = []

            for root, dirs, files in os.walk(self.downloadDir + "/debug_logs", topdown=False):
                for name in dirs:
                    saveList.append(name)
                for name in files:
                    saveFiles.append(os.path.join(root, name))

            if set(self.dirList) == set(saveList):
                self.log.info('Current log directory list: ')
                self.log.info(saveList)
            else:
                self.log.error('Check Debug Logs: Log directory missing. ')
                self.log.error(self.dirList)
                self.log.error(saveList)
                raise self.err.TestFailure('Check Debug Logs: Log directory missing.')

            #Check log file permission
            for logfile in saveFiles:
                mode = os.lstat(logfile)[stat.ST_MODE]
                self.log.info(logfile)
                if not mode & stat.S_IROTH:
                    self.log.error('Check Debug Logs: log file permission error')
                    self.log.error(logfile)
                    raise self.err.TestFailure('Check Debug Logs: log file permission error')

        self.log.info('{0}: Enable AP WAN'.format(self.TEST_NAME))
        self.log.info('{0}: WAN is shared on br0'.format(self.TEST_NAME))
        self.ap.enable_network_interface('br0')
        self._disable_wan = False

        self.log.info('{0}: Test device connect to Wi-Fi'.format(self.TEST_NAME))
        self.adb.disconnect()
        self.serial_client.restart_adbd()
        self.adb.connect(timeout=60*5)

        if self.check_wifi_status: # Logcat logs may missing.
            self.log.info('{0}: Check system log: "Wifi Connected"'.format(self.TEST_NAME))
            retry( # Retry 30 mins.
                func=self.check_wifi, wifi_status='Wifi Connected',
                excepts=(Exception), retry_lambda=lambda ret: not ret, delay=10, max_retry=30*6, log=self.log.warning
            )

    def after_test(self):
        if os.path.exists(self.downloadDir):
            shutil.rmtree(self.downloadDir)
        self.log.info('Check Debug Logs: Clear download folder')
        #Check wan status
        if self._disable_wan:
            self.ap.enable_network_interface('br0')
            self._disable_wan = False
        #Recover network to original
        self.serial_client.setup_and_connect_WiFi(ssid=self.env.ap_ssid, password=self.env.ap_password, restart_wifi=True)

    def send_serial_verify(self):
        DirSaveList = []
        DirFilterData = []
        DirSaveList = self.serial_client.serial_cmd(cmd='find %s -maxdepth 1 -mindepth 1 -type d -exec realpath {} \;' %self.logDir, \
                                                    timeout=60*5, wait_response=True, return_type='list')
        self.log.info('{0}: Original directory list: {1}'.format(self.TEST_NAME, DirSaveList))

        for content in DirSaveList:
            if content.startswith(self.logDir):
                DirFilterData.append(os.path.basename(content))

        if set(self.dirList) == set(DirFilterData):
            self.log.info('{0}: Current log directory list: {1}'.format(self.TEST_NAME, DirFilterData))
            return True
        else:
            self.log.info('{0}: Current log directory different list: {1}'.format(self.TEST_NAME, DirFilterData))
            return False

    def check_wifi_AP(self, timeout, filter_keyword=None):
        start = time.time()
        self.serial_client.scan_wifi_ap()
        wifi_scan = self.serial_client.list_wifi_ap(filter_keyword)
        while not wifi_scan:
            if time.time() - start > timeout:
                raise self.err.TestFailure('{0}: Wi-Fi {1} AP is not ready, Skipped the test'.format(self.TEST_NAME, filter_keyword))
            self.serial_client.scan_wifi_ap()
            wifi_scan = self.serial_client.list_wifi_ap(filter_keyword)
            time.sleep(1)

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Check debug logs Script ***
        Examples: ./run.sh functional_tests/check_debug_log.py --uut_ip 10.92.224.68 \
        """)
    # Test Arguments
    parser.add_argument('--ap_power_port', help='AP port on power switch', metavar='PORT', type=int, default=1)
    parser.add_argument('--test_2_4G_ssid', help='AP SSID for 2.4G test', metavar='SSID', default='A1-2.4G-dd-wrt')
    parser.add_argument('--test_2_4G_password', help='AP password for 2.4G test', metavar='PWD', default='1qaz2wsx')
    parser.add_argument('--test_2_4G_security_mode', help='Security mode for 2.4G test', metavar='MODE', default='psk2')

    test = CheckDebugLogsWithoutWan(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
