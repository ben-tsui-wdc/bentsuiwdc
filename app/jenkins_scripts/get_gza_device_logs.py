# -*- coding: utf-8 -*-
""" Tool for getting logs from GZA device.
"""
# std modules
import logging
from argparse import ArgumentParser

# platform modules
from platform_libraries.ssh_client import SSHClient

class GZADeviceLogGetter(object):

    def __init__(self, parser):
        self.ssh_client = None
        self.log_path = parser.path
        self.clean_logs = parser.clean_logs

        self.ssh_client = SSHClient(parser.ssh_ip, parser.ssh_user, parser.ssh_password, parser.ssh_port)
        self.ssh_client.connect()

    def main(self):
        self.ssh_client.save_gza_device_logs(file_name=self.log_path)
        if self.clean_logs: self.ssh_client.clean_device_logs()
        self.ssh_client.close()


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Get logcat from GZA device ***
        """)

    parser.add_argument('-p', '--path', help='File path to save device log', metavar='PATH', default='/root/app/output/logs.tgz')
    parser.add_argument('-ssh_ip', '--ssh_ip', help='The hostname of SSH server', metavar='IP')
    parser.add_argument('-ssh_user', '--ssh_user', help='The username of SSH server', default="sshd")
    parser.add_argument('-ssh_password', '--ssh_password', help='The password of SSH server', metavar='PWD', default="Test1234")
    parser.add_argument('-ssh_port', '--ssh_port', help='The port of SSH server', type=int, metavar='PORT', default=22)
    parser.add_argument('-c', '--clean_logs', help='clean logs after getting logs', action='store_true', default=False)

    test = GZADeviceLogGetter(parser.parse_args())
    test.main()
