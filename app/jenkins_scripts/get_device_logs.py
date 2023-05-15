# -*- coding: utf-8 -*-
""" Tool for getting logcat logs from device.
"""
# std modules
import logging
from argparse import ArgumentParser

# platform modules
from platform_libraries.adblib import ADB
from platform_libraries.serial_client import SerialClient

class DeviceLogGetter(object):

    def __init__(self, parser):
        self.adb = None
        self.serial_client = None
        self.log_path = parser.path
        self.clean_logcat = parser.clean_logcat

        if parser.ip:
            self.adb = ADB(uut_ip=parser.ip, port=5555)
            self.adb.connect()
        if parser.serial_server_ip:
            self.serial_client = SerialClient(parser.serial_server_ip, parser.serial_server_port, stream_log_level=logging.DEBUG)
            self.serial_client.initialize_serial_port()
            try:
                self.serial_client.logger.info('Device IP checking...')
                current_ip = self.serial_client.get_ip()
                if not current_ip or current_ip == '192.168.43.1':
                    return
                self.adb = ADB(uut_ip=current_ip, port=5555)
                self.adb.connect()
            except Exception, e:
                self.serial_client.logger.warning('Error found during getting IP: {}'.format(e), exc_info=True)

    def main(self):
        if self.adb: # via ADB
            self.adb.logcat_to_file(file_name=self.log_path)
            if self.clean_logcat:
                self.adb.clean_logcat()
        else: # via serial concole
            self.serial_client.export_logcat(path=self.log_path, read_timeout=60*10)
            # or save logcat to attached USB.
            if self.clean_logcat:
                self.serial_client.clean_logcat()


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Get logcat logs from device ***
        """)

    parser.add_argument('-p', '--path', help='File path to save device log', metavar='PATH', default='log.logcat')
    parser.add_argument('-ip', '--ip', help='Destination UUT IP address', metavar='IP')
    parser.add_argument('-ss_ip', '--serial_server_ip', help='Destination serial server IP address', metavar='IP', default=None)
    parser.add_argument('-ss_port', '--serial_server_port', help='Destination UUT serial port', metavar='PORT', default=None)
    parser.add_argument('-c', '--clean_logcat', help='clean logcat after getting logs', action='store_true', default=False)

    test = DeviceLogGetter(parser.parse_args())
    test.main()
