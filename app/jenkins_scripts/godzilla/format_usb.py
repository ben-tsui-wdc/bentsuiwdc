# -*- coding: utf-8 -*-
""" Tool for format USB.
"""
# std modules
from argparse import ArgumentParser

# platform modules
from platform_libraries.mcci_client import MCCIAPI
from platform_libraries.ssh_client import SSHClient


class FormatUSB(object):

    def __init__(self, parser):
        self.usb_format = parser.usb_format
        self.mcci = None
        self.ssh_client = SSHClient(parser.ssh_ip, parser.ssh_user, parser.ssh_password, parser.ssh_port)
        self.ssh_client.connect()

        if parser.url and (parser.serno or parser.device):
            self.mcci = MCCIAPI(parser.url)
            self.serno = parser.serno
            self.device = parser.device

    def main(self):
        # Check attached USB drive.
        usbs = self.ssh_client.get_usb_format()
        if not usbs: raise self.err.StopTest("USB not found")
        usb_format = usbs.values()[0] # Expect one USB driver attached.
        self.ssh_client.log.info("USB format: {}".format(usb_format))

        # Check USB format.
        if usb_format != self.usb_format:
            # Format USB and push data set.
            self.ssh_client.format_usb(self.usb_format, reattach_func=self.reattach_usb3 if self.mcci else None)

    def reattach_usb3(self):
        self.mcci.reattach_usb3(serno=self.serno, device=self.device)


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Format USB. 
        MCCI server is optional which is for speed up the process.
        ***
        """)

    parser.add_argument('-uf', '--usb_format', help='USB type to format', default='TYPE', choices=['fat32', 'hfs+', 'ntfs', 'exfat'], required=True)
    parser.add_argument('-ssh_ip', '--ssh_ip', help='The hostname of SSH server', metavar='IP', required=True)
    parser.add_argument('-ssh_user', '--ssh_user', help='The username of SSH server', default="sshd")
    parser.add_argument('-ssh_password', '--ssh_password', help='The password of SSH server', metavar='PWD', default="Test1234")
    parser.add_argument('-ssh_port', '--ssh_port', help='The port of SSH server', type=int, metavar='PORT', default=22)
    parser.add_argument('-u', '--url', help='MCCI server URL', metavar='PATH')
    parser.add_argument('-s', '--serno', help='Serail number of MCCI device', metavar='serno', default=None)
    parser.add_argument('-d', '--device', help='Device number of MCCI device', metavar='device', default=None)

    FormatUSB(parser.parse_args()).main()
