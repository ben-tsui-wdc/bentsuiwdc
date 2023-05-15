# -*- coding: utf-8 -*-
""" Test for desktop sync tool: sync from remote to local (KAM-xxxxx).
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import time
# platform modules
from middleware.test_case import TestCase


class SyncNasToLocal(TestCase):

    TEST_SUITE = 'Desktop_Sync_Tests'
    TEST_NAME = 'Sync_From_Remote_To_Local'

    def init(self):
        self.ds_obj = self.share['desktop_sync_obj']
        self.src_path = self.share['src_path']
        self.dst_folder_name = self.share['dst_folder_name']
        self.file_server_ip = self.share['file_server_ip']
        self.download_path = '/test/DesktopSync/sync_nas_to_local/sync_nas_to_local.bmp'
        self.download_file = 'sync_nas_to_local.bmp'

    def test(self):
        self.log.info("Start to test sync from nas to local")
        self.log.info("Check if the sync process is started before, unsync them")
        result = self.ds_obj.get_sync()
        if result:
            # Todo: find if the src_path in result
            delete_result = self.ds_obj.delete_sync(self.src_path)
            if delete_result:
                self.log.info("Unsync successfully")
            else:
                raise self.err.TestFailure("Failed to unsync!")

        self.log.info("Download test files from file server to nas folder")
        user_id = self.uut_owner.get_user_id().replace('auth0|', 'auth0\|')
        self.adb.download_file_from_server(self.file_server_ip, self.download_path, user_id, self.dst_folder_name)
        if self.adb.check_file_exist_in_nas("{}/{}".format(self.dst_folder_name, self.download_file), user_id):
            self.log.info("Download test file successfully")
        else:
            raise self.err.TestFailure("Failed to download test file!")

        nas_checksum_dict = self.adb.MD5_checksum(user_id, self.dst_folder_name)
        self.log.debug("nas_checksum_dict:{}".format(nas_checksum_dict))

        owner_info = self.uut_owner.get_cloud_user()
        owner_first_name = owner_info["user_metadata"]["first_name"]
        dst_path = self.ds_obj.get_nas_mount_path(owner_first_name, self.dst_folder_name)
        result = self.ds_obj.create_sync(self.src_path, dst_path)
        if not result:
            raise self.err.TestFailure("Failed to create sync!")

        # Todo: Update when RD finish implement getting sync process
        time.sleep(90)

        local_checksum_dict = self.ds_obj.get_local_checksum_dict(self.src_path)
        self.log.debug("local_checksum_dict:{}".format(local_checksum_dict))

        local_file_list = local_checksum_dict.keys()
        nas_file_list = nas_checksum_dict.keys()
        result = self.ds_obj.compare_filename(local_file_list, nas_file_list)
        if result:
            self.log.info("File name comparison passed")
        else:
            raise self.err.TestFailure("File name comparison failed!")

        result = self.ds_obj.compare_checksum(local_checksum_dict, nas_checksum_dict)
        if result:
            self.log.info("MD5 comparison passed")
        else:
            raise self.err.TestFailure("MD5 comparison failed!")

        self.log.info("Sync local to NAS passed")