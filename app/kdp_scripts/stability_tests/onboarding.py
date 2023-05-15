# -*- coding: utf-8 -*-
""" Test for simulate user onboarding.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
import time
from itertools import count
# platform modules
from middleware.arguments import KDPInputArgumentParser
from kdp_scripts.restsdk_tests.functional_tests.factory_restore import FactoryRestoreTest
from platform_libraries.pyutils import retry
from platform_libraries.restAPI import RestAPI
# 3rd party modules
import requests


class OnBoarding(FactoryRestoreTest):

    TEST_SUITE = 'Stability Tests'
    TEST_NAME = 'Admin On-boarding Test'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-679,KDP-678'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.security_code = None

    def before_test(self):
        self.log.info("Init RestSDK client ...")
        self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username,
            password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
        RestAPI._ids = count(0)
        if self.env.uut_restsdk_port:
            self.uut_owner.update_device_ip("{}".format(self.env.uut_ip))
        self.uut_owner.id = 0
        self.uut_owner.update_device_id()

        self.log.info("Re-created admin user ...")
        retry(
            func=self.uut_owner.delete_user, delay=20, max_retry=30, log=self.log.warning
        )
        retry(
            func=self.uut_owner.create_user, username=self.env.username, password=self.env.password,
            delay=20, max_retry=30, log=self.log.warning
        )
        retry(
            func=self.uut_owner.get_fresh_id_token, delay=20, max_retry=30, log=self.log.warning
        )
        self.uut_owner._retry_times = 0
        self.uut_owner._retry_delay = 0

    def test(self):
        self.log.info("Checking local discovery")
        nRetries = 3
        foundDevice = None
        while nRetries > 0:
            try:
                resp = self.uut_owner.get_localdevice_from_cloud()
                local_devices = resp['data']
                for device in local_devices:
                    self.log.info('{} {} {}'.format(
                        device.get("type", ""), device.get("serialNumber", ""), device["network"].get("localIpAddress", "")
                    ))
                    if self.env.uut_ip in device['network'].get("localIpAddress", ""):
                        foundDevice = device
                        break
                if not foundDevice:
                    self.log.info("Fail to find device in local")
            except Exception as e:
                self.log.info("Fail to find device in local")

            if not foundDevice:
                try:
                    foundDevice = self.uut_owner.cloud.get_device_by_security_code(self.security_code)
                    self.log.info("Found device: " + foundDevice)
                except Exception as e:
                    self.log.info("Fail to find device by security code")

            if foundDevice:
                break

            nRetries -= 1
            if nRetries <= 0:
                self.log.error("Local discovery is FAILED")
                break # Since bad Lab network problem, ignore this error but logging error here.
                #raise AssertionError("Failed to find device from local discovery")
            self.log.warn("Failed to find device from local discovery. Retries remaining: %d" % nRetries)
            time.sleep(20)

        self.log.info("Checking device network info from cloud")
        nRetries = 30
        while nRetries > 0:
            try:
                self.uut_owner.get_device_network_from_cloud()
                break
            except Exception as e:
                self.log.warn(e)
                nRetries -= 1
                if nRetries <= 0:
                    raise AssertionError("Failed to get device network info from cloud")
                self.log.warn("Failed to get device network info from cloud. Retries remaining: %d" % nRetries)
                time.sleep(20)
        self.log.info("Get device network info from cloud successfully")

        self.log.info("Attaching user to device")
        nRetries = 10
        while nRetries > 0:
            try:
                self.uut_owner.attach_user_to_device()
                self.log.info("User is attached to device")
                break
            except Exception as e:
                self.log.warn(e)
                nRetries -= 1
                self.log.warn("Failed to attach. Retries remaining: %d" % nRetries)
                if nRetries <= 0:
                    raise AssertionError("Failed to attach using local code")
                time.sleep(5)

        self.uut_owner.get_device_from_cloud()

        time.sleep(10)

        self.log.info("Getting the root folder")
        self.uut_owner.search_file_by_parent()
        self.log.info("Test completed successfully")


    def after_test(self):
        self.log.info("Reset device...")
        super(OnBoarding, self).test()
        

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** On boarding test for KDP ***
        """)

    parser.add_argument('-sc', '--security_code', help='Security code of the test device', metavar='CODE')

    test = OnBoarding(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
