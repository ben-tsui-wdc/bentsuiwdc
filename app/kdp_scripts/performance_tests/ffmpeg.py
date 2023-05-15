# -*- coding: utf-8 -*-

"""
Trigger ffmpeg to get transcoding speed and transcoding total_time.


"""

__author__ = "Ben Tsui <ben.tsui@wdc.com>"
__author_2__ = "Jason Chiang <jason.chiang@wdc.com>"

import ctypes
import datetime
import json
import re
import subprocess
import sys
import time


from multiprocessing import Process, Value

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.ssh_client import SSHClient
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat

class FFmpegStress(KDPTestCase):

    TEST_SUITE = 'FFmpeg transcoding speed and total_time test'
    TEST_NAME = 'FFmpeg transcoding speed and total_time test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-612'
    REPORT_NAME = 'Stress'

    SETTINGS = {
        'uut_owner': False,
        'ssh_client': True
    }


    def declare(self):
        self.test_result_list = []
        self.html_format = '2'
        self.html_format = '2'
        self.file_donwload_url = "http://fileserver.hgst.com/test/VideoTranscoding/FullRegression/202105/v3.1/300s/"
        self.file_name = "H264_1080P_60FPS_BASELINE@L32_300S.mkv"
        self.ffmpeg_result = 'ffmpeg_result'
        self.ffmpeg_timeout = 900
        self.mem_list = []

    def init(self):
        pass

    def before_loop(self):
        if self.uut.get('model') in ['rocket', 'drax']:
            self.uut_test_folder = "/Volume1/"
        elif self.uut.get('model') in ['monarch2', 'pelican2', 'yodaplus2']:
            self.uut_test_folder = "/data/wd/diskVolume0/"
        # Remove testing video
        stdout, stderr = self.ssh_client.execute_cmd('rm {}{}'.format(self.uut_test_folder, self.file_name), timeout=300)
        #  wget http://fileserver.hgst.com/test/FFmpegStress/1080P_H264_AAC_30FPS.mkv -P /data/wd/diskVolume0
        exit_status, output = self.ssh_client.execute('wget {}{} -P {} --quiet'.format(self.file_donwload_url, self.file_name.replace('@', '%40'), self.uut_test_folder), timeout=600)
        if exit_status != 0:
            raise self.err.StopTest("Testing video file is not downloaded successfully.")

    def before_test(self):
        # Remove ffmpeg_result
        stdout, stderr = self.ssh_client.execute_cmd('rm -f {}{}'.format(self.uut_test_folder, self.ffmpeg_result), timeout=60)

    def test(self):
        speed_result_list = []
        self.log.info('Start FFmpeg and will play whole video')
        self.log.info('Checking if FFmpeg was started by anyone else')
        stdout, stderr = self.ssh_client.execute_cmd('ps | grep ffmpeg')
        if any('grep' not in line and 'ffmpeg' in line for line in stdout.splitlines()):
            #if 'grep ffmpeg' not in line:  # Ignore "grep ffmpeg"
            #    if "ffmpeg" in line:
            raise self.err.StopTest('There is already a FFmpeg process exists: {}'.format(stdout))
        else:
            self.log.info('No one is running FFmpeg, start the test')

        command = 'nohup ' +'ffmpeg ' +  ' -eFps 30 -eWid 1280 -eHei 720 ' + \
                  '-i {0}{1} '.format(self.uut_test_folder, self.file_name) + \
                  '-c:a copy -c:v h264 -b:v 5500k -mediacodec_output_size 1280x720 ' + \
                  '-f mpegts -copyts {} >/dev/null 2>{}{} &'.format(self.output_url, self.uut_test_folder, self.ffmpeg_result)
        stdout, stderr = self.ssh_client.execute_cmd(command, timeout=1)
        # Polling ffmpeg by "ps"
        start_time = time.time()
        time.sleep(5)  # Wait for starting ffmpeg 
        while time.time() - start_time < self.ffmpeg_timeout:
            stdout, stderr = self.ssh_client.execute_cmd('top -n 1 | grep ffmpeg | grep -v grep')
            if stdout:
                mem = stdout.split()[4].split('m')[0]  # memory usage: VSZ
                self.mem_list.append(int(mem))
            else:
                self.log.info('The ffmpeg finished.')
                break
            time.sleep(10)
        if time.time() - start_time > self.ffmpeg_timeout:
            raise self.err.TestError('The ffmpeg doesn\'t complete in {} seconds.'.format(self.ffmpeg_timeout))
        if not self.mem_list:
            raise self.err.TestError("There is no memory usage by ffmpeg!")
        # Check ffmpeg_result
        stdout, stderr = self.ssh_client.execute_cmd('cat {}{}'.format(self.uut_test_folder, self.ffmpeg_result), timeout=30)
        if not stdout:
            raise self.err.TestFailure('There is no output from {}{}!'.format(self.uut_test_folder, self.ffmpeg_result))
        output = stdout.splitlines()
        ffmpeg_result = json.loads(output[-1].strip())
        print "\n#### ffmpeg_result ####\n"
        print ffmpeg_result
        print "\n#### ffmpeg_result ####\n"
        transcoding_speed = ffmpeg_result.get('speed').strip().split('x')[0]
        transcoding_total_time = ffmpeg_result.get('total_time').strip()
        # Convert the transcoding_total_time into seconds
        t = time.strptime(transcoding_total_time.split('.')[0], '%H:%M:%S')
        transcoding_total_time_sec = datetime.timedelta(hours=t.tm_hour, minutes=t.tm_min, seconds=t.tm_sec).total_seconds()
        # Check self.mem_list
        self.log.warning(self.mem_list)
        mem_max = max(self.mem_list)
        mem_min = min(self.mem_list)
        mem_avg = float(sum(self.mem_list))/float(len(self.mem_list))
        self.log.warning('Meomory Usage (VSZ) Max: {}'.format(mem_max))
        self.log.warning('Meomory Usage (VSZ) Min: {}'.format(mem_min))
        self.log.warning('Meomory Usage (VSZ) Avg: {}'.format(mem_avg))


        self.data.test_result['video'] = self.file_name
        self.data.test_result['transcoding_speed_avg'] = transcoding_speed
        self.data.test_result['transcoding_total_time_avg'] = transcoding_total_time_sec
        self.data.test_result['transcoding_speed_unit'] = 'x'
        self.data.test_result['transcoding_total_time_unit'] = 'sec'
        self.data.test_result['mem_max_avg'] = mem_max
        self.data.test_result['mem_max_unit'] = 'm'
        self.data.test_result['mem_min_avg'] = mem_min
        self.data.test_result['mem_min_unit'] = 'm' 
        self.data.test_result['mem_avg_avg'] = mem_avg
        self.data.test_result['mem_avg_unit'] = 'm'
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # millisecond

    def after_test(self):
        self.test_result_list.append(self.data.test_result)
        # Remove ffmpeg_result
        stdout, stderr = self.ssh_client.execute_cmd('rm -f {}{}'.format(self.uut_test_folder, self.ffmpeg_result), timeout=60)

    def after_loop(self):
        # Remove testing video
        stdout, stderr = self.ssh_client.execute_cmd('rm {}{}'.format(self.uut_test_folder, self.file_name), timeout=300)

        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'video', 'transcoding_speed_avg', 'transcoding_speed_unit', 'transcoding_total_time_avg', 'transcoding_total_time_unit', 'mem_max_avg', 'mem_max_unit', 'mem_min_avg', 'mem_min_unit', 'mem_avg_avg', 'mem_avg_unit']
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'build', 'video', 'transcoding_speed_avg', 'transcoding_speed_unit', 'transcoding_total_time_avg', 'transcoding_total_time_unit', 'mem_max_avg', 'mem_max_unit', 'mem_min_avg', 'mem_min_unit', 'mem_avg_avg', 'mem_avg_unit', 'count', 'executionTime']
        csv_inst.csv_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # Determine if the test is passed or not.
        if not pass_status_summary:
            '''
            # Workaround for popcorn report
            import copy
            result_fake = copy.deepcopy(self.data.loop_results[-1])
            result_fake.TEST_PASS = False
            result_fake['failure_message'] = "At leaset one value doesn't meet the target/pass criteria."
            result_fake.POPCORN_RESULT["result"] = "FAILED"
            result_fake.POPCORN_RESULT["error"] = "At leaset one value doesn't meet the target/pass criteria."
            result_fake.POPCORN_RESULT["start"] = result_fake.POPCORN_RESULT["start"] + 2
            result_fake.POPCORN_RESULT["end"] = result_fake.POPCORN_RESULT["end"] + 3
            self.data.loop_results.append(result_fake)
            '''
            raise self.err.TestFailure("At leaset one value doesn't meet the target/pass criteria.")

    def _query_ffmpeg_log(self, speed):

        self.ssh_client_2 = SSHClient(self.env.uut_ip, self.env.ssh_user, self.env.ssh_password)
        self.ssh_client_2.connect()

        stdout, stderr = self.ssh_client_2.execute_cmd('ps | grep ffmpeg')
        if stdout:
            for line in stdout.splitlines():
                if '/usr/sbin/ffmpeg' in line:
                    self.log.info('FFmpeg wrapper process status: {}'.format(line))
                    ffmpeg_pid = line.split()[0]
                    self.log.info('FFmpeg wrapperer pid: {}'.format(ffmpeg_pid))
                    break
        else:
            self.err.TestFailure("There is no any ffmpeg process running.")
        beginning_time = time.time()
        total_ffmpeg_stderr_output = []
        while True:
            stdout, stderr = self.ssh_client_2.execute_cmd('busybox tail -n 1 /tmp/ffmpeg.stderr.{}'.format(ffmpeg_pid))
            if "No such file or directory" in stderr:
                break
            elif time.time() - beginning_time >= 600:
                raise self.err.TestError("/tmp/ffmpeg.stderr.{} keeps displaying log more than 600 seconds!".format(ffmpeg_pid))
            else:
                total_ffmpeg_stderr_output.append(stdout.strip())
        if total_ffmpeg_stderr_output:
            average_speed = self._parser_ffmpeg_result(total_ffmpeg_stderr_output)
            speed.value = average_speed
        else:
            raise self.err.TestError('There is no speed information from /tmp/ffmpeg.stderr.{}'.format(ffmpeg_pid))

    def _parser_ffmpeg_result(self, output):
        """
        The FFmpeg output will be looked like:
        frame=   77 fps= 51 q=-0.0 size=    1840kB time=00:00:36.07 bitrate= 417.8kbits/s speed=23.7x
        """
        check_field = ['time', 'speed']
        speed_list = []
        for line in output:
            if all(field in line for field in check_field):
                self.log.info(line)
                pattern = re.compile(r'(.+time=)(.+)(bitrate=.+speed=)(.+)(x)')
                match = pattern.match(line)
                play_time = match.group(2)
                speed = float(match.group(4))
                
                # Convert the play_time into seconds
                #t = time.strptime(play_time.split('.')[0], '%H:%M:%S')
                #current_time = datetime.timedelta(hours=t.tm_hour, minutes=t.tm_min, seconds=t.tm_sec).total_seconds()

                if speed <= 1:
                    self.log.error('The transcoding speed: {}X is lesser than 1X'.format(speed))
                    speed_list = []
                    break
                else:
                    self.log.debug('Speed: {}X is greater than: 1X as expected'.format(speed))
                    speed_list.append(speed)

        if speed_list:
            # The transcoding speed at the beginning will be much higher than average value,
            # so remove the first 1/3 data and use the rest 2/3 to calculate average speed
            for i in range((len(speed_list)+1)/3):
                speed_list.pop(0)
            average_speed = round(sum(speed_list) / len(speed_list), 2)
        else:
            self.log.error('There are no speed information from stderr output')
            average_speed = 0

        self.log.info('Transcoding average speed: {}X for video'.format(average_speed))
        return average_speed


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** FFmpeg starting time stress test on KDP Linux ***
        """)

    parser.add_argument('--file_donwload_url', help='specify the url where testing video file could be downloaded.', \
                        default="http://fileserver.hgst.com/test/VideoTranscoding/FullRegression/202105/v3.1/300s/")
    parser.add_argument('--file_name', help='testing video file name', default='H264_1080P_60FPS_BASELINE@L32_300S.mkv')
    parser.add_argument('--play_duration', help='How many seconds to play the video', default=60)
    parser.add_argument('--output_url', help='Which client the FFmpeg send UDP output to', default='udp://127.0.0.1:9999')
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')


    test = FFmpegStress(parser)
    resp = test.main()
    #print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
