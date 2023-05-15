# -*- coding: utf-8 -*-
""" kpi test for the elapsed time of factory_reset.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import re
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from bat_scripts_new.factory_reset import FactoryReset


class factory_reset_time(TestCase):
    TEST_SUITE = 'Performance_Tests'
    TEST_NAME = 'kpi_factory_reset_time'
    # Popcorn
    TEST_JIRA_ID = 'KAM-27711'

    SETTINGS = {'uut_owner' : False # Disbale restAPI.
    }

    # Pre-defined parameters for IntegrationTest
    def declare(self):
        pass


    # main function
    def test(self):
        starting_time = time.time()
        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=False']
        factory_reset = FactoryReset(env_dict)
        factory_reset.no_rest_api = True
        factory_reset.test()
        disk_size = 'None'

        if 'monarch' or 'yoda' in self.uut.get('model'):
            stdout, stderr = self.adb.executeShellCommand('sgdisk --print /dev/block/sataa24')
            disk_size_description = re.findall('/dev/block/sata\S* \S* sectors', stdout)[0]
            disk_size_sector = re.findall(' \d* ', disk_size_description)[0]
            disk_size_TB = int(disk_size_sector.strip())*0.5/1000/1000/1000
            if 0.4 < disk_size_TB < 0.5:
                disk_size = '0.5TB'
            elif 0.8 < disk_size_TB < 1:
                disk_size = '1TB'
            elif 1.8 < disk_size_TB < 2:
                disk_size = '2TB'
            elif 2.8 < disk_size_TB < 3:
                disk_size = '3TB'
            elif 3.8 < disk_size_TB < 4:
                disk_size = '4TB'
            elif 7 < disk_size_TB < 8:
                disk_size = '8TB'
            else:
                raise self.err.StopTest('Please check the disk_size of DUT.')

        if 'yoda' in self.uut.get('model'):
            # Check if BLE is launched
            #stdout, stderr = self.adb.executeShellCommand('logcat -d | grep BTWifiConfigService')
            stdout, stderr = self.adb.executeShellCommand('logcat -d | grep Advertising && logcat -d | grep LeAdvStarted')
            if self.uut.get('firmware').startswith('5.2.0'):
                if 'Advertising started' in stdout and 'success' in stdout:
                    pass
            elif not self.uut.get('firmware').startswith('5.2.0'):
                if 'startAdvertising' in stdout and 'success' in stdout:
                    pass
            else:
                raise self.err.TestError('"startAdvertising" and "success" aren\'t displayed in logcat.')
        while True:
            result = self.adb.executeShellCommand("ps | egrep 'otaclient|appmgr|restsdk'")[0]
            if 'otaclient' in result and \
                'appmgr' in result and \
                'restsdk-server' in result:
                factory_reset_time = time.time() - starting_time
                break
            elif time.time() - starting_time > 120:
                raise self.err.TestError('Although /proc/time occurred, one of otaclient|appmgr|restsdk still doesn\'t work after 120 seconds.')
            time.sleep(1)

        self.adb.stop_otaclient()

        self.data.test_result['disk_size'] = disk_size
        self.data.test_result['factory_reset_time'] = factory_reset_time


if __name__ == '__main__':

    parser = InputArgumentParser("""\
        *** time_machine_throughput test on Kamino Android ***
        Examples: ./run.sh performance_tests/factory_reset_time.py --uut_ip 10.92.224.13 \
        --debug_middleware --dry_run (optional) --ap_ssid private_2.4G
        """)

    test = factory_reset_time(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)