# -*- coding: utf-8 -*-
""" Tool for fatory reset ibi device via serial console.
"""
# std modules
import logging
import sys
from argparse import ArgumentParser

# platform modules
from platform_libraries.serial_client import SerialClient

class FactoryReset(object):

    def __init__(self, parser):
        self.serial_client = SerialClient(parser.serial_server_ip, parser.serial_server_port, stream_log_level=logging.DEBUG)
        self.serial_client.initialize_serial_port()
        self.kdp = parser.kdp

    def main(self):
        if self.kdp:
            return self.reset_kdp_ibi()
        else:
            return self.reset_android_ibi()

    def reset_android_ibi(self):
        # make sure console is clean to use.
        self.serial_client.serial_write("")
        self.serial_client.serial_read_all()

        # Send cmd to reset.
        self.serial_client.serial_write("reset_button.sh factory")
        
        self.serial_client.logger.info('Expect device do rebooting...')
        self.serial_client.serial_wait_for_string('init: stopping android....', timeout=60*10)

        self.serial_client.logger.info('Device rebooting...')
        self.serial_client.serial_wait_for_string('Hardware name: Realtek_RTD1295', timeout=60*15)
        return self.serial_client.wait_for_boot_complete(timeout=60*30)

    def reset_kdp_ibi(self):
        # make sure console is clean to use.
        self.serial_client.serial_write("")
        self.serial_client.serial_read_all()

        # Send cmd to reset.
        self.serial_client.serial_write("reset_button.sh factory")

        self.serial_client.logger.info('Expect device do rebooting...')
        self.serial_client.serial_wait_for_string('The system is going down', timeout=60*35)

        self.serial_client.logger.info('Device rebooting...')
        self.serial_client.serial_wait_for_string('Starting Kernel', timeout=60*15)
        return self.serial_client.wait_for_boot_complete_kdp(timeout=60*30)


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Factory Reset Script For ibi ***
        """)
    parser.add_argument('-ss_ip', '--serial_server_ip', help='Destination serial server IP address', metavar='IP', default=None)
    parser.add_argument('-ss_port', '--serial_server_port', help='Destination UUT serial port', metavar='PORT', default=None)
    parser.add_argument('-kdp', '--kdp', help='Target device is using KDP build', action='store_true', default=False)

    test = FactoryReset(parser.parse_args())
    if test.main():
        sys.exit(0)
    sys.exit(1)
