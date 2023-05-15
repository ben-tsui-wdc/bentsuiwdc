# -*- coding: utf-8 -*-
""" Do basic transcoding with ffmpeg command and check the trascoding fucntion is working properly on platform side.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import os

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class BasicTranscoding(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Basic Transcoding Test'
    # Popcorn
    TEST_JIRA_ID = 'KAM-13982'
    TEST_TYPE = 'Functional'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.image_name = 'MOV_0790.mp4'
        self.media_folder = '/root/app/bat_scripts_new/media/{}'.format(self.image_name)
        self.source = '/data/wd/diskVolume0/media'
        self.destination = '/data/wd/diskVolume0/trascondig_output'
        self.ffmpeg_output = '{}/ffmpeg_output'.format(self.destination)
        self.transcoding_cmd = '/system/bin/ffmpeg  -eFps 30 -eWid 1280 -eHei 720  -re -i ' \
                               '{0}/{1} -c:a copy -c:v h264 -b:v 5500k -mediacodec_output_size 1280x720 {2}/test.mp4 > {3} 2>&1'\
                                .format(self.source, self.image_name, self.destination, self.ffmpeg_output)

    def test(self):
        model = self.uut.get('model')
        if model == 'yoda':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(model))
        else:
            self.adb.executeShellCommand('mkdir -p {0}'.format(self.source))
            self.adb.push(local=self.media_folder, remote=self.source+'/'+self.image_name, timeout=60*10)
            self.adb.executeShellCommand('mkdir -p {0}'.format(self.destination))
            check_list = ['DEC AMEDIACODEC_INFO_OUTPUT_FORMAT_CHANGED', 'frame=', 'fps=', 'speed=', 'video:', 'bitrate=', 'time=', 'Start transcoding']
            self.adb.executeShellCommand('logcat -c')
            self.log.info('Make sure there is no FFmpg process execute in background...')
            if not self.adb.wait_all_FFmpeg_finish(delay=10, timeout=60*50):
                self.log.error('Timeout waiting for FFmpeg processes finished !!!!')
            self.adb.executeShellCommand(self.transcoding_cmd, timeout=60*5)
            self.log.info('****** Print out ffmpeg output ******')
            transcoding_output = self.adb.executeShellCommand('cat {}'.format(self.ffmpeg_output))[0]
            if not all(word in transcoding_output for word in check_list):
                self.err.TestFailure('Transcoding Failed!! Check list items not exist!')

    def after_test(self):
        self.log.info('Remove {}'.format(self.destination))
        self.adb.executeShellCommand('rm -rf {}'.format(self.destination))

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Basic Transcoding Test Script ***
        Examples: ./run.sh bat_scripts/basic_transcoding.py --uut_ip 10.92.224.68\
        """)

    test = BasicTranscoding(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
