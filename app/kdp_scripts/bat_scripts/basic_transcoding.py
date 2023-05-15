# -*- coding: utf-8 -*-
""" Do basic transcoding with ffmpeg command and check the transcoding function is working properly on platform side.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP


class BasicTranscoding(KDPTestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'KDP-209 - Basic Transcoding Test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-209'
    TEST_TYPE = 'Functional'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        data_vol_path = KDP.DATA_VOLUME_PATH[self.uut.get('model')]
        self.image_name = 'MOV_0790.mp4'
        self.local_media_path = '/root/app/bat_scripts_new/media/{}'.format(self.image_name)
        self.src_root_path = '{}/media'.format(data_vol_path)
        self.src_media_path = '{}/{}'.format(self.src_root_path, self.image_name)
        self.dest_root_path = '{}/transcoding_output'.format(data_vol_path)
        self.ffmpeg_output_path = '{}/ffmpeg_output'.format(self.dest_root_path)
        self.transcoding_cmd = 'ffmpeg  -eFps 30 -eWid 1280 -eHei 720 -i {} ' \
            '-c:a copy -c:v h264 -b:v 5500k -mediacodec_output_size 1280x720 {}/test.mp4 > {} 2>&1' \
            .format(self.src_media_path, self.dest_root_path, self.ffmpeg_output_path)

    def test(self):
        self.log.info('Creating source folder')
        exitcode, _ = self.ssh_client.execute('mkdir -p {}'.format(self.src_root_path))
        assert exitcode == 0, 'Failed to create {}'.format(self.src_root_path)

        self.log.info('Coying test media')
        self.ssh_client.scp_connect()
        self.ssh_client.scp_upload(localpath=self.local_media_path, remotepath=self.src_media_path)

        self.log.info('Creating destination folder')
        exitcode, _ = self.ssh_client.execute('mkdir -p {0}'.format(self.dest_root_path))
        assert exitcode == 0, 'Failed to create {}'.format(self.dest_root_path)

        self.log.info('Make sure there is no FFmpeg process execute in background...')
        if not self.ssh_client.wait_all_FFmpeg_finish(
                delay=10, timeout=60*50, check_func=self.ssh_client.is_any_FFmpeg_running_kdp):
            self.log.error('Timeout waiting for FFmpeg processes finished !!!!')

        exitcode, _ = self.ssh_client.execute(self.transcoding_cmd, timeout=60*5)
        assert exitcode == 0, 'Failed to execute FFmpeg'

        self.log.info('****** Print out ffmpeg output ******')
        check_list = ['speed', 'total_time', 'cmd']
        exitcode, output = self.ssh_client.execute('cat {}'.format(self.ffmpeg_output_path))
        if not all(word in output for word in check_list):
            self.err.TestFailure('Transcoding Failed!! Check list items not exist!')
        assert 'failed' not in output, 'Found "failed" message in output'

    def after_test(self):
        self.log.info('Removing test data')
        self.ssh_client.execute('test -e {0} && rm -rf {0}'.format(self.src_root_path))
        self.ssh_client.execute('test -e {0} && rm -rf {0}'.format(self.dest_root_path))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Basic Transcoding Test Script ***
        Examples: ./run.sh bat_scripts/basic_transcoding.py --uut_ip 10.92.224.68\
        """)

    test = BasicTranscoding(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
