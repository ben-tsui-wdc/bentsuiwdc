___author___ = 'Vance Lo <vance.lo@wdc.com>'

import sys
import os
import argparse
import time

from junit_xml import TestSuite
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries import common_utils

from loadRestsdkmodule import loadRestsdkmodule
from checkCloudServices import checkCloudServices
from network_adb_connect import network_adb_Connect
from sambaEnabledCheck import sambaEnabledCheck
from loadAvahiNetatalkCheck import loadAvahiNetatalkCheck
from loadAfpCheck import loadAfpCheck
from loadAppManager import loadAppManager
from loadOtaClient import loadOtaClient
from checkUserRootsMountOnDevice import checkUserRootsMountOnDevice
from createUserAttachUserCheck import createUserAttachUser
from sambaRW import sambaRW
from fwUpdateUtility import fwUpdateUtility
from checkRaidAutoMount import checkRaidAutoMount
from usbAutoMount import usbAutoMount
from usbSlurpBackupFile import usbSlurpBackupTest
from usbSlurpDeleteFile import usbSlurpDeleteTest
from basicTranscoding import basicTranscoding
from cloudEnvironmentCheck import cloudEnvironmentCheck
from factoryReset import factoryReset
from rebootTest import rebootTest
from dataLossCheck import dataLossCheck

class bat_run(object):
    def __init__(self, adb=None):
        self.adb = adb
        self.log = common_utils.create_logger(root_log='BAT')
        self.adb.connect()
        time.sleep(3)

    def run(self, single=None, env=None):
        if not single:
            # version = self.adb.getFirmwareVersion().split()[0]
            testlist = [
                rebootTest,
                loadRestsdkmodule,
                network_adb_Connect,
                cloudEnvironmentCheck,
                loadAppManager,
                loadAvahiNetatalkCheck,
                loadAfpCheck,
                loadOtaClient,
                checkUserRootsMountOnDevice,
                checkCloudServices,
                createUserAttachUser,
                basicTranscoding,
                usbAutoMount,
                usbSlurpBackupTest,
                usbSlurpDeleteTest,
                dataLossCheck,
                factoryReset
            ]
        else:
            testlist = [eval(single)]

        testcases = []
        for item in testlist:
            testrun = item(adb=adb, env=env)
            self.log.info('=============== Start to run {} test!! ==============='.format(str(item)))
            test = testrun.run()
            testcases.append(test)
            time.sleep(2)
        ts = TestSuite('BAT Test Suite', testcases)

        with open('output.xml', 'w') as f:
            TestSuite.to_file(f, [ts], prettyprint=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to run BAT')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number', default='5555')
    parser.add_argument('-env', help='Target environment', default='dev1')
    parser.add_argument('-single', help='Run single case')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    env = args.env
    single = args.single
    port = args.port

    adb = ADB(uut_ip=uut_ip, port=port)

    bat = bat_run(adb=adb)
    bat.run(single=single, env=env)

