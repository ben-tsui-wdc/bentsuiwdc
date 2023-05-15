# -*- coding: utf-8 -*-
""" Case to shrink a drive from exist raid on grack model.
"""
__author__ = "Vance Lo <Vance.Lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import GrackInputArgumentParser
from middleware.grack_test_case import GrackTestCase
from platform_libraries.gtech_rpc_api import GTechRPCAPI


class ShrinkRAID(GrackTestCase):

    TEST_SUITE = 'GRack_BAT'
    TEST_NAME = 'Shrink RAID Test'

    def init(self):
        self.grack_ssh = GTechRPCAPI(uut_ip=self.env.uut_ip, username='admin', password='gtech', root_password='gtech')

    def test(self):
        uuid = self.grack_ssh.get_raid_uuid()[0]
        if not uuid:
            raise self.err.StopTest('No RAID exist, stop the test!!')
        raid_disk_list = self.grack_ssh.get_raid_candidates()
        self.log.info('RAID devices: {}'.format(raid_disk_list))
        shrink_disk = raid_disk_list[0]
        self.log.info('Choose disk:{}'.format(shrink_disk))
        self.grack_ssh.shrink_drive_from_RAID_set(uuid=uuid, devices=shrink_disk)
        time.sleep(3)  # Wait for apply configuration changed
        raid_disk_list = self.grack_ssh.get_raid_candidates()
        self.log.info('RAID disk list: {}'.format(raid_disk_list))
        if shrink_disk in str(raid_disk_list):
            raise self.err.TestFailure('Disk:{} is in the raid list, test failed !!'.format(shrink_disk))


if __name__ == '__main__':
    parser = GrackInputArgumentParser("""\
        *** Shrink RAID Test ***
        Examples: ./run.sh grack_scripts/shrink_raid.py --uut_ip 10.92.234.16\
        """)

    test = ShrinkRAID(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
