# -*- coding: utf-8 -*-
""" Tool for waiting for deivce boot completed
"""
# std modules
import logging
import sys
import time
from argparse import ArgumentParser

# platform modules
from platform_libraries.adblib import ADB
from platform_libraries.serial_client import SerialClient

class WaitForBootCompleted(object):

    def __init__(self, parser):
        self.adb = None
        self.serial_client = None
        self.waiting_time = parser.waiting_time

        if parser.ip:
            self.adb = ADB(uut_ip=parser.ip, port=5555)
            self.adb.connect()
        if parser.serial_server_ip:
            self.serial_client = SerialClient(parser.serial_server_ip, parser.serial_server_port, stream_log_level=logging.DEBUG)
            self.serial_client.initialize_serial_port()

    def main(self):
        if self.adb: # via ADB
            time_of_waiting_for_reboot = time_of_waiting_for_boot_up = self.waiting_time
            if self.waiting_time > 60:
                time_of_waiting_for_reboot = 60
                time_of_waiting_for_boot_up = self.waiting_time - 60
            if self.adb.wait_for_device_to_shutdown(timeout=time_of_waiting_for_reboot):
                time.sleep(60*3)  # For MCH, wait for golden mode reboot
            return self.adb.wait_for_device_boot_completed(timeout=time_of_waiting_for_boot_up, time_calibration_retry=False)
        else: # via serial concole
            return self.serial_client.wait_for_boot_complete(timeout=self.waiting_time, raise_error=False)


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Wait for deivce boot completed ***
        """)

    parser.add_argument('-ip', '--ip', help='Destination UUT IP address', metavar='IP')
    parser.add_argument('-ss_ip', '--serial_server_ip', help='Destination serial server IP address', metavar='IP', default=None)
    parser.add_argument('-ss_port', '--serial_server_port', help='Destination UUT serial port', metavar='PORT', default=None)
    parser.add_argument('-t', '--waiting_time', help='Max time to wait for booting up', type=int, metavar='TIME', default=300)

    test = WaitForBootCompleted(parser.parse_args())
    if test.main():
        sys.exit(0)
    sys.exit(1)
