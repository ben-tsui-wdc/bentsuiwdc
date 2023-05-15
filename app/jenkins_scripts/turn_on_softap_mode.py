# -*- coding: utf-8 -*-
""" Tool for turn on SoftAP mode.
"""
# std modules
import logging
import sys
from argparse import ArgumentParser

# platform modules
from platform_libraries.serial_client import SerialClient


class TurnOnSoftAPMode(object):

    def __init__(self, parser):
        self.serial_client = SerialClient(parser.serial_server_ip, parser.serial_server_port, stream_log_level=logging.DEBUG)
        self.serial_client.initialize_serial_port()
        self.kdp = parser.kdp

    def main(self):
        if self.kdp: 
            self.serial_client.lock_otaclient_service_kdp()
            return self.serial_client.turn_on_soft_ap_mode_kdp()
        self.serial_client.stop_otaclient_service()
        return self.serial_client.turn_on_soft_ap_mode()


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Turn on SoftAP mode ***
        """)
    parser.add_argument('-ss_ip', '--serial_server_ip', help='Destination serial server IP address', metavar='IP', default=None)
    parser.add_argument('-ss_port', '--serial_server_port', help='Destination UUT serial port', metavar='PORT', default=None)
    parser.add_argument('-kdp', '--kdp', help='Target device is using KDP build', action='store_true', default=False)

    test = TurnOnSoftAPMode(parser.parse_args())
    if test.main():
        sys.exit(0)
    sys.exit(1)
