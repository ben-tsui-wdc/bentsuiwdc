# -*- coding: utf-8 -*-
""" Test cases to check factory reset log uploaded when pip is on [KAM-26711]
"""
__author__ = "Andrew Tsai <andrew.tsai@wdc.com>"

# std modules
import sys
import time
import datetime
import os

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.serial_client import SerialClient
from platform_libraries.restAPI import RestAPI
from platform_libraries.sumologicAPI import sumologicAPI
from bat_scripts_new.factory_reset import FactoryReset


class FactoryResetLogUploadWhenPIPIsOn(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Factory Reset Log Uploaded When PIP is On'
    # Popcorn
    TEST_JIRA_ID = 'KAM-26711'

    SETTINGS = {
        'uut_owner': True
    }
    TEST_FILE = 'TEST_DB_LOCK.png'

    start = time.time()

    def declare(self):
        self.timeout = 300

    def before_test(self):
        self.environment = self.uut.get('environment')
        self.url_exist = False
        self.sumoURL = ""
        self.mac_address_hash = None
        self.jobID = ""
        self.counter = 0
        self.sumologicAPI = sumologicAPI()

        if os.path.isfile(self.TEST_FILE):
            os.remove(self.TEST_FILE)

    def test(self):
        # Skip test because dev1 environment has no hash mac address
        if self.environment == 'dev1':
            raise self.err.TestSkipped('Environment is {}, skipped the test !!'.format(self.environment))

        self.check_device_bootup()
        self.make_sure_pip_on()

        # Upload files
        self.log.info('Try to upload a new file by device owner')
        self._create_random_file(self.TEST_FILE)
        with open(self.TEST_FILE, 'rb') as f:
            self.uut_owner.chuck_upload_file(file_object=f, file_name=self.TEST_FILE)
        user_id = self.uut_owner.get_user_id(escape=True)
        if self.adb.check_file_exist_in_nas("{}".format(self.TEST_FILE), user_id):
            self.log.info('Upload test file to device successfully!')
        else:
            raise self.err.TestFailure('Upload test file to device failed!')

        # Do factory reset
        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=True']
        factory_reset = FactoryReset(env_dict)
        factory_reset.no_rest_api = False
        factory_reset.disable_ota = False
        factory_reset.test()

        # Onboarding device and turn on pip
        self.check_device_bootup()
        self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, client_settings={'config_url': self.uut['config_url']})
        self.make_sure_pip_on()

        # To reduce the waiting time of uploading log
        self.adb.executeShellCommand("move_upload_logs.sh -a")
        self.adb.executeShellCommand("move_upload_logs.sh -n")

        self.log.info("Wait 180 seconds for uploading log to sumo...")
        time.sleep(180)

        # Check factory reset log in Sumologic
        self.sumologic_check_factory_reset_log()


    def after_test(self):
        if os.path.isfile(self.TEST_FILE):
            os.remove(self.TEST_FILE)

    def check_device_bootup(self):
        # check device boot up
        while not self.is_timeout(self.timeout):
            boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed', timeout=10)[0]
            if '1' in boot_completed:
                self.log.info('Boot completed')
                break
            time.sleep(5)

    def make_sure_pip_on(self):
        # check PIP setting is on
        pipstatus = self.adb.executeShellCommand("configtool pipstatus")[0]
        if 'true' in pipstatus:
            self.log.info("PIP is %s" %pipstatus)
        else:
            self.log.info("PIP is %s, try to turn on PIP." %pipstatus)
            response = self.uut_owner.enable_pip()
            self.log.info(response)
            if response.status_code != 200:
                raise self.err.TestFailure("Failed to turn on PIP.")
            else:
                pipstatus = self.adb.executeShellCommand("configtool pipstatus")[0]
                self.log.info("Update PIP status: %s" %pipstatus)

    def _create_random_file(self, file_name, local_path='', file_size='1048576'):
        # Default 1MB dummy file
        self.log.info('Creating file: {}'.format(file_name))
        try:
            with open(os.path.join(local_path, file_name), 'wb') as f:
                f.write(os.urandom(int(file_size)))
        except Exception as e:
            self.log.error('Failed to create file: {0}, error message: {1}'.format(local_path, repr(e)))
            raise

    def sumologic_check_factory_reset_log(self):
        # check sumo url
        sumologic_upload_URL = self.adb.check_sumo_URL()
        if sumologic_upload_URL == "":
            self.log.error("sumo URL is empty, please check out your ethernet setting.")
        else:
            self.sumoURL = sumologic_upload_URL
            self.url_exist = True
            self.log.info("URL:{0}".format(self.sumoURL))

        # Get mac_address_hash of DUT
        if 'yoda' in self.uut.get('model'):
            interface = 'wlan0'
        else:
            interface = 'eth0'
        MAX_RETRIES = 3
        retry = 1
        while retry <= MAX_RETRIES:
            self.mac_address_hash = self.adb.get_hashed_mac_address(interface=interface)
            if not self.mac_address_hash:
                self.log.warning("Failed to get mac address, remaining {} retries".format(retry))
                time.sleep(10)
                retry += 1
            else:
                break
        if not self.mac_address_hash:
            raise self.err.TestError("Failed to get mac address, remaining {} retries".format(MAX_RETRIES))

        # To prepare request members for sumologic API
        sumo_des = '_sourcename={} AND {} AND crashreport'.format(self.mac_address_hash, 'factory_reset')
        self.log.info("Searching rulse: %s" %sumo_des)

        try:
            self.result = self.sumologicAPI.searchRQ(_adb_client=self.adb, searching=sumo_des, relativeTime=10, timezone="GMT")
            self.counter = int(self.result["messageCount"])
            self.log.info(self.result)
        except Exception as ex:
            self.log.error("Failed to send sumologic API: {}".format(ex))
            raise self.err.TestFailure("Test Failed related to sumologicAPI method.")

        if self.counter <= 0:
            self.log.error("Test: Failed. Cannot find the log in sumologic website.")
            raise self.err.TestFailure("Test: Failed, log file is not found in sumologic database.")
        else:
            self.log.info("Factory Reset Log Uploaded When PIP is On Test: PASSED")

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout
        
if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Factory Reset Log Uploaded When PIP is On Script ***
        Examples: ./run.sh functional_tests/factory_reset_log_upload_when_pip_on.py --cloud_env qa1 --serial_server_ip 10.0.0.6 --serial_server_port 20000\
        """)

    test = FactoryResetLogUploadWhenPIPIsOn(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
