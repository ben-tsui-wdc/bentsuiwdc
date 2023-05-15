# -*- coding: utf-8 -*-
# std modules
from argparse import ArgumentParser
import ftplib
# platform modules
from platform_libraries.common_utils import create_logger


class FTPClient(object):

    def __init__(self, log_name=None, stream_log_level=None):
        self.log = create_logger(overwrite=False, log_name=log_name, stream_log_level=stream_log_level)
        self.ftp_inst = None

    def connect(self, server, port=21, username='anonymous', password='anonymous'):
        if not self.ftp_inst: self.ftp_inst = ftplib.FTP(timeout=60)
        self.log.info('Connect to {0}:{1}...'.format(server, port))
        self.ftp_inst.connect(server, port)
        self.log.info('Server connected and now login with {0}...'.format(username, password))
        self.ftp_inst.login(username, password)
        self.log.info('Login successfully')

    def disconnect(self):
        if self.ftp_inst: self.ftp_inst.quit()

    def upload_file(ftp, filename):
        with open(filename, 'rb') as fp:
            self.log.info('Upload {}...'.format(filename))
            self.ftp_inst.storbinary('STOR %s' % filename, fp)
            self.log.info('{} is uploaded'.format(filename))