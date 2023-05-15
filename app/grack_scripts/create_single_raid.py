# -*- coding: utf-8 -*-
""" Case to create single raid on grack model.
"""
__author__ = "Vance Lo <Vance.Lo@wdc.com>"

# std modules
import sys
import time
from pprint import pformat

# platform modules
from middleware.arguments import GrackInputArgumentParser
from middleware.grack_test_case import GrackTestCase
from platform_libraries.gtech_rpc_api import GTechRPCAPI


class CreateRAID(GrackTestCase):

    TEST_SUITE = 'GRack_BAT'
    TEST_NAME = 'Create Single RAID Test'

    def declare(self):
        self.delete_raid = False

    def init(self):
        self.grack_ssh = GTechRPCAPI(uut_ip=self.env.uut_ip, username='admin', password='gtech', root_password='gtech')

    def test(self):
        if self.delete_raid:
            self.log.info('Delete RAID if there have RAID exist')
            uuid = self.grack_ssh.get_raid_uuid()
            if uuid:
                for item in uuid:
                    self.grack_ssh.delete_raid(item)
                    time.sleep(3)
                uuid = self.grack_ssh.get_raid_uuid()
                if uuid:
                    self.log.warning('RAID uuid exist: {}!'.format(uuid))
                    raise self.err.StopTest('Delete RAID Failed, stop the test !!')
        self.log.info('Start to Create RAID5 ...')
        device_list = self.grack_ssh.get_free_device_name_list()
        self.log.info('Free devices: {}'.format(device_list))
        self.grack_ssh.create_raid('grackraid5', 'btrfsraid5', '{},{},{},{}'
                                   .format(device_list[0],device_list[1],device_list[2],device_list[3]))
        uuid = self.grack_ssh.get_raid_uuid()
        if uuid:
            self.log.info(pformat(self.grack_ssh.get_available_btrfs_raid_list()[1]))
        else:
            raise self.err.TestFailure('Create RAID failed !! No RAID exist!')

if __name__ == '__main__':
    parser = GrackInputArgumentParser("""\
        *** Create Single RAID Test ***
        Examples: ./run.sh grack_scripts/create_single_raid.py --uut_ip 10.92.234.16\
        """)
    # Test Arguments
    parser.add_argument('--delete_raid', help='Delete RAID before create new RAID', action='store_true')

    test = CreateRAID(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
