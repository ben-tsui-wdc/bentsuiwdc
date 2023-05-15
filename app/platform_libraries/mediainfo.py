"""
A tool to parse mediainfo output string.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import re
# platform modules
import common_utils


class MediaInfo(object):

    def __init__(self, filename, shell_exe, root_log='KAT'):
        self.filename = filename
        self.shell_exe = shell_exe # To execute shell command.
        self.logging = common_utils.create_logger(root_log=root_log)
        self.raw_info = self.get_media_inforamtion() # Raw data from mediainfo output.
        self.info = self.parse_info() # Dict data.
        """ examples:
        {'Audio': {'Bit rate': 6111,
          'Channel positions': 'Front: L R',
          'Channel(s)': '2 channels',
          'Codec ID': '40',
          'Compression mode': 'Lossy',
          'Duration': '19s 349ms',
          'Format': 'AAC',
          'Format profile': 'LC',
          'Format/Info': 'Advanced Audio Codec',
          'ID': '2',
          'Language': 'ehs',
          'Sampling rate': '48.0 KHz',
          'Stream size': '14.4 KiB (1%)'},
         'General': {'Codec ID': 'isml',
          'Codec ID/Hint': 'IIS Smooth Streaming file format',
          'Complete name': '/mnt/hgfs/Workspace/response',
          'Duration': '19s 349ms',
          'File size': '1.21 MiB',
          'Format': 'MPEG-4',
          'Format profile': 'ISML',
          'Overall bit rate': 525,
          'Writing application': 'Lavf57.37.100'},
         'Video': {'Bit depth': '8 bits',
          'Bit rate': 515,
          'Bits/(Pixel*Frame)': '0.019',
          'Chroma subsampling': '4:2:0',
          'Codec ID': 'avc1',
          'Codec ID/Info': 'Advanced Video Coding',
          'Color space': 'YUV',
          'Display aspect ratio': '16:9',
          'Duration': '19s 119ms',
          'Format': 'AVC',
          'Format profile': 'High@L4.2',
          'Format settings, CABAC': 'Yes',
          'Format settings, ReFrames': '1 frame',
          'Format/Info': 'Advanced Video Codec',
          'Frame rate': None,
          'Frame rate mode': 'Constant',
          'Height': 720,
          'ID': '1',
          'Language': 'ehs',
          'Scan type': 'Progressive',
          'Stream size': '1.17 MiB (97%)',
          'Width': 1280}}
        """

    def get_media_inforamtion(self):
        stdout, stderr = self.shell_exe('mediainfo {}'.format(self.filename))
        if stdout:
            return stdout
        return None

    def parse_info(self):
        return parse_info_string(info_str=self.raw_info, logging=self.logging)

    def verify_video_format(self, video_format):
        # case insensitive
        self.logging.info('Video format is expected: {}'.format(video_format))
        if video_format.lower() in self.info['General']['Format'].lower():
            return True
        self.logging.error('Video format do not match: {} != {}'.format(self.info['General']['Format'], video_format))
        return False

    def verify_video_codec(self, video_codec):
        # case insensitive
        self.logging.info('Video codec is expected: {}'.format(video_codec))
        cmp_codec_lower = video_codec.lower()
        codec_lower = self.info['Video']['Codec ID'].lower()
        # We cosider AVC and H.264 are the same.
        if cmp_codec_lower.replace('.', '') in ['avc', 'h264'] and codec_lower.replace('.', '') in ['avc', 'h264']:
            return True
        elif cmp_codec_lower not in codec_lower:
            return True
        self.logging.error('Video codec do not match: {} != {}'.format(self.info['Video']['Codec ID'], video_codec))
        return False

    def verify_resolution(self, resolution):
        # Only check Height of video.
        height = {
            '240p': 240,
            '360p': 360,
            '480p': 480,
            '720p': 720,
            '1080p': 1080
        }.get(resolution)
        if not height:
            self.logging.error('{} not supported'.format(resolution))
            return False
        return self.verify_width_and_height(height=height)

    def verify_width_and_height(self, width=None, height=None):
        if not any([width, height]):
            self.logging.error('Need width or height')
            return False
        self.logging.info('Video resolution is expected: {} {}'.format(
                'width={}'.format(width) if width else '',
                'height={}'.format(height) if height else ''
            ))
        # +-3% tolerance.
        if height:
            if not height*1.03 > self.info['Video']['Height'] > height*0.97:
                self.logging.error('Video Height do not match: {} != {}'.format(self.info['Video']['Height'], height))
                return False
        if width:
            if not width*1.03 > self.info['Video']['Width'] > width*0.97:
                self.logging.error('Video Width do not match: {} != {}'.format(self.info['Video']['Width'], width))
                return False
        return True

def parse_info_string(info_str, attr_handlers=None, logging=None):
    """ Parse string from mediainfo to dict object. """
    if not attr_handlers:
        attr_handlers = AttrHandler()
    info = {}
    focus_section = None
    for line in info_str.splitlines():
        try:
            line = line.strip()
            if not line:
                continue
            # Set focus_section
            if ':' not in line:
                focus_section = line
                info[focus_section] = {}
                continue
            # Parse string
            key, value = attr_handlers.parse_attr(line)
            # Record info
            info[focus_section][key] = value
        except:
            if logging:
                logging.exception(line)
            else:
                print 'Exception at:', line
    return info


class AttrHandler(object):

    def get_final_key(self, raw_key):
        # "raw_key" => "final_key" or "raw_key"
        return { # Add more key here.
        }.get(raw_key, raw_key)

    def get_value_parser(self, final_key, raw_value):
        # "final_key" => value parser
        return { # Add more parser here.
            'Height': self.parse_prefix_number,
            'Width': self.parse_prefix_number,
            'Bit rate': self.parse_prefix_number,
            'Overall bit rate': self.parse_prefix_number,
            'Bit rate': self.parse_prefix_number,
            'Frame rate': self.parse_prefix_number,
        }.get(final_key, lambda x: x)

    def parse_attr(self, line):
        # Split line
        raw_key = line[:41].strip()
        raw_value = line[43:].strip()
        # Parse string
        key = self.get_final_key(raw_key)
        v_parser = self.get_value_parser(key, raw_value)
        if v_parser:
            return key, v_parser(raw_value)
        return key, raw_value

    def parse_prefix_number(self, string):
        if not string:
            return None
        last_digit_idx = re.search(r'(\d)[^\d]*$', string).start() + 1
        number_string = string[:last_digit_idx + 1].replace(' ', '')
        if not number_string.isdigit():
            return None
        return int(number_string)
