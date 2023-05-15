# -*- coding: utf-8 -*-

"""
A stress test to execute ffmpeg in parallel.ß

Pass criteria:
    1. FFMPEG always works without errors
    2. The speed is always greater than 0.95X
"""

import subprocess
import threading
import time
import sys
from multiprocessing import Process, Value

# platform modules
from ffmpeg_resolutions_stress import FFmpegResolutionsStress
from middleware.arguments import KDPInputArgumentParser


class FFmpegMultithreadStress(FFmpegResolutionsStress):

    TEST_SUITE = 'FFmpeg multithread test'
    TEST_NAME = 'FFmpeg multithread stress test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3332'
    REPORT_NAME = 'Stress'

    def declare(self):
        self.file_donwload_url = "http://10.200.141.26/test/VideoTranscoding/StressTest/"
        self.file_name = None
        self.uut_test_folder = "/data/wd/diskVolume0/"
        self.download_files = []
        self.run_tests = None
        self.print_fork_name = True
        self.running_ffmpeg = []
        self.ffmpeg_log_prefix = "ffmpeg-stderr-"
        self.single = None

    def init(self):
        if 'monarch' in self.uut['model']:
            self.run_tests = self.monarch_tests()
            self.download_files = [('1080p', 60), ('1080p', 30), ('720p', 30), ('480p', 30)]
        elif 'pelican' in self.uut['model'] or 'yoda' in self.uut['model']:
            self.run_tests = self.penlican_tests()
            self.download_files = [('4k', 60), ('1080p', 60), ('1080p', 30), ('480p', 30)]
        elif 'rocket' in self.uut['model'] or 'drax' in self.uut['model']:
            self.uut_test_folder = "/Volume1/"
            self.run_tests = self.rnd_h264_tests()
            self.download_files = [('4k', 60), ('1080pH265', 60), ('1080p', 60), ('1080p', 30), ('480p', 30)]
        else:
            raise RuntimeError('Unknown model: {}'.format(self.uut['model']))

        for file_info in self.download_files:
            self.file_name = self.get_file_name(file_info)
            self.remove_file(path='{}{}'.format(self.uut_test_folder, self.file_name))
            self.download_file(url='{}{}'.format(self.file_donwload_url, self.file_name), to=self.uut_test_folder)

    def after_loop(self):
        pass

    def test(self):
        fails = {}
        for idx, thread_tasks in enumerate(self.run_tests, 1):
            try:
                self.wait_for_ffmpeg_done()
                self.log.info('Test #{} is started...'.format(idx))
                self.multithread_test(thread_tasks)
            except Exception as e:
                self.log.error(e, exc_info=True)
                fails[idx] = e
            finally:
                self.log.info('Test #{} is done'.format(idx))
                self.log.info('='*75)
        if fails:
            raise self.err.TestFailure('Test Failed: \n{}'.format(
                '\n'.join(['Test #{}: {}'.format(idx, e) for idx, e in fails.iteritems()])))

    def multithread_test(self, thread_tasks):
        p_ffmpeg_list = []
        p_read_log_list = []
        value_list = []
        speed_result_list = []
        is_failing_test_pass = True
        self.running_ffmpeg = []
        
        for idx, test_info in enumerate(thread_tasks, 1):
            self.log.info(self.task_description(idx, test_info))

            width, hight = self.get_transcode_settings(test_info['target'][0])

            # Process 1: trigger ffmpeg
            command = self.ffmpeg_cmd(
                file_path='{}{}'.format(self.uut_test_folder, self.get_file_name(test_info['src'])),output_url=self.output_url,
                start_time=0, width=width, hight=hight, fps=test_info['target'][1])
            execute_ffmpeg = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if idx == len(thread_tasks):  # failing process check
                stdout, stderr = execute_ffmpeg.communicate()
                self.log.info('stdout: \n{}'.format(stdout))
                self.log.info('stderr: \n{}'.format(stderr))
                if "Please wait until current transcoding finished" not in stderr and "Reach maximum job limitaion" not in stderr:
                    is_failing_test_pass = False
                    self.log.error('Hit an error, check by ps')
                    self.ssh_client.is_any_FFmpeg_running_kdp()
            else:
                p_ffmpeg = threading.Thread(target=self._get_process_output, args=(execute_ffmpeg,))
                p_ffmpeg.daemon = True
                #p_ffmpeg = Process(target=self._get_process_output, args=(execute_ffmpeg,))
                p_ffmpeg_list.append(p_ffmpeg)
                p_ffmpeg.start()
                time.sleep(3)

                # Process 2: polling "tail -n 1 /tmp/ffmpeg.stderr.$PID"
                # Shared value for getting speed result from forked process
                speed = Value('d')
                value_list.append(speed)
                p_read_log = threading.Thread(target=self._query_ffmpeg_log, args=(0, speed, "ssh_client-Thread#{}".format(idx),))
                p_read_log.daemon = True
                #p_read_log = Process(target=self._query_ffmpeg_log, args=(0, speed,))
                p_read_log_list.append(p_read_log)
                p_read_log.start()

                # Wait for the process start for making sure test script can get correct PID.
                wait_timeout = 45  # found case may take ~30 secs to establish SSH connection.
                wait_start = time.time()
                while len(self.running_ffmpeg) != idx:
                    if time.time() - wait_start >= wait_timeout:
                        raise self.err.TestError('Wait timeout {}s for FFmpeg start'.format(wait_timeout))
                    self.log.info('Wait for FFmpeg start... Running PID: {}'.format(self.running_ffmpeg))
                    time.sleep(3)
                self.log.info('FFmpeg started, running PID: {}'.format(self.running_ffmpeg))


        for p_ffmpeg in p_ffmpeg_list:
            p_ffmpeg.join()
        for p_read_log in p_read_log_list:
            p_read_log.join()
        for speed in value_list:
            speed_result_list.append(speed.value)
        if not is_failing_test_pass:
            raise self.err.TestError("The message from {}th FFmpeg thread is not as expected".format(len(thread_tasks)))
        self.test_summary(speed_result_list, thread_tasks)

    def test_summary(self, speed_result_list, thread_tasks):
        if not speed_result_list:
            raise self.err.TestFailure("There is no any transcoding video speed.")
        # pass criteria: transcoding speed must > 0.95X
        for idx, speed in enumerate(speed_result_list):
            if float(speed) == 0:
                raise self.err.TestFailure("Transcoding speed is 0X for {}!".format(self.task_description(idx, thread_tasks[idx])))
            elif float(speed) < 0.95:
                raise self.err.TestFailure("Transcoding speed({}X) < 0.95X for {}!".format(speed, self.task_description(idx, thread_tasks[idx])))
    
        average_speed = round(sum(speed_result_list) / len(speed_result_list), 2)
        self.log.info('Total transcoding average speed: {}X for all video'.format(average_speed))
        #self.data.test_result['FFmpegtressSpeed'] = average_speed

    def task_description(self, idx, test_info):
        return 'Thread#{} - Source: {}/{}fps -> Target: {}/{}fps'.format(
            idx, test_info['src'][0], test_info['src'][1], test_info['target'][0], test_info['target'][1])

    def wait_for_ffmpeg_done(self, timeout=60*5):
        start_time = time.time()
        while self.ssh_client.is_any_FFmpeg_running_kdp(ignore_zombie=True):
            if time.time() - start_time >= timeout:
                self.log.warning('Timeout of waiting: {}s'.format(timeout))
                raise self.err.TestFailure('FFmpeg prcoess is running on device')
            self.log.info('wait for ffmpeg done...')
            time.sleep(15)
        self.log.info('No Fmmpeg prcoess is running')

    def get_file_name(self, file_info):
        return {
            ('4k', 60): 'H265_4K_60FPS_MAIN@L51_300S.mkv',
            ('1080pH265', 60): 'H265_1080P_60FPS_MAIN@L41_300S.mkv',
            ('1080p', 60): 'H264_1080P_60FPS_MAIN@L42_300S.mkv',
            ('1080p', 30): 'H264_1080P_30FPS_MAIN@L42_300S.mkv',
            ('720p', 30): 'H264_720P_30FPS_MAIN@L31_300S.mkv',
            ('480p', 30): 'H264_480P_30FPS_MAIN@L3_300S.mkv'
        }.get(file_info)

    def monarch_tests(self):
        if self.single:
            return [
                [
                    {'src': ('1080p', 60), 'target': ('1080p', 30)},
                    {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
                ]
            ]
        return [
            [
                {'src': ('1080p', 60), 'target': ('1080p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ],
            [
                {'src': ('1080p', 30), 'target': ('1080p', 30)},
                {'src': ('720p', 30), 'target': ('720p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ],
            [
                {'src': ('480p', 30), 'target': ('480p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ]
        ]

    def penlican_tests(self):
        if self.single:
            return [
                [
                    {'src': ('4k', 60), 'target': ('1080p', 30)},
                    {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
                ]
            ]
        return [
            [
                {'src': ('4k', 60), 'target': ('1080p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ],
            [
                {'src': ('1080p', 60), 'target': ('1080p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ],
            [
                {'src': ('1080p', 30), 'target': ('720p', 30)},
                {'src': ('1080p', 30), 'target': ('720p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ],
            [
                {'src': ('480p', 30), 'target': ('480p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ]
        ]

    def rnd_h264_tests(self):
        if self.single:
            return [
                [
                    {'src': ('4k', 60), 'target': ('1080p', 30)},
                    {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
                ]
            ]
        return [
            [
                {'src': ('4k', 60), 'target': ('1080p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ],
            [
                {'src': ('1080p', 60), 'target': ('1080p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ],
            [
                {'src': ('1080pH265', 60), 'target': ('1080p', 30)},
                {'src': ('1080pH265', 60), 'target': ('1080p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ],
            [
                {'src': ('1080p', 30), 'target': ('720p', 30)},
                {'src': ('1080p', 30), 'target': ('720p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ],
            [
                {'src': ('480p', 30), 'target': ('480p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)},
                {'src': ('480p', 30), 'target': ('480p', 30)} # over limit
            ]
        ]


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** FFmpeg multithread stress test on KDP Linux ***
        """)

    parser.add_argument('--file_donwload_url', help='specify the url where testing video file could be downloaded.', \
                        default="http://10.200.141.26/test/VideoTranscoding/StressTest/")
    parser.add_argument('--output_url', help='Which client the FFmpeg send UDP output to', default='udp://127.0.0.1:9999')
    parser.add_argument('--single', help='Run single case', action='store_true', default=False)

    test = FFmpegMultithreadStress(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
