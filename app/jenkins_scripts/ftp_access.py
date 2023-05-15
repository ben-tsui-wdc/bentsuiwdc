# -*- coding: utf-8 -*-
""" Tool for FTP access.
"""
# std modules
from argparse import ArgumentParser
import io
import ftplib
import socket
# platform modules
from platform_libraries.ftp_client import FTPClient


class FTPAccess(object):

    def __init__(self, parser):
        self.server = parser.server
        self.port = parser.port
        self.username = parser.username
        self.password = parser.password

        self.remote_work_folder = parser.remote_work_folder
        self.clean_up = parser.clean_up
        self.verify_login_fail = parser.verify_login_fail
        self.verify_read_fail = parser.verify_read_fail
        self.verify_read = parser.verify_read
        self.verify_write = parser.verify_write

        self.ftp_client = FTPClient()
        self.cleanup_files = []

    def main(self):
        try:
            try:
                self.ftp_client.connect(self.server, self.port, self.username, self.password)
                if self.verify_login_fail: raise AssertionError("connected to server successfully as not expected")
            except (ftplib.error_perm, socket.error) as e:
                if self.verify_login_fail:
                    self.ftp_client.log.info('Login fail as expected')
                    return # not allow this account or anonymous has no folder can access
                else:
                    self.ftp_client.log.error(e, exc_info=True)
                    raise AssertionError("Login fail")

            if not self.remote_work_folder: raise RuntimeError("No argument --remote-work-folder specified")
            try:
                self.ftp_client.ftp_inst.cwd(self.remote_work_folder)
                if self.verify_read_fail: raise AssertionError("Read folder successfully as not expected")
            except ftplib.error_perm as e:
                if self.verify_read_fail:
                    self.ftp_client.log.info('Read folder fail as expected')
                    return # this account can login but has no read permission to the folder
                else:
                    self.ftp_client.log.error(e, exc_info=True)
                    raise AssertionError("no read permission to specifying folder")

            if self.verify_read: self.verify_read_permission()
            if self.verify_write: self.verify_write_permission()
        finally:
            if self.clean_up: self.delete_uploaded_files()

    def verify_read_permission(self):
        self.ftp_client.log.info('Verify read permission...')
        self.ftp_client.log.info('List folder: {}'.format(self.ftp_client.ftp_inst.nlst()))
        try:
            self.gen_and_upload_file()
        except ftplib.error_perm as e:
            self.ftp_client.log.info('Upload file failed as expected')
            return
        raise AssertionError("Has write permission")

    def verify_write_permission(self):
        self.ftp_client.log.info('Verify write permission...')
        self.ftp_client.log.info('List folder: {}'.format(self.ftp_client.ftp_inst.nlst()))
        self.gen_and_upload_file()

    def gen_and_upload_file(self, filename="test.txt", content=b'Test Content'):
        self.ftp_client.log.info('Upload a file: {}...'.format(filename))
        self.ftp_client.ftp_inst.storbinary('STOR ' + filename, io.BytesIO(content))
        self.cleanup_files.append(filename)
        self.ftp_client.log.info('file: {} is uploaded'.format(filename))

    def delete_uploaded_files(self):
        for filename in self.cleanup_files:
            try:
                self.ftp_client.log.info('Deleting {}...'.format(filename))
                self.ftp_client.ftp_inst.delete(filename)
                self.ftp_client.log.info('{} is deleted'.format(filename))
            except Exception as e:
                self.ftp_client.log.error(e)


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** FTP Acess ***
        """)

    parser.add_argument('-s', '--server', help='FTP server URL', metavar='TARGET')
    parser.add_argument('-p', '--port', help='FTP server port', metavar='PORT', type=int, default='21')
    parser.add_argument('-U', '--username', help='FTP user', metavar='USER', default='anonymous')
    parser.add_argument('-P', '--password', help='FTP user password', metavar='PASSWORD', default='anonymous')
    parser.add_argument('-rwf', '--remote-work-folder', help='Remote work folder for verifications', metavar='PATH')
    parser.add_argument('-c', '--clean-up', help='Delete uploaded files', action='store_true', default=False)
    parser.add_argument('-vlf', '--verify-login-fail', help='Verify specifying user & password has no permission to login', action='store_true', default=False)
    parser.add_argument('-vrf', '--verify-read-fail', help='Verify specifying user & password has no permission to read work folder', action='store_true', default=False)
    parser.add_argument('-vr', '--verify-read', help='Verify specifying user & password has read permission to work folder', action='store_true', default=False)
    parser.add_argument('-vw', '--verify-write', help='Verify specifying user & password has write permission to work folder', action='store_true', default=False)

    FTPAccess(parser.parse_args()).main()
