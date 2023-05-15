# -*- coding: utf-8 -*-
""" Test for API: GET /v1/device (KAM-24493).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.pyutils import retry


class GetWiFiStatus(TestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Get WiFi Status'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-24493'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.utility_path = '/data/wd/diskVolume0/yoda'

    class Retry(Exception):
        pass

    def before_test(self):
        self.adb.executeShellCommand(cmd='test -e {0} || mkdir {0}'.format(self.utility_path), consoleOutput=True)
        self.adb.executeShellCommand(cmd='test -e {0}/libnl.tar.gz || busybox wget http://{0}/utility/yoda/libnl.tar.gz -P {1}'.format(
            self.adb.get_fileserver_url(), self.utility_path), consoleOutput=True)
        self.adb.executeShellCommand(cmd='test -e {0}/iw || busybox tar xvzf {0}/libnl.tar.gz -C {0}/'.format(self.utility_path),
            consoleOutput=True)
        self.adb.executeShellCommand(cmd='chmod +x {}/iw'.format(self.utility_path), consoleOutput=True)

    def after_test(self):
        self.adb.executeShellCommand(cmd='test -e {0} && rm -r {0}'.format(self.utility_path), consoleOutput=True)

    def test(self):
        # Since we can not ensure data get at the same time, the rssi value may changed, so here we give it 5 chances.
        retry(func=self._test, excepts=(GetWiFiStatus.Retry), delay=0, max_retry=5, log=self.log.warning)

    def _test(self):
        # Prepare expected value. (Here has a little delay with request)
        status = self.get_wifi_status()
        self.log.info('WiFi status from command: \n{}'.format(pformat(status)))
        if len(status) != 4:
            raise self.err.TestFailure('WiFi status is not enough.')
        # Send Request
        ret_val = self.uut_owner.get_uut_info()
        self.log.info('API Response: \n{}'.format(pformat(ret_val)))
        self.verify_response(ret_val, expected=status)

    def get_wifi_status(self):
        stdout, _ = self.adb.executeShellCommand(cmd='LD_LIBRARY_PATH={0} {0}/iw dev wlan0 link'.format(self.utility_path))
        status = {}
        for line in stdout.split('\n'):
            strings = line.split()
            if 'SSID' in line:
                status['ssid'] = strings[1]
            elif 'freq' in line:
                status['frequency'] = int(strings[1])
            elif 'tx' in line:
                v = float(strings[2])
                if 'KBit/s' in strings[3]:
                    v = v * 1000
                elif 'MBit/s' in strings[3]:
                    v = v * 1000 * 1000
                elif 'GBit/s' in strings[3]:
                    v = v * 1000 * 1000 * 1000
                status['linkSpeed'] = v
            elif 'signal' in line:
                status['rssi'] = int(strings[1])
        return status

    def calculate_signal_level(self, rssi, num_levels=2, MIN_RSSI=-100, MAX_RSSI=-55):
        """ Calculate signal level.

        From https://github.com/aosp-mirror/platform_frameworks_base/blob/master/wifi/java/android/net/wifi/WifiManager.java#L848
        """
        if rssi <= MIN_RSSI:
            return 0
        elif rssi >= MAX_RSSI:
            return num_levels - 1
        else:
            input_range = (MAX_RSSI - MIN_RSSI)
            output_range = (num_levels - 1)
            return int(float(rssi - MIN_RSSI) * output_range / input_range)

    def verify_response(self, resp, expected):
        def verify_value(key):
            if status[key] != expected[key]:
                raise self.err.TestFailure('{} is not correct, value is {} but expect is {}'.format(key, status[key], expected[key]))
            self.log.info('{} is correct.'.format(key))

        # Check wifi field.
        if 'wifi' not in resp:
            raise self.err.TestFailure('No wifi status.')
        status = resp['wifi']

        # verify ssid, frequency and linkSpeed
        verify_value('ssid')
        verify_value('frequency')
        verify_value('linkSpeed')

        # verify rssi
        rssi = float(status['rssi'])
        # Since rssi value changed very quickly, here we give it a torrance.
        if expected['rssi'] * 0.9 < rssi or rssi < expected['rssi'] * 1.1:
            raise GetWiFiStatus.Retry('rssi is not correct, value is {} but expect is {}'.format(rssi, expected['rssi']))
        self.log.info('rssi is correct.')

        # verify signalLevel
        signal_level = self.calculate_signal_level(rssi) # Use rssi value from endpoint for deviation issue.
        if status['signalLevel'] != signal_level: # Steve said this value is float (?).
            raise self.err.TestFailure('signalLevel is not correct, value is {} but expect is {}'.format(status['signalLevel'], signal_level))
        self.log.info('signalLevel is correct.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** GetWiFiStatus test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/get_wifi_status.py --uut_ip 10.136.137.159\
        """)

    test = GetWiFiStatus(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
