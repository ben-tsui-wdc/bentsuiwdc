""" Log upload when PIP is enabled (KAM-17894).
"""
__author__ = "Philip Yang <Philip.Yang@wdc.com>"

# std modules
import sys
import time
import datetime
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.sumologicAPI import sumologicAPI


class LogUploaderTest(TestCase):

    TEST_SUITE = 'LogUploader Tests'
    TEST_NAME = 'Check Log Upload behavior'
    # Popcorn
    TEST_JIRA_ID = 'KAM-17894'

    SETTINGS = {
        'uut_owner': True
    }

    def init(self):
        self.pip = True
        self.url_exist = False
        self.holding = True
        self.sumoURL = ""
        self.logname = ""
        self.jobID = ""
        self.counter = 0
        self.sumologicAPI = sumologicAPI()


    def before_test(self):
        # Skip test because dev1 environment has no hash mac address
        if self.uut.get('environment') == 'dev1':
            raise self.err.TestSkipped('Environment is {}, skipped the test !!'.format(self.uut.get('environment')))


    def test(self):
        # check sumo url
        sumologic_upload_URL = self.adb.check_sumo_URL()
        if sumologic_upload_URL == "":
            self.log.error("sumo URL is empty, please check out your ethernet setting.")
            raise self.err.TestFailure("Failed. Because sumo URL is empty.")
        else:
            self.sumoURL = sumologic_upload_URL
            self.url_exist = True
            self.log.info("URL:{0}".format(self.sumoURL))
        # check PIP setting
        pipstatus = self.adb.get_pipstatus()
        if pipstatus == "true":
            self.log.info("PIP is %s" %pipstatus)
            self.pip = True
        else:
            self.log.info("PIP is %s, try to turn on PIP." %pipstatus)
            response = self.uut_owner.enable_pip()
            self.log.info(response)
            if response.status_code != 200:
                self.pip = False
                raise self.err.TestFailure("Failed to turn on PIP.")
            else:
                pipstatus = self.adb.get_pipstatus()
                self.log.info("Update PIP status: %s" %pipstatus)
                self.pip = True
        # parse LogUploader in logcat
        while self.holding:
            stdout, stderr = self.adb.executeShellCommand(cmd=" logcat -d | grep -E 'LogUploader | move_upload_log' ")
            if not stdout:
                self.log.info("Empty, try again after 300sec.")
                time.sleep(300)
                self.counter+=1
                self.log.info("Counter: %d" %self.counter)
            elif self.counter >5:
                raise self.err.TestFailure("Test failed because log moving is not detected.")
            else:
                self.holding = False

        # Do reboot and waiting log upload to SumoLogic
        self.adb.reboot_device_and_wait_boot_up()

        # Get hashed mac address
        if 'yoda' in self.uut.get('model'):
            interface = 'wlan0'
        else:
            interface = 'eth0'
        if self.pip and self.url_exist:
            try:
                MAX_RETRIES = 5
                retry = 1
                while retry <= MAX_RETRIES:
                    self.logname = self.adb.get_hashed_mac_address(interface=interface)
                    if not self.logname:
                        self.log.warning("Failed to get mac address, remaining {} retries".format(retry))
                        time.sleep(10)
                        retry += 1
                    else:
                        break

                self.log.info("Hashed mac address: %s" %self.logname)
            except:
                raise self.err.TestFailure("Test failed: cause we cannot parser hashed mac address to search log.")
        else:
            self.log.error("Failed to get hashed mac address.")
            raise self.err.TestFailure("Test failed cause Test Condition does not match.")
        # To prepare request members for sumologic API
        sumo_des = "_sourceCategory=qa1/device/%s/LogUploader AND _sourceName=%s" % (self.uut.get('model'), self.logname)
        self.log.info("Searching rulse: %s" %sumo_des)

        try:
            self.result = self.sumologicAPI.searchRQ(_adb_client=self.adb, searching=sumo_des, relativeTime=10, timezone="GMT")
            self.counter = int(self.result["messageCount"])
            self.log.info(self.result)
        except Exception as ex:
            self.log.error("Failed to send sumologic API: {}".format(ex))
            raise self.err.TestFailure("Test failed related to sumologicAPI method.")

        if self.counter <= 0:
            self.log.error("Test: Failed. Cannot find the log in sumologic website.")
            raise self.err.TestFailure("Test: Failed, log file is not found in sumologic database.")
        else:
            self.log.info("Test: pass")

    def after_test(self):
        '''
        Clean test enviroment
        '''

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Log Upload test on Kamino Android ***
        Examples: ./run.sh ...  --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-wait', '--wait_device', help='Wait for device boot completede', action='store_true')

    test = LogUploaderTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
