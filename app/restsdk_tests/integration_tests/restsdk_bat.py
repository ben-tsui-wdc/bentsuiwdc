# -*- coding: utf-8 -*-
""" RESTSDK integration test for daily.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
from datetime import datetime, timedelta
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
# Sub-tests
from restsdk_tests.functional_tests.abort_file_copy import AbortFileCopyTest
from restsdk_tests.functional_tests.delete_data import DeleteDataTest
from restsdk_tests.functional_tests.factory_restore import FactoryRestoreTest
from restsdk_tests.functional_tests.factory_restore_for_yoda import FactoryRestoreTestForYoda
from restsdk_tests.functional_tests.file_copy_from_usb import FileCopyFromUsbTest
from restsdk_tests.functional_tests.get_data_by_id import GetDataByIDTest
from restsdk_tests.functional_tests.get_device_info import GetDeviceInfoTest
from restsdk_tests.functional_tests.get_feature_flags import GetFeatureFlags
from restsdk_tests.functional_tests.get_file_content import GetFileContentTest
from restsdk_tests.functional_tests.get_file_copy import GetFileCopyTest
from restsdk_tests.functional_tests.get_media_time_groups import GetMediaTimeGroupsTest
from restsdk_tests.functional_tests.get_owner_info_by_id import GetOwnerInfoByIDTest
from restsdk_tests.functional_tests.get_users import GetUsersTest
from restsdk_tests.functional_tests.get_video_playlist import GetVideoPlaylistTest
from restsdk_tests.functional_tests.get_video_stream import GetVideoStreamTest
from restsdk_tests.functional_tests.get_wifi_status import GetWiFiStatus
from restsdk_tests.functional_tests.ns_get_video_playlist import NSGetVideoPlaylistTest
from restsdk_tests.functional_tests.ns_get_video_stream import NSGetVideoStreamTest
from restsdk_tests.functional_tests.reboot_device import RebootDeviceTest
from restsdk_tests.functional_tests.search_audio_file import SearchAudioFileTest
from restsdk_tests.functional_tests.search_file_by_name import SearchFileByNameTest
from restsdk_tests.functional_tests.search_file_by_text import SearchFileByTextTest
from restsdk_tests.functional_tests.search_image_by_EXIF_time import SearchImageByEXIFTimeTest
from restsdk_tests.functional_tests.search_image_sample_by_EXIF_time import SearchImageSampleByEXIFTimeTest
from restsdk_tests.functional_tests.search_root_folder import SearchRootFolderTest
from restsdk_tests.functional_tests.upload_data import UploadDataTest
from restsdk_tests.functional_tests.upload_file import UploadFileTest


class RESTSDK_BAT(IntegrationTest):

    TEST_SUITE = 'RESTSDK BAT'
    TEST_NAME = 'RESTSDK BAT'
    # Popcorn
    TEST_TYPE = 'functional'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    REPORT_NAME = 'BAT'

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
                (DeleteDataTest, {'data_name': '1K.data', 'TEST_NAME': 'Delete File'})
            ])

            # USB relevant test
            if self.uut['model'] not in ['yoda']:
                self.integration.add_testcases(testcases=[
                    (FileCopyFromUsbTest, {'verify_by_any_file': True}),
                    GetFileCopyTest,
                    AbortFileCopyTest
                ])

            self.integration.add_testcases(testcases=[
                (UploadFileTest, {
                    'file_url': 'http://fileserver.hgst.com/test/Images50GB/JPG/EXIF_images/hari_1219.jpg',
                    'check_mime_type': 'image/jpeg', 'TEST_NAME': 'Update Photo', 'TEST_JIRA_ID':'KAM-19803'
                }),
                (UploadFileTest, {
                    'file_url': 'http://fileserver.hgst.com/test/Small5GB/Audio1GB/MP3/1kHz.mp3',
                    'check_mime_type': 'audio/mpeg', 'TEST_NAME': 'Update Audio', 'TEST_JIRA_ID':'KAM-19804'
                }),
                (UploadFileTest, {
                    'file_url': 'http://fileserver.hgst.com/test/Large100GB/Video20GB/MP4/Elcard test files/BMP2_PSP.mp4',
                    'check_mime_type': 'video/mp4', 'TEST_NAME': 'Update Video', 'TEST_JIRA_ID':'KAM-19805'
                }),
                (SearchAudioFileTest, {'file_name': '1kHz.mp3'}),
                #(SearchImageSampleByEXIFTimeTest, {'start_time': '2009-09-26T09:14:38.000Z', 'end_time': '2009-09-26T09:14:39.000Z'}),
                (SearchImageByEXIFTimeTest, {'start_time': '2009-09-26T09:14:38.000Z', 'end_time': '2009-09-26T09:14:39.000Z'}),
                (GetMediaTimeGroupsTest, {
                    'end_time': tomorrow_timestamp_str, 'mime_groups': 'image', 'unit': 'year',
                    'TEST_NAME': 'Get Image Time Groups By Year Test', 'TEST_JIRA_ID':'KAM-20434'
                }),
                # KDP-1118
                #(GetMediaTimeGroupsTest, {
                #    'end_time': tomorrow_timestamp_str, 'mime_groups': 'audio', 'unit': 'month',
                #    'TEST_NAME': 'Get Audio Time Groups By Month Test', 'TEST_JIRA_ID':'KAM-20435'
                #}),
                (GetMediaTimeGroupsTest, {
                    'end_time': tomorrow_timestamp_str, 'mime_groups': 'video', 'unit': 'day',
                    'TEST_NAME': 'Get Video Time Groups By Day Test', 'TEST_JIRA_ID':'KAM-20436'
                }),
                #(GetMediaTimeGroupsTest, {
                #    'end_time': tomorrow_timestamp_str, 'mime_groups': 'application', 'unit': 'hour',
                #    'TEST_NAME': 'Get Data Time Groups By Hour Test', 'TEST_JIRA_ID':'KAM-16651'
                #})
            ])

            # Device Features test
            if self.uut['firmware'].startswith('4.5') or self.uut['firmware'].startswith('5.'):
                self.integration.add_testcases(testcases=[
                    GetFeatureFlags
                ])

            # WiFi status test
            if self.uut['model'] in ['yoda', 'yodaplus']:
                self.integration.add_testcases(testcases=[
                    GetWiFiStatus
                ])

            # Video test
            if self.uut['model'] in ['monarch', 'pelican', 'yodaplus']:
                self.integration.add_testcases(testcases=[
                    (GetVideoStreamTest, {'file_name': 'BMP2_PSP.mp4', 'TEST_NAME': 'Get Matroska Video Stream'}),
                    (GetVideoPlaylistTest, {'file_name': 'BMP2_PSP.mp4', 'TEST_NAME': 'Get Video Playlist'})
                ])
            elif self.uut['model'] in ['yoda']:
                self.integration.add_testcases(testcases=[
                    (NSGetVideoStreamTest, {'file_name': 'BMP2_PSP.mp4', 'TEST_NAME': 'Negative: Get Matroska Video Stream'}),
                    (NSGetVideoPlaylistTest, {'file_name': 'BMP2_PSP.mp4', 'TEST_NAME': 'Negative: Get Video Playlist'}),
                ])

            # Factory reset test
            if self.uut['model'] in ['monarch', 'pelican']:
                self.integration.add_testcases(testcases=[
                    (FactoryRestoreTest, {'wait_device': True})
                ])
            elif self.uut['model'] in ['yoda', 'yodaplus']:
                self.integration.add_testcases(testcases=[
                    (FactoryRestoreTestForYoda, {'wait_device': True})
                ])


if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** RESTSDK_BAT on Kamino Android ***
        Examples: ./run.sh restsdk_tests/integration_tests/restsdk_bat --uut_ip 10.136.137.159\
        """)

    # Test Arguments
    parser.add_argument('--single_run', help='Run single case for Yoda RESTSDK BAT')


    test = RESTSDK_BAT(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
