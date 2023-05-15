# -*- coding: utf-8 -*-
""" Storage Management Test.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import time
import numbers
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.assert_utls import assert_equal
from platform_libraries.constants import RnD


class NasAdminStorageTest(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-5516 - nasAdmin - Storage Management Test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5516'
    ISSUE_JIRA_ID = None

    def test(self):
        volumes = self.nasadmin.get_volumes()
        mdstat, mdadms = self.ssh_client.all_md_info()
        assert_equal(len(volumes), len(mdadms))

        for v in volumes:
            found_md = None
            v_uuid = v['uuid']
            if '-' in v_uuid: # remove sep char to compare
                v_uuid = v_uuid.replace('-', '')
            for name, md in mdadms.iteritems():
                if md['information']['UUID'].replace(':', '') == v_uuid:
                    found_md = md
            assert found_md, "Not found md with UUID: " + v['uuid']

            assert_equal(v['id'], found_md.get_id())

            # array size = capacity(99 %) + reserved(1 %)
            size_in_blocks = self.ssh_client.get_blocks_by_md(found_md.get_name())
            assert v['capacity'] > 0.98 * size_in_blocks, \
                'capacity: {} is not 99% of block size: {}'.format(volumes['capacity'], size_in_blocks)

            used_slots = []
            for node_path in mdadms[found_md.get_name()]['raidDevices']:
                node_name = node_path[5:8]
                drive_slot = self.ssh_client.get_drive_slot_by_node(node_name)
                used_slots.append(drive_slot)
            assert_equal(set(v['usedSlots']), set(used_slots))

            assert_equal(v['state'], mdstat.get_defined_state(found_md.get_name()))
            # assert_equal(v['stateDetail'], mdstat[found_md.get_name()]['progress']) # process has timing issue

        drives_info = self.nasadmin.get_drives_info()
        smart_dict = self.ssh_client.get_all_smart_info()
        for drive in drives_info:
            assert drive['slot'] in smart_dict, 'Not found a drive with slot=' + drive['slot']
            smart = smart_dict[drive['slot']]
            assert_equal(drive['vendor'], smart.get_vendor())
            assert_equal(drive['model'], smart['information']['Device Model'])
            assert_equal(drive['serial'], smart['information']['Serial Number'])
            assert_equal(drive['capacity'], smart.get_capacity())
            assert_equal(drive['firmware'], smart['information']['Firmware Version'])


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** nasAdmin - Storage Management Test ***
        """)

    test = NasAdminStorageTest(parser)
    resp = test.main()
    print 'test result: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
