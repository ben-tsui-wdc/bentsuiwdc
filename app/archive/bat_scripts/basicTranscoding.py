___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from junit_xml import TestCase


class basicTranscoding(object):

    def __init__(self, adb=None, env=None):
        self.adb = adb
        self.env = env
        self.log = common_utils.create_logger(overwrite=False)
        self.start_time = time.time()
        self.testcase = None
        self.device_init()
        self.log = common_utils.create_logger(overwrite=False)
        self.image_name = 'MOV_0790.mp4'
        self.media_folder = './media/{}'.format(self.image_name)
        self.source = '/data/wd/diskVolume0/media'
        self.destination = '/data/wd/diskVolume0/trascondig_output'
        self.transcoding_logcat_file = './output/basic_transcoding_logcat.txt'
        self.ffmpeg_output = '{}/ffmpeg_output'.format(self.destination)
        self.transcoding_cmd = '/system/bin/ffmpeg  -eFps 30 -eWid 1280 -eHei 720  -re -i ' \
                               '{0}/{1} -c:a copy -c:v h264 -b:v 5500k -mediacodec_output_size 1280x720 {2}/test.mp4 > {3} 2>&1'\
                                .format(self.source, self.image_name, self.destination, self.ffmpeg_output)

    def run(self):
        try:
            self.adb.executeShellCommand('mkdir -p {0}'.format(self.source))
            self.adb.push(local=self.media_folder, remote=self.source+'/'+self.image_name, timeout=600)
            self.adb.executeShellCommand('mkdir -p {0}'.format(self.destination))
            check_list = ['DEC AMEDIACODEC_INFO_OUTPUT_FORMAT_CHANGED', 'frame=', 'fps=', 'speed=', 'video']
            self.adb.executeShellCommand('logcat -c')
            self.adb.executeShellCommand(self.transcoding_cmd, timeout=600, consoleOutput=False)
            self.adb.logcat_to_file(self.transcoding_logcat_file)
            self.log.info('****** Print out ffmpeg output ******')
            transcoding_output = self.adb.executeShellCommand('cat {}'.format(self.ffmpeg_output))[0]
            self.log.info('****** Print out transcoding logcat message ******')
            self.adb.executeCommand('cat {}'.format(self.transcoding_logcat_file))
            if all(word in transcoding_output for word in check_list):
                self.log.info('Basic Transcoding Test PASSED!!')
                self.testcase = TestCase(name='Basic Transcoding Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            else:
                self.error('Transcoding Failed!! Check list items not exist!')
        except Exception as ex:
            self.log.info('****** Print out ffmpeg output ******')
            self.adb.executeShellCommand('cat {}'.format(self.ffmpeg_output))
            self.log.info('****** Print out transcoding logcat message ******')
            self.adb.executeCommand('cat {}'.format(self.transcoding_logcat_file))
            self.testcase = TestCase(name='Basic Transcoding Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            self.testcase.add_failure_info('Basic Transcoding Test FAILED!! Err: {}'.format(ex))
        finally:
            self.log.info('Remove {}'.format(self.destination))
            self.adb.executeShellCommand('rm -rf {}'.format(self.destination), consoleOutput=False)
            return self.testcase

    def device_init(self):
        try:
            self.adb.connect()
            time.sleep(2)
            version = self.adb.getFirmwareVersion()
            platform = self.adb.getModel()
            self.log.info('Firmware is :{}'.format(version.split()[0]))
            self.log.info('Platform is :{}'.format(platform.split()[0]))
            time.sleep(1)
            return version.split()[0], platform.split()[0]
        except Exception as ex:
            raise Exception('Failed to connect to device and execute adb command! Err: {}'.format(ex))

    def error(self, message):
        """
            Save the error log and raise Exception at the same time
            :param message: The error log to be saved
        """
        self.log.error(message)
        raise Exception(message)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    if args.port:
        port = args.port
    else:
        port = '5555'
    adb = ADB(uut_ip=uut_ip, port=port)

    testrun = basicTranscoding(adb=adb)
    testrun.run()
