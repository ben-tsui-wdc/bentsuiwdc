# -*- coding: utf-8 -*-
""" Test for desktop sync tool: offline unsync (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import time
# platform modules
from middleware.test_case import TestCase


class OfflineUnsync(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'Offline_Not_Sync'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']
        self.src_path = self.share['src_path']
        self.dst_folder_name = self.share['dst_folder_name']
        self.file_server_ip = self.share['file_server_ip']
        self.download_folder = '/test/DesktopSync/offline_unsync'

    def test(self):
        self.log.info("Start offline unsync test")
        self.log.info("Check if the sync process is started before, unsync them")
        result = self.ds_obj.get_sync()
        if result:
            # Todo: find if the src_path in result
            delete_result = self.ds_obj.delete_sync(self.src_path)
            if delete_result:
                self.log.info("Unsync successfully")
            else:
                raise self.err.TestFailure("Failed to unsync!")

        self.log.info("Download test files from file server to local backup folder")
        result = self.ds_obj.download_files_from_file_server(self.file_server_ip, self.download_folder, self.src_path)
        if result:
            self.log.info("Download test files successfuly")
        else:
            raise self.err.TestFailure("Failed to download test files")

        local_checksum_dict = self.ds_obj.get_local_checksum_dict(self.src_path)
        self.log.debug("local_checksum_dict:{}".format(local_checksum_dict))

        # Todo: Update when RD finish implement getting sync process
        time.sleep(90)

        user_id = self.uut_owner.get_user_id().replace('auth0|', 'auth0\|')
        nas_checksum_dict = self.adb.MD5_checksum(user_id, self.dst_folder_name)
        self.log.debug("nas_checksum_dict:{}".format(nas_checksum_dict))

        local_file_list = local_checksum_dict.keys()
        nas_file_list = nas_checksum_dict.keys()
        result = self.ds_obj.compare_filename(local_file_list, nas_file_list)
        if result:
            raise self.err.TestFailure("Sync should have been failed, but the files are synced!")
        else:
            self.log.info("Offline unsync test passed")


