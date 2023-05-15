# -*- coding: utf-8 -*-
""" A simple tool to upload json result to ELK server.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import argparse
import os
import re
import sys
# platform modules
from platform_libraries.constants import LOGSTASH_SERVER_TW
from platform_libraries.common_utils import create_logger
from platform_libraries.test_result import TestResult

log = create_logger()


# TODO: Move these function to library.
def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    """ alist.sort(key=natural_keys) sorts in human order """
    return [ atoi(c) for c in re.split('(\d+)', text) ]


if __name__ == '__main__':
    # Handle input arguments. 
    parser = argparse.ArgumentParser(description='Upload results from json files.',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-f', '--from_folder', help='Location of result files', metavar='PATH')
    parser.add_argument('-lsu', '--logstash_server_url', help='Logstash server URL', metavar='URL', default=LOGSTASH_SERVER_TW)
    args = parser.parse_args()

    path = args.from_folder
    server_url = args.logstash_server_url

    # Check path.
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        log.info('Path does not exist.')
        sys.exit(1)

    # Upload results
    for dir_path, dir_names, file_names in os.walk(abs_path):
        if not file_names:
            continue
        log.info('Current folder: {}.'.format(dir_path))
        file_names.sort(key=natural_keys) # Upload file in human order.
        for name in file_names:
            file_path = os.path.join(dir_path, name)
            if not name.endswith('.json'):
                log.info('Ignore file: {}.'.format(file_path))
                continue
            try:
                log.info('Load file: {}...'.format(file_path))
                tr = TestResult().from_file(file_path, input_format='json')
                log.info('Upload result...')
                tr.upload_to_logstash(server_url=server_url)
            except:
                log.exception('Upload file failed.')
    log.info('Done.')
    sys.exit(0)
