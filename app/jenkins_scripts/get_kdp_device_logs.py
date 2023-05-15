# -*- coding: utf-8 -*-
""" Tool for getting logs from KDP device.
"""
# std modules
import logging
from argparse import ArgumentParser

# platform modules
from platform_libraries.ssh_client import SSHClient
from platform_libraries.serial_client import SerialClient

class KDPDeviceLogGetter(object):

    def __init__(self, parser):
        self.ssh_client = None
        self.log_path = parser.path
        self.clean_logs = parser.clean_logs

        self.ssh_client = SSHClient(parser.ssh_ip, parser.ssh_user, parser.ssh_password, parser.ssh_port)
        self.serial_client = None
        if (not parser.ssh_ip or not self.ssh_client.check_device_pingable()) and parser.serial_server_ip and parser.serial_server_port:
            self.serial_client = SerialClient(parser.serial_server_ip, parser.serial_server_port, stream_log_level=logging.DEBUG)
            self.serial_client.initialize_serial_port()
            current_ip = self.serial_client.retry_for_connect_WiFi_kdp(parser.ssid, parser.wifi_password, try_time=10, interval_secs=5)
            if not current_ip:
                raise RuntimeError("Fail to connect to network")
            self.ssh_client.hostname = current_ip
        if not self.ssh_client.hostname:
            raise RuntimeError("No specify device IP")
        self.ssh_client.connect()

    def main(self):
        self.ssh_client.save_kdp_device_logs(file_name=self.log_path)
        #if self.clean_logs: self.ssh_client.clean_device_logs()
        self.ssh_client.close()
        if self.serial_client: self.ssh_client.close()
        # Disable netowrk if need. Reset device vis SSH while test is failed in normal.


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Get logcat from KDP device ***
        """)

    parser.add_argument('-p', '--path', help='File path to save device log', metavar='PATH', default='/root/app/output/logs.tgz')
    parser.add_argument('-ssh_ip', '--ssh_ip', help='The hostname of SSH server', metavar='IP')
    parser.add_argument('-ssh_user', '--ssh_user', help='The username of SSH server', default="root")
    parser.add_argument('-ssh_password', '--ssh_password', help='The password of SSH server', metavar='PWD', default="")
    parser.add_argument('-ssh_port', '--ssh_port', help='The port of SSH server', type=int, metavar='PORT', default=22)
    parser.add_argument('-ss_ip', '--serial_server_ip', help='Destination serial server IP address', metavar='IP', default=None)
    parser.add_argument('-ss_port', '--serial_server_port', help='Destination UUT serial port', metavar='PORT', default=None)
    parser.add_argument('-ssid', '--ssid', help='SSID of new network', default=None)
    parser.add_argument('-wifi_password', '--wifi_password', help='Password of new network', default=None)
    parser.add_argument('-c', '--clean_logs', help='clean logs after getting logs', action='store_true', default=False)

    test = KDPDeviceLogGetter(parser.parse_args())
    test.main()
