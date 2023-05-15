# -*- coding: utf-8 -*-
""" Video Transcoding Settings.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
from collections import defaultdict, OrderedDict
# platform modules
from platform_libraries.pyutils import NotSet


#
# Codec String Area
#
CODEC_H263 = 'h263'
CODEC_H264 = 'h264'
CODEC_H265 = 'hevc'
CODEC_MPEG4 = 'mpeg4'
CODEC_VP9 = 'vp9'
CODEC_AV1 = 'av1'
CODEC_VC1 = 'vc1'

#
# Transcoding Settings Area
#
# Refer to: func parseTranscodeParams() in internal/httpserver/files.go.
API_VIDEO_CODECS = [
    CODEC_H264
]

# Refer to: func serve() in internal/httpserver/files.go.
API_CONTAINERS = [
    'ismv',
    'matroska',
    'mpegTS',
    #'fmp4',
    #'webm'
]

# Refer to: switch transOpts.Container in internal/httpserver/files.go.
API_MIMETYPE = {
    'ismv': 'application/vnd.ms-sstr+xml',
    'matroska': 'video/x-matroska',
    'mpegTS': 'video/mp2t',
    'fmp4': 'video/mp4',
    'webm': 'video/webm'
}

# Refer to: func parseTranscodeParams() in internal/httpserver/files.go.
API_TRANSCODING_SETTINGS = OrderedDict([
    #'original': {},
    ('1080p', {
        'width': 1920,
        'height': 1080,
        'frame_rate': 30,
        'bit_rate': 4000
    }),
    ('1080p-high', {
        'width': 1920,
        'height': 1080,
        'frame_rate': 30,
        'bit_rate': 8000
    }),
    ('1080p-medium', {
        'width': 1920,
        'height': 1080,
        'frame_rate': 30,
        'bit_rate': 4000
    }),
    ('1080p-low', {
        'width': 1920,
        'height': 1080,
        'frame_rate': 30,
        'bit_rate': 4000
    }),
    ('720p', {
        'width': 1280,
        'height': 720,
        'frame_rate': 30,
        'bit_rate': 2000
    }),
    ('720p-high', {
        'width': 1280,
        'height': 720,
        'frame_rate': 30,
        'bit_rate': 8000
    }),
    ('720p-medium', {
        'width': 1280,
        'height': 720,
        'frame_rate': 30,
        'bit_rate': 4000
    }),
    ('720p-low', {
        'width':1280,
        'height': 720,
        'frame_rate': 30,
        'bit_rate': 2000
    }),
    ('480p', {
        'width':858,
        'height': 480,
        'frame_rate': 30,
        'bit_rate': 1000
    }),
    ('480p-high', {
        'width':858,
        'height': 480,
        'frame_rate': 30,
        'bit_rate': 4000
    }),
    ('480p-medium', {
        'width':858,
        'height': 480,
        'frame_rate': 30,
        'bit_rate': 2000
    }),
    ('480p-low', {
        'width':858,
        'height': 480,
        'frame_rate': 30,
        'bit_rate': 1000
    }),
    ('360p', {
        'width':480,
        'height': 360,
        'frame_rate': 30,
        'bit_rate': 500
    }),
    ('360p-high', {
        'width':480,
        'height': 360,
        'frame_rate': 30,
        'bit_rate': 2000
    }),
    ('360p-medium', {
        'width':480,
        'height': 360,
        'frame_rate': 30,
        'bit_rate': 1000
    }),
    ('360p-low', {
        'width':480,
        'height': 360,
        'frame_rate': 30,
        'bit_rate': 750
    }),
    ('240p', {
        'width':352,
        'height': 240,
        'frame_rate': 30,
        'bit_rate': 250
    }),
    ('240p-high', {
        'width':352,
        'height': 240,
        'frame_rate': 30,
        'bit_rate': 1000
    }),
    ('240p-medium', {
        'width':352,
        'height': 240,
        'frame_rate': 30,
        'bit_rate': 750
    }),
    ('240p-low', {
        'width':352,
        'height': 240,
        'frame_rate': 30,
        'bit_rate': 500
    })
])

RESOLUTION_MAPPINGS = OrderedDict([
    ('1080p', (1920, 1080)),
    ('720p', (1280, 720)),
    ('480p', (858, 480)),
    ('360p', (480, 360)),
    ('240p', (352, 240))
])


def get_max_api_resolution_options(video_info):
    """
    Ref to: convertMaxTranscodeOptions() in http://stash.wdmv.wdc.com/projects/RESTSDK/repos/sdk/browse/internal/httpserver/files.go
    """
    resolution_option = '1080p'
    for resolution, wh in RESOLUTION_MAPPINGS.iteritems():
        if wh[0] >= video_info['video']['width'] and wh[1] >= video_info['video']['height']:
            resolution_option = resolution
            continue
        break
    return resolution_option

def get_pretranscoding_resolution(video_info):
    resolution = get_max_api_resolution_options(video_info)
    if '1080p' in resolution:
        return '720p'
    return resolution


#
# Video Profile Area
#
"""
Refer to:
    https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/profiles.c
    https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/avcodec.h
    https://www.itu.int/rec/T-REC-H.264
"""
class VideoProfile(str):

    def __new__(cls, codec, profile_name, profile_id):
        obj = str.__new__(cls, profile_name)
        obj.codec = codec
        obj.id = profile_id
        return obj


# Notes: For now use these objects like string, Codec ID may not be used...
# H264 Profiles
FF_PROFILE_H264_BASELINE = VideoProfile(CODEC_H264, "Baseline", 66)
FF_PROFILE_H264_CONSTRAINED_BASELINE = VideoProfile(CODEC_H264, "Constrained Baseline", 66) # 66|FF_PROFILE_H264_CONSTRAINED
FF_PROFILE_H264_MAIN = VideoProfile(CODEC_H264, "Main", 77)
FF_PROFILE_H264_EXTENDED = VideoProfile(CODEC_H264, "Extended", 88)
FF_PROFILE_H264_HIGH = VideoProfile(CODEC_H264, "High", 100)
FF_PROFILE_H264_HIGH_10 = VideoProfile(CODEC_H264, "High 10", 110)
FF_PROFILE_H264_HIGH_10_INTRA = VideoProfile(CODEC_H264, "High 10 Intra", 110) #110|FF_PROFILE_H264_INTRA
FF_PROFILE_H264_MULTIVIEW_HIGH = VideoProfile(CODEC_H264, "Multiview High", 118)
FF_PROFILE_H264_HIGH_422 = VideoProfile(CODEC_H264, "High 4:2:2", 122)
FF_PROFILE_H264_HIGH_422_INTRA = VideoProfile(CODEC_H264, "High 4:2:2 Intra", 122)
FF_PROFILE_H264_STEREO_HIGH = VideoProfile(CODEC_H264, "Stereo High", 128)
FF_PROFILE_H264_HIGH_444 = VideoProfile(CODEC_H264, "High 4:4:4", 144)
FF_PROFILE_H264_HIGH_444_PREDICTIVE = VideoProfile(CODEC_H264, "High 4:4:4 Predictive", 244)
FF_PROFILE_H264_HIGH_444_INTRA = VideoProfile(CODEC_H264, "High 4:4:4 Intra", 244) # 244|FF_PROFILE_H264_INTRA
FF_PROFILE_H264_CAVLC_444 = VideoProfile(CODEC_H264, "CAVLC 4:4:4", 44)

# H268 Profiles
FF_PROFILE_HEVC_MAIN = VideoProfile(CODEC_H265, "Main", 1)
FF_PROFILE_HEVC_MAIN_10 = VideoProfile(CODEC_H265, "Main 10", 2)
FF_PROFILE_HEVC_MAIN_STILL_PICTURE = VideoProfile(CODEC_H265, "Main Still Picture", 3)
FF_PROFILE_HEVC_REXT = VideoProfile(CODEC_H265, "Rext", 4)

# MPEG4 Video Profiles
FF_PROFILE_MPEG4_SIMPLE = VideoProfile(CODEC_MPEG4, "Simple Profile", 0)
FF_PROFILE_MPEG4_SIMPLE_SCALABLE = VideoProfile(CODEC_MPEG4, "Simple Scalable Profile", 1)
FF_PROFILE_MPEG4_CORE = VideoProfile(CODEC_MPEG4, "Core Profile", 2)
FF_PROFILE_MPEG4_MAIN = VideoProfile(CODEC_MPEG4, "Main Profile", 3)
FF_PROFILE_MPEG4_N_BIT = VideoProfile(CODEC_MPEG4, "N-bit Profile", 4)
FF_PROFILE_MPEG4_SCALABLE_TEXTURE = VideoProfile(CODEC_MPEG4, "Scalable Texture Profile", 5)
FF_PROFILE_MPEG4_SIMPLE_FACE_ANIMATION = VideoProfile(CODEC_MPEG4, "Simple Face Animation Profile", 6)
FF_PROFILE_MPEG4_BASIC_ANIMATED_TEXTURE = VideoProfile(CODEC_MPEG4, "Basic Animated Texture Profile", 7)
FF_PROFILE_MPEG4_HYBRID = VideoProfile(CODEC_MPEG4, "Hybrid Profile", 8)
FF_PROFILE_MPEG4_ADVANCED_REAL_TIME = VideoProfile(CODEC_MPEG4, "Advanced Real Time Simple Profile", 9)
FF_PROFILE_MPEG4_CORE_SCALABLE = VideoProfile(CODEC_MPEG4, "Code Scalable Profile", 10)
FF_PROFILE_MPEG4_ADVANCED_CODING = VideoProfile(CODEC_MPEG4, "Advanced Coding Profile", 11)
FF_PROFILE_MPEG4_ADVANCED_CORE = VideoProfile(CODEC_MPEG4, "Advanced Core Profile", 12)
FF_PROFILE_MPEG4_ADVANCED_SCALABLE_TEXTURE = VideoProfile(CODEC_MPEG4, "Advanced Scalable Texture Profile", 13)
FF_PROFILE_MPEG4_SIMPLE_STUDIO = VideoProfile(CODEC_MPEG4, "Simple Studio Profile", 14)
FF_PROFILE_MPEG4_ADVANCED_SIMPLE = VideoProfile(CODEC_MPEG4, "Advanced Simple Profile", 15)

# VP9 Video Profiles
FF_PROFILE_VP9_PROFILE_0 = VideoProfile(CODEC_VP9, "Profile 0", 0)
FF_PROFILE_VP9_PROFILE_1 = VideoProfile(CODEC_VP9, "Profile 1", 1)
FF_PROFILE_VP9_PROFILE_2 = VideoProfile(CODEC_VP9, "Profile 2", 2)
FF_PROFILE_VP9_PROFILE_3 = VideoProfile(CODEC_VP9, "Profile 3", 3)

#define FF_PROFILE_VC1_SIMPLE   0
#define FF_PROFILE_VC1_MAIN     1
#define FF_PROFILE_VC1_COMPLEX  2
#define FF_PROFILE_VC1_ADVANCED 3

# AV1 Video Profiles
FF_PROFILE_AV1_MAIN = VideoProfile(CODEC_AV1, "Main", 0)
FF_PROFILE_AV1_HIGH = VideoProfile(CODEC_AV1, "High", 1)
FF_PROFILE_AV1_PROFESSIONAL = VideoProfile(CODEC_AV1, "Professional", 2)

# VC1 Video Profiles
FF_PROFILE_VC1_SIMPLE = VideoProfile(CODEC_VC1, "Simple", 0)
FF_PROFILE_VC1_MAIN = VideoProfile(CODEC_VC1, "Main", 1)
FF_PROFILE_VC1_COMPLEX = VideoProfile(CODEC_VC1, "Complex", 2)
FF_PROFILE_VC1_ADVANCED = VideoProfile(CODEC_VC1, "Advanced", 3)


# Init VIDEO_PROFILES table
"""
Example: 
{
    "h264": {
        "Baseline": FF_PROFILE_H264_BASELINE object,
        "Constrained Baseline": FF_PROFILE_H264_CONSTRAINED_BASELINE object
    }
}
"""
VIDEO_PROFILES = defaultdict(dict)
for name, value in locals().items():
    if not (name.startswith('FF_PROFILE_') and isinstance(value, VideoProfile)):
        continue
    VIDEO_PROFILES[value.codec][str(value)] = value

def get_video_profile(codec, name, default=NotSet):
    if default is NotSet:
        default = name
    return VIDEO_PROFILES.get(codec, {}).get(name, default)


#
# Support Rules Area
#
# Refer to: func VideoTranscodingRules() and h265VideoTranscodingRules() in /internal/system/system_monarch/system_android.go
Monarch_Transcoding_Rules = [
    {
        'src_max_width': 1920,
        'src_max_height': 1080,
        'src_max_frame_rate': 60,
        'src_codecs': [
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_MAIN,
                'level': 42,
            },
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_HIGH,
                'level': 42,
            },
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_BASELINE,
                'level': 32,
            },
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_CONSTRAINED_BASELINE,
                'level': 32,
            },
            {
                'codec': CODEC_H263,
                'profile': None,
                'level': None,
            },
            {
                'codec': CODEC_MPEG4,
                'profile': FF_PROFILE_MPEG4_SIMPLE,
                'level': 5,
            },
            {
                'codec': CODEC_MPEG4,
                'profile': FF_PROFILE_MPEG4_ADVANCED_SIMPLE,
                'level': 5,
            },
            {
                'codec': CODEC_VP9,
                'profile': FF_PROFILE_VP9_PROFILE_0,
                'level': None,
            },
        ],
        'dst_max_width': 1920,
        'dst_max_height': 1080,
        'dst_max_frame_rate': 30,
        'dst_codec': CODEC_H264
    },
    {
        'src_max_width': 1920,
        'src_max_height': 1080,
        'src_max_frame_rate': 60,
        'src_codecs': [
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_MAIN,
                'level': 42,
            },
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_HIGH,
                'level': 42,
            },
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_BASELINE,
                'level': 32,
            },
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_CONSTRAINED_BASELINE,
                'level': 32,
            },
            {
                'codec': CODEC_H263,
                'profile': None,
                'level': None,
            },
            {
                'codec': CODEC_MPEG4,
                'profile': FF_PROFILE_MPEG4_SIMPLE,
                'level': 5,
            },
            {
                'codec': CODEC_MPEG4,
                'profile': FF_PROFILE_MPEG4_ADVANCED_SIMPLE,
                'level': 5,
            },
            {
                'codec': CODEC_VP9,
                'profile': FF_PROFILE_VP9_PROFILE_0,
                'level': None,
            },
        ],
        'dst_max_width': 1280,
        'dst_max_height': 720,
        'dst_max_frame_rate': 60,
        'dst_codec': CODEC_H264
    }
]

Pelican_Transcoding_Rules = [
    {
        'src_max_width': 3840,
        'src_max_height': 2160,
        'src_max_frame_rate': 60,
        'src_codecs': [
            {
                'codec': CODEC_H265,
                'profile': FF_PROFILE_HEVC_MAIN,
                'level': 51,
            },
            {
                'codec': CODEC_H265,
                'profile': FF_PROFILE_HEVC_MAIN_10,
                'level': 51,
            },
            {
                'codec': CODEC_H263,
                'profile': None,
                'level': None,
            }
        ],
        'dst_max_width': 1920,
        'dst_max_height': 1080,
        'dst_max_frame_rate': 30,
        'dst_codec': CODEC_H264
    },
    {
        'src_max_width': 3840,
        'src_max_height': 2160,
        'src_max_frame_rate': 30,
        'src_codecs': [
            {
                'codec': CODEC_H265,
                'profile': FF_PROFILE_HEVC_MAIN,
                'level': 51,
            },
            {
                'codec': CODEC_H265,
                'profile': FF_PROFILE_HEVC_MAIN_10,
                'level': 51,
            },
            {
                'codec': CODEC_H263,
                'profile': None,
                'level': None,
            },
            {
                'codec': CODEC_VP9,
                'profile': FF_PROFILE_VP9_PROFILE_0,
                'level': None,
            }
        ],
        'dst_max_width': 1280,
        'dst_max_height': 720,
        'dst_max_frame_rate': 60,
        'dst_codec': CODEC_H264
    }
]
Pelican_Transcoding_Rules.extend(Monarch_Transcoding_Rules)
YodaPlus_Transcoding_Rules = Pelican_Transcoding_Rules
Godzilla_Transcoding_Rules = [
    {
        'src_max_width': 3840,
        'src_max_height': 2160,
        'src_max_frame_rate': 60,
        'src_codecs': [
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_MAIN,
                'level': 51,
            }
        ],
        'dst_max_width': 1920,
        'dst_max_height': 1080,
        'dst_max_frame_rate': 30,
        'dst_codec': CODEC_H264
    },
    {
        'src_max_width': 1920,
        'src_max_height': 1080,
        'src_max_frame_rate': 60,
        'src_codecs': [
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_MAIN,
                'level': 42,
            },
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_HIGH,
                'level': 42,
            },
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_BASELINE,
                'level': 32,
            },
            {
                'codec': CODEC_H264,
                'profile': FF_PROFILE_H264_CONSTRAINED_BASELINE,
                'level': 32,
            }
        ],
        'dst_max_width': 1920,
        'dst_max_height': 1080,
        'dst_max_frame_rate': 30,
        'dst_codec': CODEC_H264
    }
]
RnD_H264_4K_SRC_CODES = [
    {
        'codec': CODEC_H265,
        'profile': FF_PROFILE_HEVC_MAIN,
        'level': 51,
    },
    {
        'codec': CODEC_VP9,
        'profile': FF_PROFILE_VP9_PROFILE_0,
        'level': None,
    },
    {
        'codec': CODEC_AV1,
        'profile': FF_PROFILE_AV1_MAIN,
        'level': 51,
    }
]
RnD_H264_1080P_SRC_CODES = [
    {
        'codec': CODEC_H264,
        'profile': FF_PROFILE_H264_MAIN,
        'level': 42,
    },
    {
        'codec': CODEC_H264,
        'profile': FF_PROFILE_H264_HIGH,
        'level': 42,
    },
    {
        'codec': CODEC_H264,
        'profile': FF_PROFILE_H264_BASELINE,
        'level': 42,
    },
    {
        'codec': CODEC_H264,
        'profile': FF_PROFILE_H264_CONSTRAINED_BASELINE,
        'level': 42,
    },
    {
        'codec': CODEC_MPEG4,
        'profile': FF_PROFILE_MPEG4_SIMPLE,
        'level': 5,
    },
    {
        'codec': CODEC_MPEG4,
        'profile': FF_PROFILE_MPEG4_ADVANCED_SIMPLE,
        'level': 5,
    },
    {
        'codec': CODEC_H265,
        'profile': FF_PROFILE_HEVC_MAIN,
        'level': 51,
    },
    {
        'codec': CODEC_VP9,
        'profile': FF_PROFILE_VP9_PROFILE_0,
        'level': None,
    },
    {
        'codec': CODEC_AV1,
        'profile': FF_PROFILE_AV1_MAIN,
        'level': 51,
    }
]
RnD_H264_Transcoding_Rules = [
    {
        'src_max_width': 3840,
        'src_max_height': 2160,
        'src_max_frame_rate': 60,
        'src_codecs': RnD_H264_4K_SRC_CODES,
        'dst_max_width': 1920,
        'dst_max_height': 1080,
        'dst_max_frame_rate': 30,
        'dst_codec': CODEC_H264
    },
    {
        'src_max_width': 3840,
        'src_max_height': 2160,
        'src_max_frame_rate': 30,
        'src_codecs': RnD_H264_4K_SRC_CODES,
        'dst_max_width': 1920,
        'dst_max_height': 1080,
        'dst_max_frame_rate': 30,
        'dst_codec': CODEC_H264
    },
    {
        'src_max_width': 1920,
        'src_max_height': 1080,
        'src_max_frame_rate': 60,
        'src_codecs': RnD_H264_1080P_SRC_CODES,
        'dst_max_width': 1920,
        'dst_max_height': 1080,
        'dst_max_frame_rate': 30,
        'dst_codec': CODEC_H264
    },
    {
        'src_max_width': 1920,
        'src_max_height': 1080,
        'src_max_frame_rate': 60,
        'src_codecs': RnD_H264_1080P_SRC_CODES,
        'dst_max_width': 1280,
        'dst_max_height': 720,
        'dst_max_frame_rate': 60,
        'dst_codec': CODEC_H264
    }
]
RnD_Transcoding_Rules = RnD_H264_Transcoding_Rules