# -*- coding: utf-8 -*-

"""
A stress test to execute ffmpeg with specified starting time: 60->180->120 seconds

Pass criteria:
    1. FFMPEG always works without errors
    2. Current playing time is greater than the start time we specified
    3. The speed is always greater than 1X
"""

__author__ = "Ben Tsui <ben.tsui@wdc.com>"
__author_2__ = "Jason Chiang <jason.chiang@wdc.com>"
__author_3__ = "Estvan Huang <estvan.huang@wdc.com>"
__compatible__ = 'KDP,RnD'

import datetime
import re
import subprocess
import sys
import time
import threading

from multiprocessing import Process, Value

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.ssh_client import SSHClient
from platform_libraries.constants import SSH_KEY
from platform_libraries.common_utils import create_logger


class FFmpegStress(KDPTestCase):

    TEST_SUITE = 'FFmpeg staring time test'
    TEST_NAME = 'FFmpeg staring time stress test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-612'
    REPORT_NAME = 'Stress'

    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True
    }


    def declare(self):
        self.file_donwload_url = "http://fileserver.hgst.com/test/FFmpegStress/"
        self.file_name = "1080P_H264_AAC_30FPS.mkv"
        self.play_duration = 60
        self.output_url = 'udp://127.0.0.1:9999'
        self.uut_test_folder = "/data/wd/diskVolume0/"
        self.start_time = [60,120,180]
        self.print_fork_name = False
        self.running_ffmpeg = None
        self.ffmpeg_log_prefix = "ffmpeg-stderr-"

    def init(self):
        pass

    def before_loop(self):
        self.download_file(url='{}{}'.format(self.file_donwload_url, self.file_name), to=self.uut_test_folder)

    def before_test(self):
        pass

    def test(self):
        speed_result_list = []

        for start_time in self.start_time:
            #self.log.info('Starting FFmpeg from: {} seconds, will be played for {} seconds'.
            #              format(start_time, self.play_duration))
            self.log.info('Starting FFmpeg from: {} seconds, will play whole video'.format(start_time))
            """
                We can use 'ps | grep ffmpeg' to check FFmpeg is running or not.
                If there is more than 1 process in Monarch or 2 processes in Pelican,
                it might cause problem if we try to create another FFmpeg process.
            """
            self.exist_ffmpeg_check()

            try:
                # Process 1: trigger ffmpeg
                command = self.ffmpeg_cmd(
                    file_path='{}{}'.format(self.uut_test_folder, self.file_name), output_url=self.output_url,
                    start_time=start_time)
                p_execute_ffmpeg = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                p1 = Process(target=self._get_process_output, args=(p_execute_ffmpeg,))
                p1.start()
                time.sleep(3)

                # Process 2: polling "tail -n 1 /tmp/ffmpeg.stderr.$PID"
                # Shared value for getting speed result from forked process
                speed = Value('d')
                p2 = Process(target=self._query_ffmpeg_log, args=(start_time, speed,))
                p2.start()

                # Quit process after specified time
                #time.sleep(float(self.play_duration))
                """
                    Use kill -15 {ffmpeg_pid} to stop ffmpeg process instead of using python kill method.
                    Python kill method will send SIGKIL signal (same as kill -9) and might cause error.
                    The ffmpeg process output:
                    root      25473 25467 109076 26624 futex_wait f71b3780 S /system/bin/ffmpeg
                """
                # p.kill()
                '''
                stdout, stderr = self.ssh_client.execute_cmd('ps | grep ffmpeg')
                if stdout:
                    for line in stdout.splitlines():
                        if '/usr/local/modules/usr/bin/ffmpeg' in line:
                            self.log.info('FFmpeg process status: {}'.format(line))
                            ffmpeg_pid = line.split()[0]
                            self.log.info('FFmpeg pid: {}'.format(ffmpeg_pid))
                            stdout, stderr = self.ssh_client.execute_cmd('kill -15 {}'.format(ffmpeg_pid))
                            # 13,21,22
                            break
                else:
                    self.log.warning('Cannot get FFmpeg process information, check stderr: {}'.format(stderr))
                '''
                p1.join()
                p2.join()
                speed_result_list.append(speed.value)

            except Exception as e:
                self.log.error('FFmpeg stress test failed by exception, error message: {}'.format(e))
                raise
        self.test_summary(speed_result_list, self.start_time)


    def test_summary(self, speed_result_list, start_times):
        # The speed result will be in list format like: [12.85, 7.93, 17.94]
        # Set test result to Failed if any one of the speed is 0X
        if not speed_result_list:
            raise self.err.TestFailure("There is no any transcoding video speed.")
        # pass criteria: transcoding speed must > 0.95X
        for i, speed in enumerate(speed_result_list):
            if float(speed) == 0:
                raise self.err.TestFailure("Transcoding speed is 0X for video start time: {}s!".format(start_times[i]))
            elif float(speed) < 0.95:
                raise self.err.TestFailure("Transcoding speed({}X) < 0.95X for video start time: {}s!".format(speed, start_times[i]))
    
        average_speed = round(sum(speed_result_list) / len(speed_result_list), 2)
        self.log.info('Total transcoding average speed: {}X for all video start times: {} sec'.format(average_speed, start_times))
        self.data.test_result['FFmpegtressSpeed'] = average_speed


    def after_test(self):
        pass

    def after_loop(self):
        # Remove testing video
        self.remove_file(path='{}{}'.format(self.uut_test_folder, self.file_name))

    def download_file(self, url, to):
        #  wget http://fileserver.hgst.com/test/FFmpegStress/1080P_H264_AAC_30FPS.mkv -P /data/wd/diskVolume0
        exit_status, output = self.ssh_client.execute('wget {} -P {} --quiet'.format(url, to), timeout=300)
        if exit_status != 0:
            raise self.err.StopTest("Testing video file is not downloaded successfully.")

    def remove_file(self, path):
        stdout, stderr = self.ssh_client.execute_cmd('test -e {0} && rm {0}'.format(path), timeout=300)

    def exist_ffmpeg_check(self):
        self.log.info('Checking if FFmpeg was started by anyone else')
        stdout, stderr = self.ssh_client.execute_cmd('ps | grep ffmpeg')
        if any('grep' not in line and 'ffmpeg' in line for line in stdout.splitlines()):
            #if 'grep ffmpeg' not in line:  # Ignore "grep ffmpeg"
            #    if "ffmpeg" in line:
            raise self.err.StopTest('There is already a FFmpeg process exists: {}'.format(stdout))
        else:
            self.log.info('No one is running FFmpeg, start the test')

    def ffmpeg_cmd(self, file_path, output_url, start_time, play_duration=None, width='1280', hight='720', fps='30'):
        ssh_prefix = 'ssh -i {} -o StrictHostKeyChecking=no root@{} '.format(SSH_KEY, self.env.uut_ip)
        duration_arg = '-t {}'.format(play_duration) if play_duration else ''
        # -t (before -i) is limit the duration of data read from the input file.
        # -t (after -i) is stop writing the output after its duration reaches duration.
        command = ssh_prefix + 'ffmpeg -ss {} {} -eFps {} -eWid {} -eHei {} '.format(start_time, duration_arg, fps, width, hight) + \
                  '-i "{}" '.format(file_path) + \
                  '-c:a copy -c:v h264 -b:v 5500k -mediacodec_output_size {}x{} '.format(width, hight) + \
                  '-f mpegts -copyts {}'.format(output_url)
        self.log.info(command)
        return command

    def _get_process_output(self, process):
        stdout, stderr = process.communicate()
        self.log.info('\n######   Transcoding final result (stderr): \n{}'.format(stderr))
        if "failed" in stderr or "Failed" in stderr:
            raise self.err.TestFailure('Find error message from FFmpeg command')
        if not stderr:
            raise self.err.TestFailure('There is no outputs(stderr) from FFmpeg command!')
        #output = stderr.splitlines()
        #output[-1].strip()

    def _query_ffmpeg_log(self, start_time, speed, thread_name=None):
        ssh_client = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        ssh_client.log = create_logger(log_name=thread_name if thread_name else "ssh_client#fork")
        ssh_client.connect()

        ffmpeg_pid = None
        for idx in xrange(15):
            ffmpeg_filters = ' | grep -v ' + ' | grep -v '.join(self.running_ffmpeg) if self.running_ffmpeg else ''
            stdout, stderr = ssh_client.execute_cmd('ps | grep ffmpeg | grep -v grep' + ffmpeg_filters)
            for line in stdout.splitlines():
                if '/usr/sbin/ffmpeg' in line:
                    ssh_client.log.info('FFmpeg wrapper process status: {}'.format(line))
                    ffmpeg_pid = line.split()[0]
                    if self.running_ffmpeg is None or ffmpeg_pid not in self.running_ffmpeg: 
                        ssh_client.log.info('FFmpeg wrapper pid: {}'.format(ffmpeg_pid))
                        if self.running_ffmpeg is not None:
                            self.running_ffmpeg.append(ffmpeg_pid)
                            ssh_client.log.info('FFmpeg wrapper pid is appended')
                        break
            if ffmpeg_pid:
                break
            else:
                time.sleep(1)
        if not ffmpeg_pid:
            raise self.err.TestFailure("There is no any ffmpeg process running.")
        speed.value = self._get_avg_speed_from_ffmpeg_log(ssh_client, ffmpeg_pid, start_time)

    def fork_name(self):
        if self.print_fork_name:
            return threading.current_thread().name + ': '
        return ''

    def _get_avg_speed_from_ffmpeg_log(self, ssh_client, ffmpeg_pid, start_time, read_timeout=600):
        fork_name = self.fork_name()
        beginning_time = time.time()
        total_ffmpeg_stdout_output = []
        ssh_client.log.info('{}Reading ffmpeg log'.format(fork_name))
        log_file = '/tmp/{}{}'.format(self.ffmpeg_log_prefix, ffmpeg_pid)
        log_found = False
        find_log_retry_times = 5
        while True:
            stdout, stderr = ssh_client.execute_cmd('tail -n 1 {}'.format(log_file), quiet=True)
            if "No such file or directory" in stderr:
                if log_found:
                    ssh_client.log.info('{} is removed by wrapper'.format(log_file))
                    break
                ssh_client.log.info('{} not found'.format(log_file))
                if find_log_retry_times > 0:
                    find_log_retry_times -= 1
                    time.sleep(1)
                    stdout, stderr = ssh_client.execute_cmd('ps | grep ff | grep -v grep', quiet=True)
                    ssh_client.log.info('Running process:\n{}'.format(stdout))
                    ssh_client.log.info('Retrying to read log')
                else:
                    break
            elif time.time() - beginning_time >= read_timeout:
                ssh_client.log.warning('Checking FFmpeg status')
                ssh_client.execute_cmd('ps | grep ff | grep -v grep', quiet=False)
                ssh_client.execute_cmd('ls -al /tmp', quiet=False)  # check log file status
                raise self.err.TestError("/tmp/{}{} keeps displaying log more than {} seconds!".format(self.ffmpeg_log_prefix, ffmpeg_pid, read_timeout))
            else:
                log_found = True
                if 'frame' not in stdout:
                    ssh_client.log.warning('{}Unexpected output: {}'.format(fork_name, stdout))
                last_row = stdout[stdout.rfind('frame'):].strip() # May contain more than 1 progress log, fix me if need.
                if last_row in total_ffmpeg_stdout_output:
                    ssh_client.log.info('{}Not new status, skip this line: {}'.format(fork_name, last_row))
                else:
                    ssh_client.log.info('{}{}'.format(fork_name, last_row))
                    total_ffmpeg_stdout_output.append(last_row)
        if total_ffmpeg_stdout_output:
            return self._parser_ffmpeg_result(total_ffmpeg_stdout_output, start_time, ssh_client.log)
        else:
            raise self.err.TestError('{}There is no speed information from /tmp/{}{}'.format(fork_name, self.ffmpeg_log_prefix, ffmpeg_pid))

    def _parser_ffmpeg_result(self, output, start_time, logger):
        """
        The FFmpeg output will be looked like:
        frame=   77 fps= 51 q=-0.0 size=    1840kB time=00:00:36.07 bitrate= 417.8kbits/s speed=23.7x
        """
        fork_name = self.fork_name()
        check_field = ['time', 'speed']
        speed_list = []
        check_speed_flag = False
        for line in output:
            if all(field in line for field in check_field):
                pattern = re.compile(r'(.+time=)(.+)(bitrate=.+speed=)(.+)(x)')
                match = pattern.match(line)
                play_time = match.group(2)
                speed = float(match.group(4))
                
                # Convert the play_time into seconds
                t = time.strptime(play_time.split('.')[0], '%H:%M:%S')
                current_time = datetime.timedelta(hours=t.tm_hour, minutes=t.tm_min, seconds=t.tm_sec).total_seconds()

                # Due to KDP-1908
                # Modify following script part
                '''
                if current_time < start_time:
                    self.log.error('Current time: {0}s is lesser than the time specified: {1}s'.format(current_time, start_time))
                else:
                    self.log.debug('Current time: {0}s is greater than: {1}s as expected'.format(current_time, start_time))
                '''
                if not check_speed_flag:
                    if speed <= 0:
                        continue
                    elif speed > 0:
                        check_speed_flag = True
                if check_speed_flag:
                    if speed <= 0:
                        logger.error('{}The transcoding speed: {}X is lesser than 0X'.format(fork_name, speed))
                        speed_list = []
                        break
                    else:
                        logger.debug('{}Speed: {}X is greater than: 0X as expected'.format(fork_name, speed))
                        speed_list.append(speed)

        if speed_list:
            # The transcoding speed at the beginning will be much higher than average value,
            # so remove the first 1/3 data and use the rest 2/3 to calculate average speed
            for i in range((len(speed_list)+1)/3):
                speed_list.pop(0)
            average_speed = round(sum(speed_list) / len(speed_list), 2)
        else:
            logger.error('{}There are no speed information from stderr output or transccoding speed is not as expected.'.format(fork_name))
            average_speed = 0

        logger.info('{}Transcoding average speed: {}X for video start_time[{}]sec'.format(fork_name, average_speed, start_time))
        return average_speed


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** FFmpeg starting time stress test on KDP Linux ***
        """)

    parser.add_argument('--file_donwload_url', help='specify the url where testing video file could be downloaded.', \
                        default="http://fileserver.hgst.com/test/FFmpegStress/")
    parser.add_argument('--file_name', help='testing video file name', default='1080P_H264_AAC_30FPS.mkv')
    parser.add_argument('--play_duration', help='How many seconds to play the video', default=60)
    parser.add_argument('--output_url', help='Which client the FFmpeg send UDP output to', default='udp://127.0.0.1:9999')



    test = FFmpegStress(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)