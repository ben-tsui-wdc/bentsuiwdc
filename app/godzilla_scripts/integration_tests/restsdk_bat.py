# -*- coding: utf-8 -*-
""" Godzilla RESTSDK integration test for daily.
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
from datetime import datetime, timedelta
# platform modules
from middleware.arguments import GodzillaIntegrationTestArgument
from middleware.godzilla_integration_test import GodzillaIntegrationTest
# Sub-tests
from godzilla_scripts.restsdk_bat_scripts.delete_data import DeleteDataTest
from godzilla_scripts.restsdk_bat_scripts.get_data_by_id import GetDataByIDTest
from godzilla_scripts.restsdk_bat_scripts.get_device_info import GetDeviceInfoTest
from godzilla_scripts.restsdk_bat_scripts.get_feature_flags import GetFeatureFlags
from godzilla_scripts.restsdk_bat_scripts.get_file_content import GetFileContentTest
from godzilla_scripts.restsdk_bat_scripts.get_media_time_groups import GetMediaTimeGroupsTest
from godzilla_scripts.restsdk_bat_scripts.get_owner_info_by_id import GetOwnerInfoByIDTest
from godzilla_scripts.restsdk_bat_scripts.get_users import GetUsersTest
from godzilla_scripts.restsdk_bat_scripts.get_video_playlist import GetVideoPlaylistTest
from godzilla_scripts.restsdk_bat_scripts.get_video_stream import GetVideoStreamTest
from godzilla_scripts.restsdk_bat_scripts.reboot_device import RebootDeviceTest
from godzilla_scripts.restsdk_bat_scripts.search_audio_file import SearchAudioFileTest
from godzilla_scripts.restsdk_bat_scripts.search_file_by_name import SearchFileByNameTest
from godzilla_scripts.restsdk_bat_scripts.search_file_by_text import SearchFileByTextTest
from godzilla_scripts.restsdk_bat_scripts.search_image_by_EXIF_time import SearchImageByEXIFTimeTest
from godzilla_scripts.restsdk_bat_scripts.search_root_folder import SearchRootFolderTest
from godzilla_scripts.restsdk_bat_scripts.upload_data import UploadDataTest
from godzilla_scripts.restsdk_bat_scripts.upload_file import UploadFileTest

class RESTSDK_BAT(GodzillaIntegrationTest):

    TEST_SUITE = 'GODZILLA RESTSDK BAT'
    TEST_NAME = 'GODZILLA RESTSDK BAT'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    PRIORITY = 'Blocker'
    COMPONENT = 'REST SDK'
    REPORT_NAME = 'REST SDK BAT'

    def init(self):
        tomorrow_timestamp_str = (datetime.now() + timedelta(1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            self.integration.add_testcases(testcases=[
                (RebootDeviceTest, {'wait_device': True}),
                GetDeviceInfoTest,
                GetUsersTest,
                (GetOwnerInfoByIDTest, {'TEST_NAME': 'Get User By ID'}),
                (UploadDataTest, {'data_name': '1K.data', 'TEST_NAME': 'Upload File'}),
                SearchRootFolderTest,
                (SearchFileByNameTest, {'name': '1K.data'}),
                (SearchFileByTextTest, {'keyword': '1K.data'}),
                (GetDataByIDTest, {'data_name': '1K.data', 'TEST_NAME': 'Get File Data By ID'}),
                (GetFileContentTest, {'file_name': '1K.data', 'source_file': '1K.data'}),
                (DeleteDataTest, {'data_name': '1K.data', 'TEST_NAME': 'Delete File'}),
                GetFeatureFlags
            ])

            self.integration.add_testcases(testcases=[
                (UploadFileTest, {
                    'file_url': 'http://{}/test/Images50GB/JPG/EXIF_images/hari_1219.jpg'.format(self.file_server_ip),
                    'check_mime_type': 'image/jpeg', 'TEST_NAME': 'Update Photo', 'TEST_JIRA_ID': 'GZA-1750'
                }),
                (UploadFileTest, {
                    'file_url': 'http://{}/test/Small5GB/Audio1GB/MP3/1kHz.mp3'.format(self.file_server_ip),
                    'check_mime_type': 'audio/mpeg', 'TEST_NAME': 'Update Audio', 'TEST_JIRA_ID': 'GZA-1738'
                }),
                (UploadFileTest, {
                    'file_url': 'http://{}/test/Large100GB/Video20GB/MP4/Elcard test files/BMP2_PSP.mp4'.format(self.file_server_ip),
                    'check_mime_type': 'video/mp4', 'TEST_NAME': 'Update Video', 'TEST_JIRA_ID': 'GZA-1756'
                }),
                (SearchAudioFileTest, {'file_name': '1kHz.mp3'}),
                (SearchImageByEXIFTimeTest, {'start_time': '2009-09-26T09:14:38.000Z', 'end_time': '2009-09-26T09:14:39.000Z'}),
                (GetMediaTimeGroupsTest, {
                    'end_time': tomorrow_timestamp_str, 'mime_groups': 'image', 'unit': 'year',
                    'TEST_NAME': 'Get Image Time Groups By Year Test', 'TEST_JIRA_ID': 'GZA-1744'
                }),
                (GetMediaTimeGroupsTest, {
                    'end_time': tomorrow_timestamp_str, 'mime_groups': 'audio', 'unit': 'month',
                    'TEST_NAME': 'Get Audio Time Groups By Month Test', 'TEST_JIRA_ID': 'GZA-1748'
                }),
                (GetMediaTimeGroupsTest, {
                    'end_time': tomorrow_timestamp_str, 'mime_groups': 'video', 'unit': 'day',
                    'TEST_NAME': 'Get Video Time Groups By Day Test', 'TEST_JIRA_ID': 'GZA-1747'
                })
            ])

            # Video test
            self.integration.add_testcases(testcases=[
                # (GetVideoStreamTest, {'file_name': 'BMP2_PSP.mp4', 'TEST_NAME': 'Get Matroska Video Stream'}),
                # (GetVideoPlaylistTest, {'file_name': 'BMP2_PSP.mp4', 'TEST_NAME': 'Get Video Playlist'})
            ])


if __name__ == '__main__':
    parser = GodzillaIntegrationTestArgument("""\
        *** RESTSDK_BAT on Kamino Android ***
        Examples: ./run.sh godzilla_scripts/integration_tests/restsdk_bat.py --uut_ip 10.136.137.159\
        """)

    # Test Arguments
    parser.add_argument('--single_run', help='Run single case for RESTSDK BAT')
    parser.add_argument('--file_server_ip', help='File server IP', default="fileserver.hgst.com")

    test = RESTSDK_BAT(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
