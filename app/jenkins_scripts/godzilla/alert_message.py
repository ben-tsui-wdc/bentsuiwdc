# -*- coding: utf-8 -*-
""" Tool for add/remove alert message.
"""
# std modules
import logging
import sys
from argparse import ArgumentParser

# platform modules
from platform_libraries.ssh_client import SSHClient


class AlertMessage(object):

    def __init__(self, parser):
        self.remove_all = parser.remove_all
        self.add_alert_code = parser.add_alert
        self.ssh_client = SSHClient(parser.ssh_ip, parser.ssh_user, parser.ssh_password, parser.ssh_port)
        self.ssh_client.connect()

    def main(self):
        if self.remove_all: self.ssh_client.clean_alert_messages()
        if self.add_alert_code: self.ssh_client.add_alert_message(code=self.add_alert_code)


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Add/Remove alert message ***
        """)

    parser.add_argument('-ssh-ip', '--ssh-ip', help='The hostname of SSH server', metavar='IP')
    parser.add_argument('-ssh-user', '--ssh-user', help='The username of SSH server', default="sshd")
    parser.add_argument('-ssh-password', '--ssh-password', help='The password of SSH server', metavar='PWD', default="Test1234")
    parser.add_argument('-ssh-port', '--ssh-port', help='The port of SSH server', type=int, metavar='PORT', default=22)
    parser.add_argument('-ra', '--remove-all', help='Remove all alert messages', action='store_true', default=False)
    parser.add_argument('-aa', '--add-alert', help='Add alert message by code', metavar='CODE', default=None)

    AlertMessage(parser.parse_args()).main()
