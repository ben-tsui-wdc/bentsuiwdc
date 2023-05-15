# -*- coding: utf-8 -*-
""" Tools for comparing data.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

import hashlib
import subprocess
import os


def md5sum(content):
    """ Create MD5 value of the given content. """
    hash_md5 = hashlib.md5()
    hash_md5.update(content)
    return hash_md5.hexdigest()

def md5sum_with_iter(content_iterator, chunk_size=1024*8, trace_logging=None):
    """ Create MD5 value of the given iterator. """
    hash_md5 = hashlib.md5()
    for data in content_iterator(chunk_size):
        if trace_logging: trace_logging.info('--Tracing content_iterator(id:{})-- read data: {} byte'.format(id(content_iterator), len(data)))
        hash_md5.update(data)
    return hash_md5.hexdigest()

def local_md5sum(file_name):
    """ Create MD5 value of local file. """
    hash_md5 = hashlib.md5()
    with open(file_name, 'rb') as f:
        for chunk in read_file_in_chunk(f):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def read_file_in_chunk(file_obj, chunk_size=1024*8):
    """
    Lazy function to read a file piece by piece.
    Default chunk size: 8kB.
    """
    while True:
        data = file_obj.read(chunk_size)
        if not data:
            break
        yield data

#
# ImageMagick Compare
#
def diff_images(src_img_path, target_img_path, metric='FUZZ', diff_img_path='/dev/null'):
    """ Return difference value of two images in percentage. """
    if not os.path.exists(src_img_path):
        raise IOError('{} not exists'.format(src_img_path))
    if not os.path.exists(target_img_path):
        raise IOError('{} not exists'.format(target_img_path))

    p = subprocess.Popen(['compare', '-metric', metric, src_img_path, target_img_path, diff_img_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate() # Response at stderr.
    resp_hander = {
        'FUZZ': lambda x: float(x.split('(')[-1].split(')')[0]) # "40952.7 (0.624898)" => 0.624898
    }.get(metric)
    try:
        return resp_hander(err)
    except ValueError as e: # It should be file not correct.
        raise RuntimeError(e)

def compare_images(src_img_path, target_img_path, threshold, metric='FUZZ', diff_img_path='/dev/null', log_inst=None, raise_error=False):
    """ Return True/False for different of two images with a threshold. """
    try:
        diff = diff_images(src_img_path, target_img_path, metric, diff_img_path)
        if log_inst: log_inst.info('Diff: {} -> Compare Threshold: {}'.format(diff, threshold))
        if diff > threshold:
            return False
        return True
    except Exception as e:
        if raise_error:
            raise
        if log_inst: log_inst.error(str(e)) # For logging error reason.
        return False
