# -*- coding: utf-8 -*-
""" Test for simulate auto backup
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
import time
import threading
# platform modules
from platform_libraries.common_utils import execute_local_cmd
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.restAPI import ItemParser, RestAPI
from platform_libraries.test_thread import MultipleThreadExecutor
from auto_backup import AutoBackup
# 3rd party modules
import requests


def test_wrapper(method):
    def wrapper(self, *args, **kwargs):
        try:
            ret = method(self, *args, **kwargs)
            self.log.info("Test is passed")
            return ret
        except Exception as e:
            self.log.info("Test is failed")
            raise e
    return wrapper


class MultipleUserFileUpload(AutoBackup):

    TEST_SUITE = 'Stability Tests'
    TEST_NAME = 'Multiple user - File Upload Test'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-380'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        super(MultipleUserFileUpload, self).declare()
        self.user_number = 5
        self.users = []
        self.user_data_root = []

    def init(self):
        self.debug_lock = threading.Lock()
        super(MultipleUserFileUpload, self).init()

        self.users = [self.uut_owner]
        for idx in xrange(1, self.user_number):
            self.log.info("Attaching user{}".format(idx))
            uut_ip = "{}:{}".format(self.env.uut_ip, self.env.uut_restsdk_port) if self.env.uut_restsdk_port else self.env.uut_ip
            self.users.append(RestAPI(uut_ip=uut_ip, env=self.env.cloud_env, username="wdcautotw+qawdc.mufu{}@gmail.com".format(idx),
                password=self.env.password, init_session=True, log_name="User{}".format(idx), stream_log_level=self.env.stream_log_level))
        self.log.info("User clients: {}".format(self.users))

        self.log.info("Wait for user is ready by creating a tmp folder") # for 404 issue
        for user in self.users:
            for idx in xrange(10):
                try:
                    user.create_folder("check")
                    break
                except Exception as e:
                    user.log.warning(e)
                    if idx == 9:
                        user.log.warning('Seem the user is not ready yet')
                    else:
                        time.sleep(6)

        self.user_data_root = []
        for idx in xrange(len(self.users)):
            self.log.info("Create dara link for user{0} link: ./{0}".format(idx))
            if not os.path.exists(str(idx)):
                execute_local_cmd('ln -s "{}" "{}"'.format(self.local_path, idx))
            self.user_data_root.append(idx)
        self.log.info("User data roots: {}".format(self.user_data_root))

    def before_test(self):
        for idx, user in enumerate(self.users):
            user.log.info("Clean home directory...")
            user.clean_user_root()

    @test_wrapper
    def test(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        for idx, user in enumerate(self.users):
            user.log.info("Upload files to device...")
            mte.append_thread_by_func(self.user_test, name="User{} thread".format(idx),
                args=[user, str(idx)], kwargs=None)
        mte.run_threads()
        self.verify_result()

    def user_test(self, user_inst, path):
        def print_console(sleep_secs):
            time.sleep(sleep_secs)
            for line in self.serial_client.serial_read_all(time_for_read=1):
                self.serial_client.logger.info(line)
            user_inst.log.info("-"*50)
        try:
            return user_inst.recursive_upload(path)
        except Exception as e:
            self.debug_lock.acquire()
            try:
                user_inst.log.warning("Debugging device status")
                if self.serial_client:
                    print_console(sleep_secs=0)
                    self.serial_client.serial_write("ifconfig")
                    print_console(sleep_secs=1)
                    self.serial_client.serial_write("ping 8.8.8.8 -c 1")
                    print_console(sleep_secs=2)
                    self.serial_client.serial_write("ps | grep rest | grep -v grep")
                    print_console(sleep_secs=1)
                execute_local_cmd('ping "{}" -c 1'.format(self.env.uut_ip))
            except Exception as ignored:
                user_inst.log.warning("Error from debugging: {}".format(ignored))
            finally:
                self.debug_lock.release()
                raise e

    def verify_result(self):
        # Handle root parent.
        file_list, sub_folders = self.uut_owner.walk_folder(search_parent_id='root', item_parser=ItemParser.id_and_name)

        for first_level_folder in sub_folders:
            if first_level_folder['name'] not in self.user_data_root:
                continue
            self.log.info("Verifying update files for user{}".format(first_level_folder['name']))
            self.verify_user_root(first_level_folder['id'])

    def verify_user_root(self, root_id):
        files_in_device = []
        sub_folder_ids = [root_id]
        # Search sub-folders from top to bottom.
        while sub_folder_ids:
            next_round_ids = []
            for folder_id in sub_folder_ids:
                file_list, sub_folders = self.uut_owner.walk_folder(search_parent_id=folder_id, item_parser=ItemParser.id_and_name)
                for file in file_list:
                    files_in_device.append(file['name'])
                next_round_ids+=[sub_folder['id'] for sub_folder in sub_folders] # Collect deeper level sub-folder IDs.
            sub_folder_ids = next_round_ids
            
        # comapre file names
        not_found_files = []
        for file_name in self.data_set:
            if file_name in files_in_device:
                files_in_device.remove(file_name)
            else:
                not_found_files.append(file_name)
        if not_found_files:
            raise self.err.TestFailure("Not found files: {}".format(not_found_files))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Multiple user file upload test for KDP ***
        """)

    parser.add_argument('-fu', '--file_url', help='Source file URL', metavar='URL')
    parser.add_argument('-lp', '--local_path', help='Local path to uplaod', metavar='PATH', default='local')
    parser.add_argument('-un', '--user_number', help='Total number of test user', metavar='NUMER', type=int, default=5)

    test = MultipleUserFileUpload(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
