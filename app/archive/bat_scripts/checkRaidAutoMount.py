___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from junit_xml import TestCase


class checkRaidAutoMount(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env
        self.log = common_utils.create_logger(overwrite=False)

    def run(self):
        start_time = time.time()
        testcase = None
        try:
            version, model = self.device_init()
            vol_list_1 = self.adb.executeShellCommand('df | grep volume')[0]
            vol_list_2 = self.adb.executeShellCommand('df | grep diskVolume0')[0]
            vol_check_1 = ['/storage/volume', '/mnt/runtime/default/volume']
            vol_check_2 = ['/data/wd/diskVolume0']
            btrfs_check = self.adb.executeShellCommand('btrfs filesystem df /data/wd/diskVolume0')[0]
            if model == 'monarch':
                if 'single' in btrfs_check:
                    raid_check = True
                else:
                    raid_check = False
            elif model == 'pelican':
                if 'RAID1' in btrfs_check:
                    raid_check = True
                else:
                    raid_check = False
            else:
                self.log.error('Model is not monarch or pelican')
                raid_check = False
            if all(word in vol_list_1 for word in vol_check_1) and all(word in vol_list_2 for word in vol_check_2) and raid_check:
                self.log.info('Disk Volume is mounted on Device!! Test PASSED!!!!')
                testcase = TestCase(name='RAID type & Volume Auto Mount Check', classname='BAT', elapsed_sec=time.time()-start_time)
            else:
                self.error('Disk Volume is not mounted on Device!! Test FAILED!!')
        except Exception as ex:
            testcase = TestCase(name='RAID type & Volume Auto Mount Check', classname='BAT', elapsed_sec=time.time()-start_time)
            testcase.add_failure_info('Test Failed. Err: {}'.format(ex))
        finally:
            return testcase

    def device_init(self):
        try:
            self.adb.connect()
            time.sleep(2)
            version = self.adb.getFirmwareVersion()
            platform = self.adb.getModel()
            self.log.info('Firmware is :{}'.format(version.split()[0]))
            self.log.info('Platform is :{}'.format(platform.split()[0]))
            time.sleep(1)
            return version.split()[0], platform.split()[0]
        except Exception as ex:
            self.log.error('Failed to connect to device and execute adb command! Err: {}'.format(ex))

    def error(self, message):
        """
            Save the error log and raise Exception at the same time
            :param message: The error log to be saved
        """
        self.log.error(message)
        raise RuntimeError(message)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    if args.port:
        port = args.port
    else:
        port = '5555'
    adb = ADB(uut_ip=uut_ip, port=port)

    testrun = checkRaidAutoMount(adb=adb)
    testrun.run()
