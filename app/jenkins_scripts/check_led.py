# -*- coding: utf-8 -*-
""" Tool for getting LED status.
"""
# std modules
import logging
import sys
from argparse import ArgumentParser

# platform modules
from platform_libraries.pyutils import retry
from platform_libraries.serial_client import SerialClient

class CheckLed(object):

    def __init__(self, parser):
        self.max_retry = parser.max_retry
        self.delay = parser.delay
        self.led_stat = {
            'fs': 'Full Solid',
            'fb': 'Fast Breathing',
            'sb': 'Slow Breathing',
            'hs': 'Half Solid'
        }[parser.led_stat]
        self.serial_client = SerialClient(parser.serial_server_ip, parser.serial_server_port, stream_log_level=logging.DEBUG)
        self.serial_client.initialize_serial_port()

    def main(self):
        self.serial_client.logger.info('Waitng LED is enabled...')
        try:
            retry(
                func=self.serial_client.get_led_enable,
                excepts=(Exception), retry_lambda=lambda status: not status,
                delay=5, max_retry=2*6*5, log=self.serial_client.logger.info
            )
        except Exception as e:
            self.serial_client.logger.error(e)
            return False

        self.serial_client.logger.info('Expected LED stats: '+self.led_stat)
        try:
            retry(
                func=self.serial_client.get_led_state,
                excepts=(Exception), retry_lambda=self.check_led_status,
                delay=self.delay, max_retry=self.max_retry, log=self.serial_client.logger.info
            )
            return True
        except Exception as e:
            self.serial_client.logger.error(e)
            return False

    def check_led_status(self, led_stat):
        self.serial_client.logger.info('Current LED status: '+led_stat)
        return led_stat != self.led_stat


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Get LED status from device ***
        """)

    parser.add_argument('-ss_ip', '--serial_server_ip', help='Destination serial server IP address', metavar='IP')
    parser.add_argument('-ss_port', '--serial_server_port', help='Destination UUT serial port', metavar='PORT')
    parser.add_argument('-ls', '--led_stat', help='LED status. ', default='fs', choices=['fs', 'fb', 'sb', 'hs'])
    parser.add_argument('-mr', '--max_retry', help='Maximum retry times', type=int, metavar='TIMES', default=10)
    parser.add_argument('-d', '--delay', help='Delay between checking LED status', type=int, metavar='TIME', default=10)

    test = CheckLed(parser.parse_args())
    if test.main():
        sys.exit(0)
    sys.exit(1)
