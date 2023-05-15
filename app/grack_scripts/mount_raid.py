# -*- coding: utf-8 -*-
""" Case to mount raid on grack model.
"""
__author__ = "Vance Lo <Vance.Lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import GrackInputArgumentParser
from middleware.grack_test_case import GrackTestCase
from platform_libraries.gtech_rpc_api import GTechRPCAPI


class MountRAID(GrackTestCase):

    TEST_SUITE = 'GRack_BAT'
    TEST_NAME = 'Mount RAID Test'

    def init(self):
        self.grack_ssh = GTechRPCAPI(uut_ip=self.env.uut_ip, username='admin', password='gtech', root_password='gtech')

    def test(self):
        uuid = self.grack_ssh.get_raid_uuid()[0]
        if not uuid:
            raise self.err.StopTest('No RAID exist, stop the test!!')
        self.grack_ssh.mount_raid(uuid)
        time.sleep(5)  # Wait for apply configuration changed
        mount_devices = self.grack_ssh.get_mounted_devices().get('uuid')
        self.log.info('Mount devices:{}'.format(mount_devices))
        if uuid not in str(mount_devices):
            raise self.err.TestFailure('RAID:{} not in mount raid list, test failed !!'.format(uuid))


if __name__ == '__main__':
    parser = GrackInputArgumentParser("""\
        *** Mount RAID Test ***
        Examples: ./run.sh grack_scripts/mount_raid.py --uut_ip 10.92.234.16\
        """)

    test = MountRAID(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
