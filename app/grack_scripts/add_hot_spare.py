# -*- coding: utf-8 -*-
""" Case to add hot spare to exist raid on grack model.
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


class AddHotSpare(GrackTestCase):

    TEST_SUITE = 'GRack_BAT'
    TEST_NAME = 'Add Hot Spare Test'

    def init(self):
        self.grack_ssh = GTechRPCAPI(uut_ip=self.env.uut_ip, username='admin', password='gtech', root_password='gtech')

    def test(self):
        uuid = self.grack_ssh.get_raid_uuid()[0]
        if not uuid:
            raise self.err.StopTest('No RAID exist, stop the test!!')
        device_list = self.grack_ssh.get_free_device_name_list()
        self.log.info('Free device: {}'.format(device_list))
        hot_spare_drive = device_list[-1]
        self.grack_ssh.add_hot_spare(uuid=uuid, devices=hot_spare_drive)
        disk_list_status = self.grack_ssh.check_hot_spare_info(uuid)[1]
        print pformat(self.grack_ssh.check_hot_spare_info(uuid))
        hotspare = [str(item['devicefile']) for item in disk_list_status if item.get('hotspare')]
        self.log.info('Choose hotspare: {}, Current hot spare list: {}'.format(hot_spare_drive, hotspare))
        if hot_spare_drive not in hotspare:
            raise self.err.TestFailure('Choose hot spare is not in the list, test failed !!')


if __name__ == '__main__':
    parser = GrackInputArgumentParser("""\
        *** Add Hot Spare Test ***
        Examples: ./run.sh grack_scripts/add_hot_spare.py --uut_ip 10.92.234.16\
        """)

    test = AddHotSpare(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
