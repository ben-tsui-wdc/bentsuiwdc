# -*- coding: utf-8 -*-
""" Tool for check ibi network
"""
# std modules
import logging
import sys
from argparse import ArgumentParser

# platform modules
from platform_libraries.serial_client import SerialClient


class CheckIbiNetwork(object):

    def __init__(self, parser):
        self.serial_client = SerialClient(parser.serial_server_ip, parser.serial_server_port, stream_log_level=logging.DEBUG)
        self.serial_client.initialize_serial_port()

    def main(self):
        self.serial_client.show_ifconfig()
        self.serial_client.ping_google()


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Turn on SoftAP mode ***
        """)
    parser.add_argument('-ss_ip', '--serial_server_ip', help='Destination serial server IP address', metavar='IP', default=None)
    parser.add_argument('-ss_port', '--serial_server_port', help='Destination UUT serial port', metavar='PORT', default=None)

    test = CheckIbiNetwork(parser.parse_args())
    if test.main():
        sys.exit(0)
    sys.exit(1)
