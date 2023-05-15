# -*- coding: utf-8 -*-
""" Mean Time Between Failure test.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import os
import sys
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
# Sub-tests
from bat_scripts_new.reboot import Reboot
from integration_tests.sequential_sharing_stress import SequentialSharingStress
from integration_tests.concurrent_sharing_stress import ConcurrentSharingStress
from integration_tests.folder_creation_stress import StressFolderCreation

from integration_tests.factory_reset_stress import FactoryResetStress
from integration_tests.fw_update_stress import FWUpdateStress
from integration_tests.io_stress import StressIOTest
from integration_tests.time_machine_stress import TimeMachineBackupRestore
from functional_tests.update_fw_to_same_version import UpdateFWToSameVersion
from functional_tests.usb_fs import USBFormat
from transcoding_tests.functional_tests.single_file_transcoding import SingleFileTranscodingTest
from transcoding_tests.functional_tests.ns_single_file_transcoding import NSSingleFileTranscodingTest


class MTBF(IntegrationTest):

    TEST_SUITE = 'MTBF'
    TEST_NAME = 'MTBF_p1'
    REPORT_NAME = 'MTBF'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        '''
        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            self.integration.add_testcases(testcases=[
                (StressIOTest, {'TEST_NAME':'upload_donwload_test', 'test_type':'m','iteration_per_user':3, 'user_number':5, 'file_server':'fileserver.hgst.com', 'private_network':True}),
            ])
        '''
        
        '''
        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            self.integration.add_testcases(testcases=[
                (RebootStress, {'TEST_NAME':'Reboot', 'no_rest_api': False}),
                (FactoryResetStress, {'no_rest_api': True, 'TEST_NAME': 'KAM-13972: Factory Reset Test'}),
            ])
        '''

        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            self.integration.add_testcases(testcases=[
                (Reboot, {'no_rest_api': False, 'wait_device': True, 'TEST_NAME': 'Reboot device', 'disable_clean_logcat_log': True}),
                (USBFormat, {'usb_fs': 'fat32', 'TEST_NAME': 'USB Slurp on MBR_FAT32', 'run_models':['monarch', 'pelican', 'yodaplus']}),
                (StressIOTest, {'TEST_NAME':'Upload, Download and Delete 100 pictures or video files for 5 users', 'test_type':'mt','iteration_per_user':1, 'user_number':5, 'file_server':'fileserver.hgst.com', 'private_network':True}),
                (SingleFileTranscodingTest, {
                    'TEST_NAME': 'Transcode of 4K H265 AAC 60_30_24FPS to 1080P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                    'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/4K_H.265_30fps.mp4',
                    'target_container': 'matroska', 'target_resolution': '1080p', 'run_models':['pelican', 'yodaplus']
                }),
                (SingleFileTranscodingTest, {
                    'TEST_NAME': 'Transcode of 4K H.265 AAC 60_30_24FPS to 720P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                    'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/4K_H.265_30fps.mp4',
                    'target_container': 'matroska', 'target_resolution': '720p', 'run_models':['pelican', 'yodaplus']
                }),
                (SingleFileTranscodingTest, {
                    'TEST_NAME': 'Transcode of 4K H.265 AAC 60_30_24FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                    'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/4K_H.265_30fps.mp4',
                    'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['pelican', 'yodaplus']
                }),
                (SingleFileTranscodingTest, {
                    'TEST_NAME': 'Transcode of 4K VP9 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                    'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/4K_VP9.webm',
                    'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['pelican', 'yodaplus']
                }),
                (SingleFileTranscodingTest, {
                    'TEST_NAME': 'Transcode of 1080P H.264 30FPS to 720P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                    'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_H.264.mp4',
                    'target_container': 'matroska', 'target_resolution': '720p', 'run_models':['monarch', 'pelican', 'yodaplus']
                }),
                (SingleFileTranscodingTest, {
                    'TEST_NAME': 'Transcode of 1080P VP9 30FPS to 720P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                    'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_VP9.webm',
                    'target_container': 'matroska', 'target_resolution': '720p', 'run_models':['monarch', 'pelican', 'yodaplus']
                }),
                (SingleFileTranscodingTest, {
                    'TEST_NAME': 'Transcode of 1080P H.264 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                    'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_H.264.mp4',
                    'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus']
                }),
                (SingleFileTranscodingTest, {
                    'TEST_NAME': 'Transcode of 1080P VP9 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                    'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_VP9.webm',
                    'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus']
                }),
                (SingleFileTranscodingTest, {
                    'TEST_NAME': 'Transcode of 4K H.265 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                    'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/4K_H.265_30fps.mp4',
                    'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['pelican', 'yodaplus']
                }),
                (SingleFileTranscodingTest, {
                    'TEST_NAME': 'Transcode of 1080P MPEG4 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                    'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_MPEG4.mp4',
                    'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus']
                }),
                (SingleFileTranscodingTest, {
                    'TEST_NAME': 'Transcode of 720P H.264 30FPS to 480P', 'db_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db',
                    'test_file_url': 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/720P_H.264.mp4',
                    'target_container': 'matroska', 'target_resolution': '480p', 'run_models':['monarch', 'pelican', 'yodaplus']
                }),
                (StressFolderCreation, {'TEST_NAME':'Folder Creation stress', 'folder_number':800, 'loop_times':1}),
            ])

            '''
            # These following scripts will keep generating a lot of sharelinks during test. However, every time "GET /shares/v1/shares/:id" is executed,  cloud will generate auth0 client token for "Public Share App" client, then "Public Share App" client will return the token to client(WebApp/Mobile/automated test). And usging auth0 is very expensive.
            Therefore, stop these following tests.
            # (SequentialSharingStress, {'TEST_NAME':'Sequential Sharing stress', 'testing_duration':'5'}),
            # (ConcurrentSharingStress, {'TEST_NAME':'Concurrent Sharing stress', 'testing_duration':'5'}),
            '''

    def after_test(self):
        self.log.warning('Calculate the number of Pass/Fail here and generate a report.')
        test_result_dict = {}

        """
        Example:
            {'test_name': {'pass':2, 'fail':4}}
        """
        for item in self.data.test_result:
            #print item.TEST_NAME, item.TEST_PASS
            #print type(item.TEST_PASS)
            if not test_result_dict.get(item.TEST_NAME):
                test_result_dict[item.TEST_NAME] = {'pass':0, 'fail':0}
            if item.TEST_PASS == True:
                test_result_dict[item.TEST_NAME]['pass'] += 1
            else:
                test_result_dict[item.TEST_NAME]['fail'] += 1

        # table start
        HTML_RESULT = '<table id="report" class="MTBF">'
        HTML_RESULT += '<tr><th>Test Name</th><th>Iterations</th><th>PASS</th><th>FAIL</th></tr>'  # Title column

        # Different test items
        '''
        Example:
            <tr><td>Factory_Reset_Test</td><td>20</td><td>15</td><td>5</td></tr>
        '''
        total_pass = 0
        total_fail = 0
        for item in test_result_dict:
            HTML_RESULT += '<tr>'
            total_pass += test_result_dict[item]['pass']
            total_fail += test_result_dict[item]['fail']
            itr_per_item = test_result_dict[item]['pass'] + test_result_dict[item]['fail']
            HTML_RESULT += "<td>{}</td><td>{}</td><td class='pass'>{}</td><td class='fail'>{}</td>".format(item, itr_per_item, test_result_dict[item]['pass'], test_result_dict[item]['fail'])
            HTML_RESULT += '</tr>'

        # Calculate the number of total iterations after all test items are printed
        '''
        Example:
            <tr><td>Factory_Reset_Test</td><td>20</td><td>15</td><td>5</td></tr>
        '''
        HTML_RESULT += '<tr>'
        HTML_RESULT += "<td>TOTAL</td><td>{}</td><td class='pass'>{}</td><td class='fail'>{}</td>".format(total_pass+total_fail, total_pass, total_fail)
        HTML_RESULT += '</tr>'

        # table finished
        HTML_RESULT += '</table>'

        MTBF_RESULT_jenkins_property = "MTBF_RESULT={}\n".format(HTML_RESULT)
        try:
            with open('/root/app/output/MTBF_RESULT', 'w') as f:
                f.write(MTBF_RESULT_jenkins_property)
        except:
            with open('MTBF_RESULT', 'w') as f:
                f.write(MTBF_RESULT_jenkins_property)


if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** MTBF Running script ***
        Examples: ./start.sh functional_tests/MTBF.py ./run.sh  functional_tests/MTBF.py --uut_ip 10.0.0.8 --cloud_env qa1 --serial_server_ip 10.0.0.6 --serial_server_port 20000 --ap_ssid jason_5G --ap_password automation --disable_serial_server_daemon_msg --dry_run --exec_ordering "(1,0) --choice 3"
        """)

    # Test Arguments
    parser.add_argument('--version_check', help='firmware version to compare')
    parser.add_argument('--single_run', help='Run single case for Yoda BAT')
    parser.add_argument('--file_server', help='File server IP address', default='fileserver.hgst.com')

    test = MTBF(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
