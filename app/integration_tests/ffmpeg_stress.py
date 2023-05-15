"""
A stress test to execute ffmpeg with specified starting time: 120->60->180 seconds

Pass criteria:
    1. FFMPEG always works without errors
    2. Current playing time is greater than the start time we specified
    3. The speed is always greater than 1X
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

import subprocess
import time
import datetime
import re
import argparse
import sys

from multiprocessing import Process, Value
from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from platform_libraries.test_result import upload_to_logstash


class FFmpegStressTest(object):

    TEST_SUITE = 'Transcoding_Stress_Test'
    TEST_NAME = 'FFMPEG_Stress_Test'
    UUT_TEST_FOLDER = '/data/wd/diskVolume0/'

    def __init__(self):

        # Create usages
        example = 'python.exe FFmpegStressTest.py --uut_ip 192.168.1.45 --loop 100'
        parser = argparse.ArgumentParser(description='*** Stress Test for FFmpeg on Kamino Android ***\n\nExamples:{0}'.
                                         format(example), formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('--uut_ip', help='Destination NAS IP address, ex. 192.168.1.45')
        parser.add_argument('--port', help='Destination IP port, ex. 5555', default='5555')
        parser.add_argument('--env', help='Cloud test environment', default='dev1', choices=['dev1', 'qa1', 'prod'])
        parser.add_argument('--adb_server', help='Use adb server to run tests or not', action='store_true', default=False)
        parser.add_argument('--adb_server_ip', help='The IP address of adb server', default='10.10.10.10')
        parser.add_argument('--adb_server_port', help='The port of adb server', default='5037')
        parser.add_argument('--logstash', help='Logstash server IP address', default='10.92.234.101')
        parser.add_argument('--file_server', help='File server IP address', default='fileserver.hgst.com')
        parser.add_argument('--loop', help='How many test iterations', default=1)
        parser.add_argument('--file_name', help='Test video file name', default='1080P_H264_AAC_30FPS.mkv')
        parser.add_argument('--play_duration', help='How many seconds to play the video', default=60)
        parser.add_argument('--udp_output', help='Which client the FFmpeg send UDP output to', default='10.10.10.10')
        parser.add_argument('--dry_run', help='Result will not be uploaded to logstash', action='store_true', default=False)
        parser.add_argument('-ap_ssid', '--ap_ssid', help='The SSID of destination AP', metavar='SSID', default=None)
        parser.add_argument('-ap_password', '--ap_password', help='The password of destination AP', metavar='PWD', default=None)
        args = parser.parse_args()

        # Environment info
        if args.adb_server:
            self.adb = ADB(adbServer=args.adb_server_ip, adbServerPort=args.adb_server_port, uut_ip=args.uut_ip)
            self.cmd = 'adb -H {0} -P {1} -s {2}:{3} shell /system/bin/ffmpeg '.\
                       format(args.adb_server_ip, args.adb_server_port, args.uut_ip, args.port)
        else:
            self.adb = ADB(uut_ip=args.uut_ip, port=args.port)
            self.cmd = 'adb -s {}:{} shell /system/bin/ffmpeg '.format(args.uut_ip, args.port)

        self.adb.connect()
        self.product=self.adb.getModel()
        self.adb.stop_otaclient()
        self.logstash_server = 'http://{}:8000'.format(args.logstash)
        self.log = common_utils.create_logger()
        self.iterations = int(args.loop)
        self.file_name = args.file_name
        self.udp_output = args.udp_output
        self.play_duration = int(args.play_duration)
        self.dry_run = args.dry_run
        self.build = 'Unknown'
        self.file_server_url = 'ftp://ftp:ftppw@{}/test/'.format(args.file_server)
        self.test_file_url = '{0}{1}{2}'.format(self.file_server_url, 'FFmpegStress/', self.file_name)
        # Specified where (seconds) to start playing the video
        self.start_time = [60, 180, 120]

    def main(self):
        # Download testfile before running tests
        self.log.info('Downloading test file: {} from file server...'.format(self.file_name))
        self.adb.executeShellCommand('busybox wget {0} -P {1}'.format(self.test_file_url, self.UUT_TEST_FOLDER))

        for iteration in range(self.iterations):
            self.log.info('### Starting FFmpeg stress test, iteration: {} ###'.format(int(iteration) + 1))
            self.build = self.adb.getFirmwareVersion()
            self.log.info('Running on firmware version: {}'.format(self.build))
            speed_result_list = []
            for start_time in self.start_time:
                self.log.info('Starting FFmpeg from: {} seconds, will be played for {} seconds'.
                              format(start_time, self.play_duration))
                self.log.info('Checking if FFmpeg was started by anyone else')
                """
                    We can use 'ps | grep ffmpeg' to check FFmpeg is running or not.
                    If there is more than 1 process in Monarch or 2 processes in Pelican,
                    it might cause problem if we try to create another FFmpeg process.
                """
                stdout, stderr = self.adb.executeShellCommand('ps | grep ffmpeg', consoleOutput=False)
                if stdout:
                    self.log.error('There is already a FFmpeg process exist: {}'.format(stdout))
                    sys.exit(1)
                else:
                    self.log.info('No one is running FFmpeg, start the test')

                try:
                    command = self.cmd + '-ss {} -eFps 30 -eWid 1280 -eHei 720 '.format(start_time) + \
                              '-i {0}{1} '.format(self.UUT_TEST_FOLDER, self.file_name) + \
                              '-c:a copy -c:v h264 -b:v 5500k -mediacodec_output_size 1280x720 ' + \
                              '-f mpegts -copyts udp://{}:9999'.format(self.udp_output)
                    p = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    # Shared value for getting speed result from forked process
                    speed = Value('d', 0.0)
                    p1 = Process(target=self._get_process_output, args=(p, start_time, speed, ))
                    p1.start()
                    # Quit process after specified time
                    time.sleep(self.play_duration)
                    """
                        Use kill -13 {ffmpeg_pid} to stop ffmpeg process instead of using python kill method.
                        Python kill method will send SIGKIL signal (same as kill -9) and might cause error.
                        The ffmpeg process output:
                        root      25473 25467 109076 26624 futex_wait f71b3780 S /system/bin/ffmpeg
                    """
                    # p.kill()
                    stdout, stderr = self.adb.executeShellCommand('ps | grep ffmpeg', consoleOutput=False)
                    if stdout:
                        self.log.debug('FFmpeg process status: {}'.format(stdout))
                        ffmpeg_pid = stdout.split()[1]
                        self.log.debug('FFmpeg pid: {}'.format(ffmpeg_pid))
                        self.adb.executeShellCommand('kill -13 {}'.format(ffmpeg_pid), consoleOutput=False)
                    else:
                        self.log.warning('Cannot get FFmpeg process information, check stderr: {}'.format(stderr))

                    p1.join()
                    speed_result_list.append(speed.value)
                except Exception as e:
                    self.log.error('FFmpeg stress test failed by exception, error message: {}'.format(e.message))
                    sys.exit(1)

            # The speed result will be in list format like: [12.85, 7.93, 17.94]
            # Set test result to Failed if any one of the speed is 0X
            if not speed_result_list or 0 in speed_result_list:
                test_result = 'Failed'
                average_speed = 0
            else:
                test_result = 'Passed'
                average_speed = round(sum(speed_result_list) / len(speed_result_list), 2)

            if not self.dry_run:
                # For Report Sequence
                if (iteration + 1) < 10:
                    build_itr = self.build + '_itr_0{}'.format(int(iteration) + 1)
                else:
                    build_itr = self.build + '_itr_{}'.format(int(iteration) + 1)

                # Upload result to logstash server
                data = {'testSuite': self.TEST_SUITE,
                        'testName': self.TEST_NAME,
                        'build': self.build,
                        'iteration': build_itr,
                        'FFMPEGStressSpeed': average_speed,
                        'FFMPEGStressResult': test_result,
                        'product': self.product}
                upload_to_logstash(data, self.logstash_server)

            if test_result == 'Passed':
                self.log.info('Total average speed: {}X'.format(average_speed))
                self.log.info('### FFmpeg stress test Passed! ###')
            else:
                self.log.error('### FFmpeg stress test Failed! ###')
                sys.exit(1)

        self.log.info('Deleting the test file in UUT folder')
        self.adb.executeShellCommand('rm {0}{1}'.format(self.UUT_TEST_FOLDER, self.file_name))

    def _get_process_output(self, process, start_time, speed):
        """
        Check the ffmpeg output and parser the information we need
        """
        try:
            stdout, stderr = process.communicate()
            self.log.debug('\nStdout: \n{}'.format(stdout))
            output = stdout.splitlines()
            if output:
                result = self._parser_ffmpeg_result(output, start_time)
                speed.value = result
            else:
                self.log.error('There are no outputs from FFmpeg command!')
                sys.exit(1)
        except Exception as e:
            self.log.info("Error:{}".format(repr(e)))

    def _parser_ffmpeg_result(self, output, start_time):
        """
        The FFmpeg output will be looked like:
        frame=   77 fps= 51 q=-0.0 size=    1840kB time=00:00:36.07 bitrate= 417.8kbits/s speed=23.7x
        """
        check_field = ['time', 'speed']
        speed_list = []
        for line in output:
            if all(field in line for field in check_field):
                pattern = re.compile(r'(.+time=)(.+)(bitrate=.+speed=)(.+)(x)')
                match = pattern.match(line)
                play_time = match.group(2)
                speed = float(match.group(4))
                # Convert the play_time into seconds
                t = time.strptime(play_time.split('.')[0], '%H:%M:%S')
                current_time = datetime.timedelta(hours=t.tm_hour, minutes=t.tm_min, seconds=t.tm_sec).total_seconds()

                if current_time < start_time:
                    self.log.error('Current time: {0} is lesser than the time specified: {1}'.format(current_time, start_time))
                else:
                    self.log.debug('Current time: {0} is greater than: {1} as expected'.format(current_time, start_time))

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
            self.log.error('There are no speed information from adb std output')
            average_speed = 0

        self.log.info('Average speed: {}X'.format(average_speed))
        return average_speed

if __name__ == '__main__':
    ffmpeg_test = FFmpegStressTest()
    ffmpeg_test.main()
