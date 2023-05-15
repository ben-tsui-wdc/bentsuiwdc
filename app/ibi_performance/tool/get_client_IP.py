# -*- coding: utf-8 -*-
""" Verify if the WI-Fi connected is preferred.
"""
__author__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
import re
import socket
import sys
import time
import xmlrpclib

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.ssh_client import SSHClient


class GetMacClientIP(TestCase):

    TEST_SUITE = 'GetMacClientIP'
    TEST_NAME = 'GetMacClientIP'

    SETTINGS = {
            'uut_owner': False,
            'disable_firmware_consistency': True,
            'adb': False,
            'power_switch': False,
            }


    def before_test(self):
        self.ssh = SSHClient(self.client_ip, self.client_username, self.client_password)
        self.ssh.connect()


    def test(self):

        # Get Wi-Fi interface name
        status, response = self.ssh.execute('networksetup -listnetworkserviceorder | grep Wi-Fi.*Device')      
        search = re.search('Device:.*[^)]', response)
        if search.group():
            wifi_interface = search.group().split('Device: ')[1]    
        else:
            raise self.err.StopTest('There is not Wi-Fi interface found in client({}):{}.'.format(self.client_os, self.client_ip))        
        self.log.info('{} wifi_interface: {}'.format(self.client_os, wifi_interface))
        
        # Confirm if the Wi-Fi is connected to correct WI-Fi network
        status, response = self.ssh.execute('networksetup  -getairportnetwork {}'.format(wifi_interface)) 
        if self.wifi_ssid in response and 'Current Wi-Fi Network:' in response:
            self.log.info("Current SSID({}) of Wi-Fi connected is correct.".format(self.wifi_ssid))
        else:
            self.log.info('Current SSID of Wi-Fi is not correct, re-connect to specified SSID of Wi-Fi: {}'.format(self.wifi_ssid))
            status, response = self.ssh.execute('networksetup -setairportnetwork {} {} {}'.format(wifi_interface, self.wifi_ssid, self.wifi_password))
            time.sleep(30)

        # Get IP of Wi-Fi interface
        command = "ifconfig {} | grep netmask".format(wifi_interface)
        status, response = self.ssh.execute(command)
        search = re.search('inet \S*', response)
        if search.group():
            wifi_ip = search.group().split('inet ')[1]    
        else:
            raise self.err.StopTest('There is not Wi-Fi ip found in client({}):{}.'.format(self.client_os, self.client_ip))
        self.log.info("{} wifi_ip: {}".format(self.client_os, wifi_ip))

        # Output result
        _write_to_result(result='{}'.format(wifi_ip), output_file='{}_client_ip'.format(self.client_os))


    def after_test(self):
        self.ssh.close()


class GetWinClientIP(TestCase):
    TEST_SUITE = 'GetWinClientIP'
    TEST_NAME = 'GetWinClientIP'

    SETTINGS = {
            'uut_owner': False,
            'disable_firmware_consistency': True,
            'adb': False,
            'power_switch': False,
            }


    def before_test(self):
        pass


    def test(self):
        # Confirm if the Wi-Fi is connected to correct WI-Fi network
        result = self._XMLRPCclient('netsh wlan show interfaces')
        if "connected" in result and self.wifi_ssid in result:
            self.log.info("Current SSID({}) of Wi-Fi connected is correct.".format(self.wifi_ssid))
        else:
            self.log.info('Current SSID of Wi-Fi is not correct, re-connect to specified SSID of Wi-Fi: {}'.format(self.wifi_ssid))
            for i in xrange(4):
                result = self._XMLRPCclient('netsh wlan connect ssid={} name={}'.format(self.wifi_ssid, self.wifi_ssid))
                if 'Connection request was completed successfully' in result:
                    time.sleep(30)
                    self.log.info('Launch XMLRPCServer.py in Windows client')
                    result = self._XMLRPCclient("%HOMEPATH%\\Desktop\\XMLRPCserver_10_200.py")
                    break
                elif i == 3:
                    raise self.err.StopTest('Failed to re-connect to SSID({}) of Wi-Fi'.format(self.wifi_ssid))
                time.sleep(5)

        # Get IP of Wi-Fi interface
        result = self._XMLRPCclient('netsh interface ip show address "Wi-Fi" | findstr "IP Address"')
        if result:
            wifi_ip = result.split()[2]
        else:
            raise self.err.StopTest('There is not Wi-Fi ip found in client({}):{}.'.format(self.client_os, self.client_ip))
        self.log.info("{} wifi_ip: {}".format(self.client_os, wifi_ip))

        # Output result
        _write_to_result(result='{}'.format(wifi_ip), output_file='{}_client_ip'.format(self.client_os))


    def _XMLRPCclient(self, cmd):
        for i in xrange(4):
            try:
                print "{0} \r\n".format(cmd)
                server = xmlrpclib.ServerProxy("http://{}:12345/".format(self.client_ip))
                result = server.command(cmd)  # server.command() return the result which is in string type.
                print result
                return result
            except socket.error as e:
                e = str(e)
                if i < 4:
                    print "socket.error: {0}\nCould not connect with the socket-server: {1}".format(e, self.client_ip)
                    print "\r\nretry #{}".format(i+1)
                    time.sleep(3)
                else:
                    raise self.err.StopTest("error message: {}".format(e))


def _write_to_result(result=None, output_file='client_ip'):
    try:
        with open('/root/app/output/{}'.format(output_file), 'w') as f:
            f.write('{}\r\n'.format(result))
    except:
        with open(output_file, 'w') as f:
            f.write('{}\r\n'.format(result))


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** To get Wi-Fi IP address of Windows/Mac client ***
        Examples: ./run.sh get_client_ip.py --uut_ip 10.92.224.68\
        """)

    parser.add_argument('--client_os', help='Client OS type', default='MAC', choices=['WIN', 'MAC'])
    parser.add_argument('--client_ip', help='Client OS ip address', default=None)
    parser.add_argument('--client_username', help='Username to login client OS', default='lserranov')  # for MAC
    parser.add_argument('--client_password', help='The password os client user', default="Abcd1234!")  # for MAC
    parser.add_argument('--wifi_ssid', help='The SSID of Wi-Fi which is preferred to connect to', default="MV-Warrior")
    parser.add_argument('--wifi_password', help='The password of Wi-Fi SSID which is preferred to connect to', default="gQJ2bQJt3MKSfH77sSNJ")
    args = parser.parse_args()

    if args.client_os == 'WIN':
        test = GetWinClientIP(parser)
    elif args.client_os == 'MAC':
        test = GetMacClientIP(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)  
