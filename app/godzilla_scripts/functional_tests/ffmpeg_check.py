# -*- coding: utf-8 -*-
""" Test case to disable Share FTP access
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
import re
import pprint
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.common_utils import execute_local_cmd, delete_local_file


class FFMpegCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'FFMpeg Check'
    # Popcorn
    PROJECT = 'godzilla'
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'GZA-1036,GZA-1267,GZA-1564,GZA-1605'
    PRIORITYT = 'major'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.file_server_ip = '10.200.141.26'
        self.media_folder = '/GZA/ffmpeg_data/'
        self.src_folder = 'ffmpeg_src'
        self.dst_folder = 'ffmpeg_dst'
        self.dst_bitrate = None
        self.ftp_user = 'admin'
        self.ftp_password = 'adminadmin'
        self.full_test = False

    def before_test(self):
        self.download_url = 'ftp://ftp:ftppw@{0}{1}'.format(self.file_server_ip, self.media_folder)
        self.src_path = '/shares/{}/'.format(self.src_folder)
        self.dst_path = '/shares/{}/'.format(self.dst_folder)
        if not self.ssh_client.check_folder_in_device(self.src_path):
            self.ssh_client.create_share(self.src_folder)
        if not self.ssh_client.check_folder_in_device(self.dst_path):
            self.ssh_client.create_share(self.dst_folder)
            self.ssh_client.enable_share_ftp(share_name=self.dst_folder)

        self.delete_transcoded_data_and_log()
        self.log.info("Download the test videos to the source folder")
        self.ssh_client.download_file(self.download_url, dst_path=self.src_path, timeout=60*60, is_folder=True)

    def test(self):
        result = self.ssh_client.execute_cmd('ls -1 {}'.format(self.src_path))[0]
        if result:
            file_list = result.split('\n')
        else:
            raise self.err.TestFailure('No videos were found in the source folder: {}'.format(self.src_path))

        self.result_dict = {}
        for video_name in file_list:
            video_name = video_name.replace("`", "\\`")
            self.log.info("Testing video: {}".format(video_name))
            output_dict = {}
            # e.g. IPHONE_X_MPEG-4_HEVC_MAIN@L4@MAIN_AAC__LC_1920X1080_30FPS.MOV
            regex = r".+_(\S+)_(\S+)@L(\d{1}\.\d{1})@.+_(\d+)X(\d+)_(\d{1,2})M_(\d{2})FPS"
            matches = re.search(regex, video_name)
            if matches:
                output_dict['src_codec'] = matches.group(1)
                output_dict['src_profile'] = matches.group(2)
                output_dict['src_level'] = matches.group(3)
                output_dict['src_w'] = matches.group(4)
                output_dict['src_h'] = matches.group(5)
                output_dict['src_bitrate'] = matches.group(6)
                output_dict['src_fps'] = matches.group(7)
            else:
                raise self.err.TestSkipped("Please check the video name format in: "
                                           "{any}_{codec}_{profile}@{level}@{any}_{w}X{h}_{Bitrate}_{}FPS")
            extension_regex = r'(\.\S{3}$)'
            src_name = re.sub(extension_regex, '', video_name)

            # Todo: Codec and FPS are hardcoded for now
            output_dict['dst_codec'] = 'H.264'
            output_dict['dst_fps'] = '30'
            max_bitrate = 5 if output_dict['src_level'] == 'BASELINE' else 8  # Mkbps
            if self.dst_bitrate:
                output_dict['dst_bitrate'] = int(self.dst_bitrate) if int(output_dict['src_bitrate']) \
                                             >= int(self.dst_bitrate) else int(output_dict['src_bitrate'])
            else:
                output_dict['dst_bitrate'] = max_bitrate if int(output_dict['src_bitrate']) \
                                             >= int(max_bitrate) else int(output_dict['src_bitrate'])
            h_list = ['1080', '720', '480', '360']
            dst_h_list = [h for h in h_list if int(h) <= int(output_dict['src_h'])]
            self.log.info("Dst resolution lists: {}".format(dst_h_list))
            for h in dst_h_list:
                output_dict['dst_h'] = h
                if h == '1080':
                    output_dict['dst_w'] = '1920'
                elif h == '720':
                    output_dict['dst_w'] = '1280'
                elif h == '480':
                    output_dict['dst_w'] = '720'
                elif h == '360':
                    output_dict['dst_w'] = '480'

                dst_name = "{}_to_{}p".format(src_name, h)
                log_path = '{}output.log'.format(self.dst_path)
                output_path = '{}output.mp4'.format(self.dst_path)
                self.log.info("Target info: {}X{}, {}FPS, {} Mkbps".format(output_dict['dst_w'],
                                                                           output_dict['dst_h'],
                                                                           output_dict['dst_fps'],
                                                                           output_dict['dst_bitrate']))
                self.log.info("Start running the ffmpeg command...")
                ffmpeg_cmd = 'FFREPORT=file="{0}" /usr/bin/ffmpeg -y -benchmark -report -hwaccel vaapi -vaapi_device ' \
                             '/dev/dri/renderD128 -i "{1}{2}" -vf "format=nv12,hwupload,scale_vaapi=w={3}:h={4},' \
                             'fps={5}" -vcodec h264_vaapi -f matroska -acodec aac -b:v {6}k ' \
                             '-metadata:s:v:0 "rotate=0" "{7}"'.format(log_path, self.src_path, video_name,
                                                                     output_dict['dst_w'], output_dict['dst_h'],
                                                                     output_dict['dst_fps'],
                                                                     int(output_dict['dst_bitrate'])*1024, output_path)
                self.ssh_client.execute_cmd(ffmpeg_cmd, timeout=60*20)

                self.log.info("Downloading the ffmpeg log from test device")
                execute_local_cmd('curl -u {0}:{1} "ftp://{2}/{3}/output.log" -o "/tmp/output.log"'.
                                  format(self.ftp_user, self.ftp_password, self.env.ssh_ip, self.dst_folder, dst_name))

                self.log.info("Parsing the test result from the ffmpeg log file")
                with open('/tmp/output.log', 'r') as f:
                    frame_regex = r'frame=\s?(\d+)\s?fps=\s?(\d+).+bitrate=([0-9]+.[0-9]{1,3}?)kbits.+speed=([0-9]+.[0-9]{1,3}?)x\s+'
                    frame_drop_regex = r'frame=\s?\d+\s?fps=\s?\d+.+bitrate=[0-9]+.[0-9]{1,3}?kbits.+?\sdrop=(\d+)\sspeed=[0-9]+.[0-9]{1,3}?x\s+?'
                    time_regex = r'bench: utime=(.+)s stime.+rtime=(.+)s'
                    error_regex = r'frames successfully decoded, (\d) decoding errors'
                    data = f.read()
                    # frame related
                    frame_result = re.search(frame_regex, data)
                    if not frame_result:
                        self.log.warning(
                            "Sometimes the test results are not fully shown in the log, check the log manually")
                        self.log.warning(data)
                        continue
                    output_dict['frame_total'] = frame_result.group(1)
                    output_dict['fps'] = frame_result.group(2)
                    output_dict['fps_check'] = 'pass' if float(output_dict['fps']) >= float(output_dict['dst_fps']) * 0.9 else 'fail'
                    output_dict['bitrate'] = frame_result.group(3)
                    output_dict['bitrate_check'] = 'pass' if float(output_dict['bitrate']) >= float(output_dict['dst_bitrate']*1024*0.9) else 'fail'  # 90%
                    output_dict['speed'] = frame_result.group(4)
                    output_dict['speed_check'] = 'pass' if float(output_dict['speed']) > 0.95 else 'fail'  # > 0.95X
                    # frame frop related
                    frame_drop_result = re.search(frame_drop_regex, data)
                    if frame_drop_result:
                        output_dict['frame_dropped'] = frame_drop_result.group(1)
                        output_dict['frame_dropped_rate'] = round((float(output_dict['frame_dropped']) / float(output_dict['frame_total'])) * 100, 2)
                    else:
                        output_dict['frame_dropped'] = output_dict['frame_dropped_rate'] = 0
                    output_dict['frame_dropped_check'] = 'pass' if float(output_dict['frame_dropped_rate']) < 0.5 else 'fail'
                    # time related
                    time_result = re.search(time_regex, data)
                    output_dict['utime'] = time_result.group(1)
                    # Todo: Replace the 300 with video length
                    output_dict['utime_check'] = 'pass' if float(output_dict['utime']) < 300 else 'fail'
                    output_dict['rtime'] = time_result.group(2)
                    # error related
                    error_regex = re.search(error_regex, data)
                    output_dict['decode_error'] = error_regex.group(1)
                    output_dict['decode_error_check'] = 'pass' if int(output_dict['decode_error']) == 0 else 'fail'
                    # final result
                    output_dict['test_result'] = '' # Cleanup this value to prevent previous failed test result affect next line
                    output_dict['test_result'] = 'pass' if 'fail' not in output_dict.values() else 'fail'
                    if output_dict['test_result'] == 'pass':
                        self.delete_transcoded_data_and_log()
                self.result_dict[dst_name] = output_dict.copy()
        pprint.pprint(self.result_dict)
        self.generate_html_report(self.result_dict)

    def generate_html_report(self, metrics):
        HTML_RESULT = '<table id="report" class="ffmpeg">'
        for video in sorted(metrics):
            # Test Video Name
            HTML_RESULT += '<tr>'
            HTML_RESULT += '<td class="filename" colspan="9">{}</td>'.format(video)
            HTML_RESULT += '</tr>'
            # Titles
            HTML_RESULT += '<tr>'
            HTML_RESULT += '<th>Src Codec</th>'
            HTML_RESULT += '<th>Src Profile</th>'
            HTML_RESULT += '<th>Src Level</th>'
            HTML_RESULT += '<th>Src Resolution</th>'
            HTML_RESULT += '<th>Src FPS</th>'
            HTML_RESULT += '<th>Dst Codec</th>'
            HTML_RESULT += '<th>Dst Resolution</th>'
            HTML_RESULT += '<th>Dst FPS</th>'
            HTML_RESULT += '<th>Dst Bitrate</th>'
            HTML_RESULT += '</tr>'
            # Values
            HTML_RESULT += '<tr>'
            HTML_RESULT += '<td>{}</td>'.format(metrics[video]['src_codec'])
            HTML_RESULT += '<td>{}</td>'.format(metrics[video]['src_profile'])
            HTML_RESULT += '<td>{}</td>'.format(metrics[video]['src_level'])
            HTML_RESULT += '<td>{}X{}</td>'.format(metrics[video]['src_w'], metrics[video]['src_h'])
            HTML_RESULT += '<td>{}</td>'.format(metrics[video]['src_fps'])
            HTML_RESULT += '<td>{}</td>'.format(metrics[video]['dst_codec'])
            HTML_RESULT += '<td>{}X{}</td>'.format(metrics[video]['dst_w'], metrics[video]['dst_h'])
            HTML_RESULT += '<td>{}</td>'.format(metrics[video]['dst_fps'])
            HTML_RESULT += '<td>{} Kbps</td>'.format(int(metrics[video]['dst_bitrate'])*1024)
            HTML_RESULT += '</tr>'
            # Titles
            HTML_RESULT += '<tr>'
            HTML_RESULT += '<th>Total Time</th>'
            HTML_RESULT += '<th>CPU time</th>'
            HTML_RESULT += '<th>FPS</th>'
            HTML_RESULT += '<th>Speed</th>'
            HTML_RESULT += '<th>Bitrate</th>'
            HTML_RESULT += '<th>Decoding Error</th>'
            HTML_RESULT += '<th>Frame Drops</th>'
            HTML_RESULT += '<th>Frame Drops %</th>'
            HTML_RESULT += '<th>Test Result</th>'
            HTML_RESULT += '</tr>'
            # Values
            HTML_RESULT += '<tr>'
            HTML_RESULT += '<td>{} sec</td>'.format(metrics[video]['rtime'])
            HTML_RESULT += '<td class="{}">{} sec</td>'.format(metrics[video]['utime_check'], metrics[video]['utime'])
            HTML_RESULT += '<td class="{}">{}</td>'.format(metrics[video]['fps_check'], metrics[video]['fps'])
            HTML_RESULT += '<td class="{}">{}X</td>'.format(metrics[video]['speed_check'], metrics[video]['speed'])
            HTML_RESULT += '<td class="{}">{} Kbps</td>'.format(metrics[video]['bitrate_check'], metrics[video]['bitrate'])
            HTML_RESULT += '<td class="{}">{}</td>'.format(metrics[video]['decode_error_check'], metrics[video]['decode_error'])
            HTML_RESULT += '<td class="{}">{}</td>'.format(metrics[video]['frame_dropped_check'], metrics[video]['frame_dropped'])
            HTML_RESULT += '<td class="{}">{}%</td>'.format(metrics[video]['frame_dropped_check'], metrics[video]['frame_dropped_rate'])
            HTML_RESULT += '<td class="result {}">{}</td>'.format(metrics[video]['test_result'], metrics[video]['test_result'].upper())
            HTML_RESULT += '</tr>'

        HTML_RESULT += '</table>'

        with open("output/build.properties", "w") as f:
            f.write("HTML_RESULT={}\n".format(HTML_RESULT))

    def after_test(self):
        for video in self.result_dict.keys():
            if self.result_dict[video]['test_result'] == 'fail':
                raise self.err.TestFailure('At least one of the ffmpeg test result is failed!')

        # Maybe it's not necessary to delete the folders because we want to keep the large dataset?
        """
        self.ssh_client.delete_share(self.src_folder)
        self.ssh_client.delete_share(self.dst_folder)
        """

    def delete_transcoded_data_and_log(self):
        self.log.info("Delete transcoded data and log")
        self.ssh_client.delete_file_in_device('{}output.log'.format(self.dst_path))
        self.ssh_client.delete_file_in_device('{}output.mp4'.format(self.dst_path))
        delete_local_file('/tmp/output.log')

if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
    *** FFMpeg check on Godzilla devices ***
    Examples: ./run.sh godzilla_scripts/functional_tests/ffmpeg_check.py --uut_ip 10.136.137.159 -model PR2100\
    """)
    # Test Arguments
    parser.add_argument('--file_server_ip', help='file server ip address', default="10.200.141.26")
    parser.add_argument('--media_folder', help='media folder path on file server', default="/GZA/ffmpeg_data/")
    parser.add_argument('--src_folder', help='source folder in test device', default="ffmpeg_src")
    parser.add_argument('--dst_folder', help='destination folder in test device', default="ffmpeg_dst")
    parser.add_argument('--dst_bitrate', help='destination bitrate (MKbps)', default=None)
    parser.add_argument('--ftp_user', help='FTP login user name', default="admin")
    parser.add_argument('--ftp_password', help='FTP login password', default="adminadmin")
    parser.add_argument('--full_test', help='Run full test with different resolution combinations', action="store_true")
    test = FFMpegCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)