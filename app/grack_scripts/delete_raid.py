# -*- coding: utf-8 -*-
""" Case to delete raid on grack model.
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


class DeleteRAID(GrackTestCase):

    TEST_SUITE = 'GRack_BAT'
    TEST_NAME = 'RAID Delete Test'

    def declare(self):
        self.create_raid = False

    def init(self):
        self.grack_ssh = GTechRPCAPI(uut_ip=self.env.uut_ip, username='admin', password='gtech', root_password='gtech')

    def test(self):
        uuid = self.grack_ssh.get_raid_uuid()
        workspace_list = self.grack_ssh.get_workspace_uuid()
        if not uuid:
            if self.create_raid:
                self.log.info('Create RAID if there no RAID exist')
                self.log.info('Start to Create RAID5 ...')
                device_list = self.grack_ssh.get_free_device_name_list()
                self.log.info('Free devices: {}'.format(device_list))
                self.grack_ssh.create_raid('grackraid5', 'btrfsraid5', '{},{},{}'.format(device_list[0],device_list[1],device_list[2]))
                uuid = self.grack_ssh.get_raid_uuid()
                if not uuid:
                    raise self.err.StopTest('Create RAID Failed, stop the test !!')
            else:
                raise self.err.TestSkipped('No RAID exist, skipped the test!!')
        else:
            self.log.info('RAID exist: {}'.format(uuid))
        self.log.info('Start to Delete RAID: {}'.format(uuid))
        if workspace_list:
            for item in workspace_list:
                self.grack_ssh.delete_workspace(item)
        for item in uuid:
            self.grack_ssh.unmount_raid(item)
            time.sleep(3)
            self.grack_ssh.delete_raid(item)
            time.sleep(3)
        uuid = self.grack_ssh.get_raid_uuid()
        if uuid:
            self.log.warning('RAID uuid exist: {}!'.format(uuid))
            raise self.err.TestFailure('Delete RAID Failed, stop the test !!')

if __name__ == '__main__':
    parser = GrackInputArgumentParser("""\
        *** Delete RAID Test ***
        Examples: ./run.sh grack_scripts/delete_raid.py --uut_ip 10.92.234.16\
        """)
    # Test Arguments
    parser.add_argument('--create_raid', help='Create RAID before create new RAID', action='store_true')

    test = DeleteRAID(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
