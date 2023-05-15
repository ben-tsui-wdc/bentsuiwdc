# -*- coding: utf-8 -*-
""" Case to add workspace on mount raid for grack model.
"""
__author__ = "Vance Lo <Vance.Lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import GrackInputArgumentParser
from middleware.grack_test_case import GrackTestCase
from platform_libraries.gtech_rpc_api import GTechRPCAPI


class AddWorkSpace(GrackTestCase):

    TEST_SUITE = 'GRack_BAT'
    TEST_NAME = 'Add Workspace Test'

    def init(self):
        self.grack_ssh = GTechRPCAPI(uut_ip=self.env.uut_ip, username='admin', password='gtech', root_password='gtech')
        self.workspace_name = 'grackautobattest_{}'.format(int(time.time()))

    def test(self):
        mount_devices_uuid = self.grack_ssh.get_mounted_devices().get('uuid')
        mount_devices_path = self.grack_ssh.get_mounted_devices().get('devicefile')
        if not mount_devices_uuid:
            raise self.err.StopTest('No mount RAID exist, stop the test!!')
        self.log.info('Mount devices:{}'.format(mount_devices_uuid))
        self.grack_ssh.add_workspace(name=self.workspace_name, raidpath=mount_devices_path)
        time.sleep(5) # Wait for apply configuration changed
        workspace_list = [item.get('name') for item in self.grack_ssh.get_workspace_list()[1]]
        self.log.info('WorkSpace List: {}'.format(workspace_list))
        if self.workspace_name not in workspace_list:
            raise self.err.TestFailure('WorkSpace:{} not in mount raid list, test failed !!'.format(self.workspace_name))


if __name__ == '__main__':
    parser = GrackInputArgumentParser("""\
        *** Add Workspace Test ***
        Examples: ./run.sh grack_scripts/add_workspace.py --uut_ip 10.92.234.16\
        """)

    test = AddWorkSpace(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
