# -*- coding: utf-8 -*-

"""
A stress test to execute ffmpeg and change resolution every 30 secs

Pass criteria:
    1. FFMPEG always works without errors
    2. Current playing time is greater than the start time we specified
    3. The speed is always greater than 1X
"""

import subprocess
import time
import sys
from multiprocessing import Process, Value

# platform modules
from ffmpeg_stress import FFmpegStress
from middleware.arguments import KDPInputArgumentParser


class FFmpegResolutionsStress(FFmpegStress):

    TEST_SUITE = 'FFmpeg change resolution stress test'
    TEST_NAME = 'FFmpeg change resolution stress test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3251'
    REPORT_NAME = 'Stress'

    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True
    }

    def declare(self):
        self.file_donwload_url = "http://10.200.141.26/test/VideoTranscoding/FullRegression/202105/v3.2/300s/"
        self.file_name_4k = "H265_4K_30FPS_MAIN@L5_300S.mkv"
        self.file_name_1080p = "H264_1080P_60FPS_MAIN@L42_300S.mkv"
        self.file_name = None
        self.uut_test_folder = "/data/wd/diskVolume0/"
        self.video_duration = 300
        self.test_interval = 30
        self.print_fork_name = False
        self.running_ffmpeg = None
        self.ffmpeg_log_prefix = "ffmpeg-stderr-"
        self.force_1080p = False

    def init(self):
        if self.force_1080p or 'monarch' in self.uut['model']:
            self.resolutions = ['1080p', '720p', '480p']
            self.file_name = self.file_name_1080p
        elif 'pelican' in self.uut['model'] or 'yoda' in self.uut['model']:
            self.resolutions = ['1080p', '720p', '480p']
            self.file_name = self.file_name_4k
        elif 'rocket' in self.uut['model'] or 'drax' in self.uut['model']:
            self.uut_test_folder = "/Volume1/"
            self.resolutions = ['1080p', '720p', '480p']
            self.file_name = self.file_name_4k
        else:
            raise RuntimeError('Unknown model: {}'.format(self.uut['model']))

        self.remove_file(path='{}{}'.format(self.uut_test_folder, self.file_name))
        self.download_file(url='{}{}'.format(self.file_donwload_url, self.file_name), to=self.uut_test_folder)

    def before_loop(self):
        pass

    def test(self):
        speed_result_list = []
        start_times = []

        for idx in xrange(int(round(self.video_duration/self.test_interval))):
            self.exist_ffmpeg_check()

            res_idx = idx % len(self.resolutions)
            resolution = self.resolutions[res_idx]
            res_setting = self.get_transcode_settings(resolution)
            start_time = self.test_interval * idx
            start_times.append(start_time)

            self.log.info('*** Starting FFmpeg to H.264 {} from {}s for {}s ***'.format(resolution, start_time, self.test_interval))

            try:
                # Read log first in case the transcoding is too fast
                # Process 1: polling "tail -n 1 /tmp/ffmpeg.stderr.$PID"
                # Shared value for getting speed result from forked process
                speed = Value('d')
                t_read_log = Process(target=self._query_ffmpeg_log, args=(start_time, speed,))
                t_read_log.start()
                time.sleep(3)

                # Process 2: trigger ffmpeg
                command = self.ffmpeg_cmd(
                    file_path='{}{}'.format(self.uut_test_folder, self.file_name), output_url=self.output_url,
                    start_time=start_time, play_duration=self.test_interval, width=res_setting[0], hight=res_setting[1], fps='30')
                execute_ffmpeg = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                t_ffmpeg = Process(target=self._get_process_output, args=(execute_ffmpeg,))
                t_ffmpeg.start()
                t_ffmpeg.join()
                t_read_log.join()

                speed_result_list.append(speed.value)

            except Exception as e:
                self.log.error('FFmpeg stress test failed by exception, error message: {}'.format(e), exc_info=True)
                raise
        self.test_summary(speed_result_list, start_times)

    def get_transcode_settings(self, resolution):
        return {
            '1080p': (1920, 1080),
            '720p': (1280, 720),
            '480p': (720, 480),
            '360p': (480, 360)
        }[resolution]

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** FFmpeg starting time stress test on KDP Linux ***
        """)

    parser.add_argument('--file_donwload_url', help='specify the url where testing video file could be downloaded.', \
                        default="http://10.200.141.26/test/VideoTranscoding/FullRegression/202105/v3.2/300s/")
    parser.add_argument('--output_url', help='Which client the FFmpeg send UDP output to', default='udp://127.0.0.1:9999')
    parser.add_argument('--force_1080p', help='Force to run 1080p case', action='store_true', default=False)

    test = FFmpegResolutionsStress(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
