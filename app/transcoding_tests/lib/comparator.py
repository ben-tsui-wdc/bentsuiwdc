# -*- coding: utf-8 -*-
""" Video information comparators.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

from transcoding_settings import get_video_profile, VideoProfile


class ErrValueNotFound(RuntimeError):
    pass

class ErrNecessaryValueNotFound(RuntimeError):
    pass


def result_logging(name=None):
    """ Print logs for compare results.
    """
    def decorator(method):
        debug_name = '{} * '.format(name) if name else ''
        def wrapper(*args, **kwargs):
            # Get logging instance.
            try:
                log = args[0].log
            except:
                log = None
            # Logging result.
            try:
                ret = method(*args, **kwargs)
                if log: log.debug('* {}Compare Result: {}'.format(debug_name, ret))
                return ret
            except ErrValueNotFound:
                if log: log.debug('* {}Compare Result: SKIP'.format(debug_name))
                raise
        return wrapper
    return decorator


class Comparator(object):
    """ Basic comparator for comparing two Information object.
    """
    def __init__(self, src_set, cmp_set, logging):
        self.src_set = src_set
        self.cmp_set = cmp_set
        self.last_cmp = None
        self.log = logging

    def record_cmp(self, keys, value_of_src, value_of_cmp):
        self.last_cmp = {'keys': keys, 'value_of_src': value_of_src, 'value_of_cmp': value_of_cmp}

    def get_last_cmp_msg(self):
        if not self.last_cmp:
            return ''
        if self.last_cmp.get('keys'):
            keys_msg = '{}: '.format(self.last_cmp['keys'])
        else:
            keys_msg = ''
        return '{}{} vs {}'.format(
            keys_msg, self.last_cmp.get('value_of_src'), self.last_cmp.get('value_of_cmp')
        )

    def _get_value_by_keys(self, dict_data, keys):
        value = dict_data
        try:
            for key in keys:
                value = value.get(key)
        except:
            return None
        return value

    def _get_cmp_values(self, keys, src_none_err=ErrValueNotFound, src_none_msg='value_of_src is None',
            cmp_none_err=ErrValueNotFound, cmp_none_msg='value_of_cmp is None', src_val_mapping=None):
        # return value_of_src, value_of_cmp
        value_of_src, value_of_cmp = self._get_value_by_keys(self.src_set, keys), self._get_value_by_keys(self.cmp_set, keys)
        if src_val_mapping:
            new_value_of_src = src_val_mapping(value_of_src)
            self.log.debug('Map value: {} to value: {}'.format(value_of_src, new_value_of_src))
            value_of_src = new_value_of_src
        self.log.debug('{:30s}: {} vs {}'.format(''.join(['["{}"]'.format(i) for i in keys]), value_of_src, value_of_cmp))
        self.record_cmp(keys, value_of_src, value_of_cmp)
        if value_of_src is None:
            raise src_none_err(src_none_msg)
        if value_of_cmp is None:
            raise cmp_none_err(cmp_none_msg)
        return value_of_src, value_of_cmp

    def _cmp_number_with_tolerance(self, src_value, cmp_value, tolerance):
        self.log.debug('Compare {} and {} with tolerance: {}'.format(src_value, cmp_value, tolerance))
        if src_value*(1 + tolerance) > cmp_value > src_value*(1 - tolerance):
            return True
        return False

    @result_logging(name='Equal Number')
    def cmp_number(self, keys, tolerance=None, **kwargs):
        src_v, cmp_v = self._get_cmp_values(keys, **kwargs)
        if tolerance:
            return self._cmp_number_with_tolerance(src_v, cmp_v, tolerance)
        return src_v == tolerance

    @result_logging(name='Substring')
    def match_substring(self, keys, case_insensitive=False, **kwargs):
        src_v, cmp_v = self._get_cmp_values(keys, **kwargs)
        return self._match_substring(src_v, cmp_v, case_insensitive)

    def _match_substring(self, src_string, cmp_string, case_insensitive=False):
        if case_insensitive:
            if hasattr(src_string, 'lower'):
                src_string = src_string.lower()
            if hasattr(cmp_string, 'lower'):
                cmp_string = cmp_string.lower()
        return src_string in cmp_string or cmp_string in src_string

    @result_logging(name='Equal Value')
    def same_cmp(self, keys, **kwargs):
        src_v, cmp_v = self._get_cmp_values(keys, **kwargs)
        return src_v == cmp_v

    def cmp_size(self):
        return self.same_cmp(keys=['size'])

    def cmp_mine_type(self):
        return self.same_cmp(keys=['mimeType'])

    def cmp_video_codec(self):
        # Special case:  "msmpeg4v3" vs "msmpeg4"
        return self.match_substring(keys=['video', 'videoCodec'])

    def cmp_video_codec_profile(self):
        return self.same_cmp(keys=['video', 'videoCodecProfile'])

    def cmp_video_codec_level(self):
        return self.same_cmp(keys=['video', 'videoCodecLevel'], src_val_mapping=self.get_video_level_mapping())

    def cmp_video_bit_rate(self, tolerance=0.03):
        return self.cmp_number(keys=['video', 'bitRate'], tolerance=tolerance)

    def cmp_video_frame_rate(self, tolerance=0.03):
        return self.cmp_number(keys=['video', 'frameRate'], tolerance=tolerance)

    def cmp_video_duration(self, tolerance=0.03):
        return self.cmp_number(keys=['video', 'duration'], tolerance=tolerance)

    def cmp_width(self, tolerance=0.03):
        return self.cmp_number(keys=['video', 'width'], tolerance=tolerance)

    def cmp_height(self, tolerance=0.03):
        return self.cmp_number(keys=['video', 'height'], tolerance=tolerance)

    @result_logging(name='Less than or Equivalent with')
    def verify_stream_video_bit_rate(self, max_times=1.1):
        src_v, cmp_v = self._get_cmp_values(keys=['video', 'bitRate'])
        self.log.debug('Expected maximum of bitRate: {}x{}'.format(src_v, max_times))
        return cmp_v <= src_v*max_times

    @result_logging(name='Container Verify')
    def verify_stream_container(self):
        src_v = self._get_value_by_keys(self.src_set, keys=['container'])
        cmp_v = self._get_value_by_keys(self.cmp_set, keys=['format_name'])
        self.record_cmp('container vs format_name', src_v, cmp_v)
        self.log.debug('{:30s}: {} vs {}'.format('container vs format_name', src_v, cmp_v))
        # Replace original src_v value for check if need.
        src_v_for_check = {
            'ismv': 'mov' # ismv is extended from QuickTime .mov
        }.get(src_v)
        if src_v_for_check:
            self.log.debug('Replace "{}" by "{}" for verifying.'.format(src_v, src_v_for_check))
            src_v = src_v_for_check
        return self._match_substring(src_v, cmp_v, case_insensitive=True)

    @result_logging(name='frameRate Verify')
    def verify_stream_frame_rate(self, src_frame_rate, tolerance=0.03):
        src_v, cmp_v = self._get_cmp_values(keys=['video', 'frameRate'])
        if src_v > src_frame_rate:
            self.log.debug('Since "{}" is greater than "{}" of source, expect frameRate is fixed.'.format(src_v, src_frame_rate))
            src_v =  src_frame_rate
        return self._cmp_number_with_tolerance(src_v, cmp_v, tolerance)

    @result_logging(name='Resolution Verify')
    def verify_stream_resolution(self, aspect_ratio, tolerance_of_ar=0.1, tolerance_of_wh=0.03):
        src_wv, cmp_wv = self._get_cmp_values(keys=['video', 'width'])
        if not cmp_wv:
            return False
        src_hv, cmp_hv = self._get_cmp_values(keys=['video', 'height'])
        if not cmp_hv:
            return False
        # Verify aspect ratio is not change. 
        self.log.debug('Check aspect ratio...')
        if not (self._cmp_number_with_tolerance(cmp_wv/float(cmp_hv), aspect_ratio, tolerance_of_ar) or \
                self._cmp_number_with_tolerance(cmp_hv/float(cmp_wv), aspect_ratio, tolerance_of_ar)):
            return False
        self.log.debug('Check width and height...')
        if not (self._cmp_number_with_tolerance(src_wv, cmp_wv, tolerance_of_wh) or \
                self._cmp_number_with_tolerance(src_hv, cmp_hv, tolerance_of_wh)):
            return False
        return True

    #
    # Mappings
    #
    def get_video_level_mapping(self):
        if self._get_value_by_keys(self.src_set, keys=['video', 'videoCodec']) in 'av1':
            return self.av1_level_mapping
        return None

    def av1_level_mapping(self, level_idx):
        # https://github.com/wdc-csbu/restsdk/blob/4509862ef1cca69b223f75f493d207e582c2c91d/internal/trans/video/video.go#L339
        # ffprobe idx value -> RestSDK level value
        return {
            0: 20,
            1: 21,
            2: 22,
            3: 23,
            4: 30,
            5: 31,
            6: 32,
            7: 33,
            8: 40,
            9: 41,
            10: 42,
            11: 43,
            12: 50,
            13: 51,
            14: 52,
            15: 53,
            16: 60,
            17: 61,
            18: 62,
            19: 63,
            20: 70,
            21: 71,
            22: 72,
            23: 73
        }.get(level_idx, None)


#
# Comparators For checkOnly Call
#
class TrasncodingSupportChecker(Comparator):
    """ Comparator for checking one single transcoding rule is support or not.
        self.src_set # SPEC Limitation Rules
        self.cmp_set # Transcoding Target
    """
    def _lt(self, keys, **kwargs):
        src_v, cmp_v = self._get_cmp_values(keys, **kwargs)
        return src_v < cmp_v

    @result_logging(name='Satisfied Value')
    def satisfy(self, keys, **kwargs):
        """ dst is not larger than src. """
        if not self._lt(keys, **kwargs):
            return True
        return False

    def get_video_profile_object(self):
        # Not support if it has no profile
        src_profile, cmp_profile = self._get_cmp_values(
            keys=['video', 'videoCodecProfile'],
            src_none_msg='src_profile is None, SPEC support all profile.',
            cmp_none_err=ErrNecessaryValueNotFound, cmp_none_msg='cmp_profile is None, video has unknown profile')
        # Try to get VideoProfile object.
        if not isinstance(src_profile, VideoProfile):
            src_profile = get_video_profile(codec=self.src_set['video']['videoCodec'], name=src_profile)
        if not isinstance(cmp_profile, VideoProfile):
            cmp_profile = get_video_profile(codec=self.cmp_set['video']['videoCodec'], name=cmp_profile)
        return src_profile, cmp_profile

    def eq_codec(self):
        # Not support if it has no videoCodec
        return self.same_cmp(keys=['video', 'videoCodec'], cmp_none_err=ErrNecessaryValueNotFound,
            cmp_none_msg='videoCodec is None, video has unknown codec')

    @result_logging(name='Equal videoCodecProfile')
    def eq_profile(self):
        src_profile, cmp_profile = self.get_video_profile_object()
        if src_profile != cmp_profile:
            return False
        return True

    def is_support(self):
        for pairs in [
            (self.eq_codec, {}),
            (self.eq_profile, {}),
            (self.satisfy, {'keys': ['video', 'videoCodecLevel']}),
            (self.satisfy, {'keys': ['video', 'width']}),
            (self.satisfy, {'keys': ['video', 'height']}),
            (self.satisfy, {'keys': ['video', 'frameRate']})
        ]:
            try:
                method, kwargs = pairs
                if not method(**kwargs):
                    return False
            except ErrValueNotFound as e:
                self.log.warning(e)
                continue
            except ErrNecessaryValueNotFound as e: # Not support for special case.
                self.log.warning(e)
                return False
        return True

class SPECLimitationChecker(object):
    """ Comparator for checking transcoding targets are support or not.

                    |SPEC Limitation VS Transcoding Target
        ------------+----------------++-------------------
        Source      |self.limit_src  VS target_src
        ------------+----------------++-------------------
        Destination |self.limit_dest VS target_dest
    """
    def __init__(self, limit_src, limit_dest, logging):
        self.limit_src = limit_src
        self.limit_dest = limit_dest
        self.log = logging

    def is_support(self, target_src, target_dest):
        self.print_src_debug_message()
        self.print_dest_debug_message(target_src, target_dest)
        # Check source video is support or not.
        self.log.debug('Check source video...')
        if not TrasncodingSupportChecker(src_set=self.limit_src, cmp_set=target_src, logging=self.log).is_support():
            return False
        self.log.debug('Check transcoding target...')
        # Check transcoding target is support or not.
        if not TrasncodingSupportChecker(src_set=self.limit_dest, cmp_set=target_dest, logging=self.log).is_support():
            return False
        return True

    def print_src_debug_message(self):
        self.log.debug('*** SPEC Checker Rules: Source {}x{}/{}hz/{}/{}/L{} to Destination {}x{}/{}hz/{}'.format(
            self.limit_src['video']['width'], self.limit_src['video']['height'], self.limit_src['video']['frameRate'],
            self.limit_src['video']['videoCodec'], self.limit_src['video']['videoCodecProfile'], self.limit_src['video']['videoCodecLevel'],
            self.limit_dest['video']['width'], self.limit_dest['video']['height'], self.limit_dest['video']['frameRate'],
            self.limit_dest['video']['videoCodec']
        ))

    def print_dest_debug_message(self, target_src, target_dest):
        self.log.debug('*** Transcoding Target: Source {}x{}/{}hz/{}/{}/L{} to Destination {}x{}/{}hz/{}'.format(
            target_src['video']['width'], target_src['video']['height'], target_src['video']['frameRate'],
            target_src['video']['videoCodec'], target_src['video']['videoCodecProfile'], target_src['video']['videoCodecLevel'],
            target_dest['video']['width'], target_dest['video']['height'], target_dest['video']['frameRate'],
            target_dest['video']['videoCodec']
        ))
