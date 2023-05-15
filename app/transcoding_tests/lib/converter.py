# -*- coding: utf-8 -*-
""" Video information converters.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import json
import subprocess
# platform modules
from transcoding_settings import API_TRANSCODING_SETTINGS

#
# Common Media Inforamtion
#
class Information(dict):
    def __init__(self, *args, **kwargs):
        # Basic format. Keep REST SDK API format.
        info = {
            u"size": None,
            u"mimeType": None,
            u"name": None,
            u"video": {
                u"audioCodec": None,
                u"videoCodec": None,
                u"videoCodecProfile": None,
                u"videoCodecLevel": None,
                u"bitRate": None,
                u"frameRate": None,
                u"width": None,
                u"height": None,
                u"duration": None
            },
            # Additional fields From ffprobe
            u"format_name": None,
            u"format_long_name": None,
            # Additional fields For Test
            u"container": None,
            u"resolution": None,
            u"rotate": None
        }
        info.update(kwargs)
        info.get('video', {}).get('videoCodecProfile')
        super(Information, self).__init__(**info)

class SPECLimitationInformation(Information):

    def __init__(self, codec, profile, level, frame_rate, width, height):
        info = Information()
        info['video']['videoCodec'] = codec
        info['video']['videoCodecProfile'] = profile
        info['video']['videoCodecLevel'] = level
        info['video']['frameRate'] = frame_rate
        info['video']['width'] = width
        info['video']['height'] = height
        super(SPECLimitationInformation, self).__init__(**info)

class TranscodingSettingInformation(Information):
    """ Transcoding Settings -> Information object
    """
    def __init__(self, video_codec, container, resolution, duration):
        settings = API_TRANSCODING_SETTINGS[resolution]
        info = Information()
        info['video']['bitRate'] = settings['bit_rate']
        info['video']['frameRate'] = settings['frame_rate']
        info['video']['videoCodec'] = video_codec # For now only accept "h264", so that we do nothing here. 
        info['video']['width'] = settings['width']
        info['video']['height'] = settings['height']
        info['video']['duration'] = duration/1000 if duration else None # expect microsecond
        info['container'] = container
        info['resolution'] = resolution
        # Keep other data be None.
        super(TranscodingSettingInformation, self).__init__(**info)


#
# Convert Function Area
#
def get_file_name(value):
    return value.rsplit('/', 1).pop()

def get_file_ext(value):
    return value.rsplit('.', 1).pop()

def string2float(value):
    # Convert float number.' 
    if '/' in value: # For case: "100/3"
        if '.' not in value:
            value = value + u'.0' # "100/3" -> "100/3.0"
        return eval(value)
    return float(value)

def string2thousandths_float(value):
    return float(value)/1000


#
# Converter Area
#
class Converter(object):
    def __init__(self, src, logging):
        self.src = src
        self.log = logging

    def _convert_value(self, value, func):
        src_value = value
        if not isinstance(func, list):
            func_list = [func]
        else:
            func_list = func

        for convert in func_list:
            try:
                value = convert(value)
            except:
                self.log.warning(u'Value: {} convert by func: {} error.'.format(value, convert.func_name), exc_info=True)
                return None
        return value

    def convert(self):
        return self.src


class FileAPIResponseConverter(Converter):
    """ File API Response -> Information object
    """
    def convert(self):
        info = Information()
        for k, v in self.src.iteritems():
            if k == 'video':
                for sk, sv in v.iteritems():
                    info['video'][sk] = sv
            else:
                info[k] = v
        return info


class FFmpegInfoConverter(Converter):
    """ FFprobe output -> Information object
    """
    def convert(self):
        info = Information()
        # From format field.
        if 'format' in self.src:
            if 'size' in self.src['format']:
                info['size'] = self._convert_value(self.src['format']['size'], func=int)
            if 'filename' in self.src['format']:
                info['name'] = self._convert_value(self.src['format']['filename'], func=get_file_name)
            if 'format_name' in self.src['format']:
                info['format_name'] = self.src['format']['format_name']
            if 'format_long_name' in self.src['format']:
                info['format_long_name'] = self.src['format']['format_long_name']

        # Get mimeType from file extension.
        if 'name' in info:
            file_ext = get_file_ext(info['name'])
            info['mimeType'] = self.get_mime_type(file_ext)

        # From video stream.
        video_stream = self.get_stream()
        if 'codec_name' in video_stream:
            info['video']['videoCodec'] = video_stream['codec_name']
        if 'profile' in video_stream:
            info['video']['videoCodecProfile'] = video_stream['profile']
        if 'level' in video_stream:
            info['video']['videoCodecLevel'] = self.get_codec_level(
                codec_name=video_stream.get('codec_name'), level=video_stream['level']
            )
        if 'avg_frame_rate' in video_stream:
            info['video']['frameRate'] = self._convert_value(video_stream['avg_frame_rate'], func=string2float)
        if 'width' in video_stream:
            info['video']['width'] = video_stream['width']
        if 'height' in video_stream:
            info['video']['height'] = video_stream['height']
        # Get rotation.
        if 'tags' in video_stream and 'rotate' in video_stream['tags']: # before FFmpeg 5.0
            info['rotate'] = self._convert_value(video_stream['tags']['rotate'], func=int)
        elif 'side_data_list' in video_stream: # after FFmpeg 5.0
            for item in video_stream['side_data_list']:
                if 'rotation' in item:
                    info['rotate'] = self._convert_value(item['rotation'], func=int)
                    break

        # From audio stream.
        audio_stream = self.get_stream(stream_type='audio')
        if 'codec_name' in audio_stream:
            info['video']['audioCodec'] = audio_stream['codec_name']

        # Set value with porirty.
        # bitRate
        if 'bit_rate' in video_stream:
            info['video']['bitRate'] = self._convert_value(video_stream['bit_rate'], func=string2thousandths_float)
        elif 'format' in self.src and 'bit_rate' in self.src['format']:
            info['video']['bitRate'] = self._convert_value(self.src['format']['bit_rate'], func=string2thousandths_float)
        # duration
        if 'duration' in video_stream:
            info['video']['duration'] = self._convert_value(video_stream['duration'], func=float)
        elif 'format' in self.src and 'duration' in self.src['format']:
            info['video']['duration'] = self._convert_value(self.src['format']['duration'], func=float)

        return info

    def get_stream(self, stream_type='video'):
        # FFmpeg should sort "streams". If it not, do sort at init.
        for stream in self.src['streams']:
            if stream['codec_type'] == stream_type:
                return stream
        return {}

    def get_codec_level(self, codec_name, level):
        # Handle H265
        if codec_name == 'hevc':
            return {
                30: 10,
                60: 20,
                63: 21,
                90: 30,
                93: 31,
                120: 40,
                123: 41,
                150: 50,
                153: 51,
                156: 52,
                180: 60,
                183: 61,
                186: 62
            }.get(level, level)
        return level

    def get_mime_type(self, ext):
        """ Ref to http://stash.wdmv.wdc.com/projects/RESTSDK/repos/sdk/browse/internal/extract/extract.go
        """
        # More extension mapping.
        if ext in ["jpg", "jpeg", "jpe", "jif", "jfif", "jfi"]:
            ext = 'jpeg'
        elif ext in ["mov", "moov", "qt"]:
            ext = 'mov'
        elif ext in ["3gp", "m4v", "mp4"]:
            ext = 'mp4'
        elif ext in ["m1v", "m2v", "mp2", "mpa", "mpe", "mpeg", "mpg"]:
            ext = 'mpeg'
        elif ext in ["ts", "tp"]:
            ext = 'ts'
        elif ext in ["3fr"]:
            ext = 'h3fr'

        return {
            'jpeg': "image/jpeg",
            'png': "image/png",
            'gif': "image/gif",
            'bmp': "image/bmp",
            'tiff': "image/tiff",
            'webp': "image/webp",
            'flac': "audio/flac",
            'm4a': "audio/m4a",
            'mp3': "audio/mpeg",
            #'ogg': "audio/ogg", # Not support ogg video (KAM111-353).
            'wav': "audio/wav",
            'wma': "audio/x-ms-wma",
            'asf': "video/x-ms-asf",
            'avi': "video/avi",
            'dv' : "video/dv",
            'flv': "video/x-flv",
            'mkv': "video/x-matroska",
            'mov': "video/quicktime",
            'mp4': "video/mp4",
            'mpeg': "video/mpeg",
            'mts': "video/mts",
            'm2ts': "video/m2ts",
            'ts' : "video/mp2t",
            'vob': "video/x-ms-vob",
            'webm': "video/webm",
            'wmv': "video/x-ms-wmv",
            'doc': "application/msword",
            'docx': "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            'xls': "application/vnd.ms-excel",
            'xlsx': "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            'ppt': "application/vnd.ms-powerpoint",
            'pptx': "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            'arw': "image/x-sony-arw",
            'srf': "image/x-raw",
            'sr2': "image/x-sony-sr2",
            'crw': "image/x-canon-crw",
            'cr2': "image/x-canon-cr2",
            'nef': "image/x-nikon-nef",
            'nrw': "image/x-nikon-nrw",
            'kdc': "image/x-kodak-kdc",
            'dcr': "image/x-kodak-dcr",
            'orf': "image/x-olympus-orf",
            'pef': "image/x-pentax-pef",
            'ptx': "image/x-ptx",
            'raf': "image/x-fuji-raf",
            'rw2': "image/x-panasonic-rw2",
            'dng': "image/x-adobe-dng",
            'x3f': "image/x-sigma-x3f",
            'srw': "image/x-samsung-srw",
            'h3fr': "image/x-hasselblad-3fr",
            'mrw': "image/x-minolta-mrw"
            # TODO: raw
        }.get(ext)


class VideoConverter(FFmpegInfoConverter):
    """ Video file -> Information object
    """
    def __init__(self, path, logging):
        self.path = path
        self.log = logging
        self.src = self.extract_video_with_ffprobe(path)

    def extract_video_with_ffprobe(self, path):
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams' , path
            ]
            self.log.debug('Executing cmd: {}'.format(cmd))
            raw_output = subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            self.log.error('Parsing video failed: {}'.format(e))
            raise
        return json.loads(raw_output)
