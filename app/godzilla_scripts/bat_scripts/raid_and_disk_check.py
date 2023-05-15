# -*- coding: utf-8 -*-
""" Test case to check the raid and disk status
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import lxml.etree
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.constants import Godzilla as GZA


class RaidAndDiskCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Raid and Disk Status Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1154'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        model = self.ssh_client.get_model_name()
        self.log.info('Checking the Raid and Disk status for model: {}'.format(model))
        device_info = GZA.DEVICE_INFO.get(model)
        disk_num = device_info.get('disk')
        raid_type = device_info.get('raid')
        stdout, strerr = self.ssh_client.execute_cmd('cat /var/www/xml/used_volume_info.xml')
        root = lxml.etree.fromstring(stdout)
        device_raid_status = root.find('./volume_info/item/raid_status').text

        self.log.info('Device raid status: {}'.format(device_raid_status))
        if device_raid_status != 0:
            self.err.TestFailure('Check raid status failed! Error Code:{}'.format(device_raid_status))

        device_raid = root.find('./volume_info/item/raid_mode').text
        self.log.info("Expect raid types: {}".format(raid_type))
        self.log.info('Device raid type: {}'.format(device_raid))
        if device_raid not in raid_type:
            self.err.TestFailure('Check raid type failed! Support raids: {0}, current raid: {1}'.
                                 format(raid_type, device_raid))

        device_disks = root.find('./volume_info/item/dev_num').text
        self.log.info("Expect disk numbers: {}".format(disk_num))
        self.log.info('Device disk numbers: {}'.format(device_disks))
        if not (device_disks <= disk_num):
            self.err.TestFailure('Check disk status failed! Maximum disks: {0}, current disks: {1}'.
                                 format(disk_num, device_disks))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Device Name Check test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/raid_and_disk_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = RaidAndDiskCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
