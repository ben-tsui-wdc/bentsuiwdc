# -*- coding: utf-8 -*-

# std modules
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.constants import Kamino


class SearchingTest(TestCase):

    TEST_SUITE = 'Searching_Tests'
    TEST_NAME = 'Search_all_Test'

    def init(self):
        self.copied_folder_id = None # Parent ID to search.

    def before_test(self):
        """ Prepare test environment. """
        # TODO: Maybe it can combine with data comparison test.
        self.log.info("Clean UUT owner's home directory...")
        self.uut_owner.clean_user_root()
        #self.uut_owner.clean_user_root_by_rm(adb_inst=self.adb)
        #self.uut_owner.clean_user_root_by_delete_each()
        self.log.info("Copy test data from USB to UUT owner's home directory...")
        copy_task_id, usb_info, resp = self.uut_owner.usb_slurp(timeout=self.copy_timeout)
        # Get copied folder information.
        copied_folder, search_time = self.uut_owner.search_file_by_parent_and_name(name=usb_info['name'])
        self.log.info("Copied folder: {}".format(copied_folder))
        self.copied_folder_id = copied_folder['id']

    def test(self):
        """ Just search all files of entire specified folder.
        """
        # Search root parent.
        _, sub_folder_ids = self.uut_owner.walk_folder(search_parent_id=self.copied_folder_id, scroll_limit=self.scroll_limit)
        # Search sub-folders from top to bottom.
        while sub_folder_ids:
            next_roud_ids = []
            for folder_id in sub_folder_ids:
                _, folder_id_list = self.uut_owner.walk_folder(search_parent_id=folder_id, scroll_limit=self.scroll_limit)
                next_roud_ids+=folder_id_list # Collect deeper level sub-folder IDs.
            sub_folder_ids = next_roud_ids


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Searching Test on Kamino Android ***
        Examples: ./run.sh performance_tests/searching_test.py --uut_ip 192.168.1.45\
        """)
    # Test Arguments
    parser.add_argument('-limit', '--scroll_limit', help='How many data to scroll each page', type=int, default=1000)
    parser.add_argument('-ct', '--copy_timeout', help='Timeout of wating USB slurp', type=int, default=36000)
    args = parser.parse_args()

    test = SearchingTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
