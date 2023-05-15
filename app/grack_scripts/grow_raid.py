# -*- coding: utf-8 -*-
""" Case to grow new drive to exist raid on grack model.
"""
__author__ = "Vance Lo <Vance.Lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import GrackInputArgumentParser
from middleware.grack_test_case import GrackTestCase
from platform_libraries.gtech_rpc_api import GTechRPCAPI


class GrowRAID(GrackTestCase):

    TEST_SUITE = 'GRack_BAT'
    TEST_NAME = 'Grow RAID Test'

    def init(self):
        self.grack_ssh = GTechRPCAPI(uut_ip=self.env.uut_ip, username='admin', password='gtech', root_password='gtech')

    def test(self):
        uuid = self.grack_ssh.get_raid_uuid()[0]
        if not uuid:
            raise self.err.StopTest('No RAID exist, stop the test!!')
        device_list = self.grack_ssh.get_free_device_name_list()
        self.log.info('Free devices: {}'.format(device_list))
        grow_disk = device_list[-1]
        self.log.info('Choose disk:{}'.format(grow_disk))
        self.grack_ssh.grow_drive_from_RAID_set(uuid=uuid, devices=grow_disk)
        time.sleep(3)  # Wait for apply configuration changed
        raid_disk_list = self.grack_ssh.get_raid_candidates()
        self.log.info('RAID_disk_list: {}'.format(raid_disk_list))
        if grow_disk not in str(raid_disk_list):
            raise self.err.TestFailure('Choose disk:{} not in the raid list, test failed !!'.format(grow_disk))


if __name__ == '__main__':
    parser = GrackInputArgumentParser("""\
        *** Grow RAID Test ***
        Examples: ./run.sh grack_scripts/grow_raid.py --uut_ip 10.92.234.16\
        """)

    test = GrowRAID(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
