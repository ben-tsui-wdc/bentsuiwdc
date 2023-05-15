# -*- coding: utf-8 -*-
""" For OTA Proxy error check (https://jira.wdmv.wdc.com/browse/IBIX-801).
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from bat_scripts_new.reboot import Reboot


class OTAProxyCheck(Reboot):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'OTA Proxy Error Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-35619'
    COMPONENT = 'PLATFORM'

    def test(self):
        try:
            super(OTAProxyCheck, self).test()
        except Exception as ex:
            raise self.err.TestSkipped('Reboot failed ! Skipped the OTA proxy error check test ! Error message: {}'.format(repr(ex)))
        timeout = 60*3
        self.timing.start()
        while not self.timing.is_timeout(timeout):
            versionInfo_check = self.adb.executeShellCommand('logcat -d -s otaclient | grep versionInfo')[0]
            if 'versionInfo' in versionInfo_check:
                break
            self.log.warning('versionInfo not found in logcat, wait for 10 secs and check again ...')
            time.sleep(10)
            if self.timing.is_timeout(timeout):
                raise self.err.TestFailure('OTA Proxy Check Failed, OTA service not started properly !!')
        otaclient_message = self.adb.executeShellCommand('logcat -d | grep otaclient')[0]
        currentVersion = self.adb.executeShellCommand('logcat -d | grep currentVersion')[0]
        if 'Internal Server Error' in otaclient_message:
            raise self.err.TestFailure('OTA Proxy Check Failed, Internal server error happened !!')
        if self.adb.getFirmwareVersion() not in currentVersion:
            raise self.err.TestFailure('Current Version value in OTA is not match with firmware version, Test Failed !!')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** OTA proxy error check Script ***
        Examples: ./run.sh bat_scripts/ota_proxy_check.py --uut_ip 10.92.224.68\
        """)

    test = OTAProxyCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
