___author___ = 'Jason Chiang <jason.chiang@wdc.com>'

import xmlrpclib
import argparse
import json
import os
import re
import requests
import socket
import sys
import time

from platform_libraries import common_utils
from platform_libraries.adblib import ADB
from platform_libraries.restAPI import RestAPI


def XMLRPCclient(cmd):
    try:
        print "{0} \r\n".format(cmd)
        server = xmlrpclib.ServerProxy("http://{}:12345/".format(windows_client_ip))
        result = server.command(cmd)  # server.command() return the result which is in string type.
        print result
        return result
    except socket.error as e:
        e = str(e)
        print "socket.error: {0}\nCould not connect with the socket-server: {1}".format(e, windows_client_ip)
        print "error message: {}".format(e)
        return e

class desktopapp_throughput(object):
    def __init__(self):
        self.log = common_utils.create_logger(overwrite=False)
        if adbserver:
            self.adb = ADB(adbServer='10.10.10.10', adbServerPort='5037', uut_ip=uut_ip, port=port)
        else:
            self.adb = ADB(uut_ip=uut_ip, port=port)
        self.adb.connect()
        self.adb.stop_otaclient()
        self.product = self.adb.getModel()
        self.REST_API = RestAPI(uut_ip=uut_ip, env=env, username=user, password=pw, init_session=False)
        self.REST_API.init_session(client_settings={'config_url': self.adb.get_config_url()}, with_cloud_connected=False)





        self.REST_API.set_global_timeout(timeout=None)  # Cancel the module "socket" timeout because the reponse time via socket is not fixed.
        self.logstash_server = 'http://{0}'.format(logstash)

    def upload_result(self, iteration=None, SINGLE_WRITE_speed=None, SINGLE_READ_speed=None, STANDARD_WRITE_speed=None, STANDARD_READ_speed=None):

        self.version = self.adb.getFirmwareVersion().split()[0]
        
        # For Report Sequence
        if iteration < 10:
           iteration = '{}_itr_0{}'.format(self.version, iteration)
        else:
           iteration = '{}_itr_{}'.format(self.version, iteration)

        headers = {'Content-Type': 'application/json'}
        data = {'testName': "kpi_desktop_app_throughput",
                'product': self.product,
                'build': self.version,
                'iteration': iteration,
                'single_write': float(SINGLE_WRITE_speed),
                'single_read': float(SINGLE_READ_speed),
                'standard_write': float(STANDARD_WRITE_speed),
                'standard_read': float(STANDARD_READ_speed),
                'wifi_mode':wifi_mode}

        print 'logstash_server: {0}'.format(self.logstash_server)
        print data

        if dry_run:
            print "\n### Do not upload ###\n"
        else:
            print "\n### upload ###\n"
            retry = 20
            for i in xrange(retry):
                try:
                    response = requests.post(url=self.logstash_server, data=json.dumps(data), headers=headers, timeout=10)
                    if response.status_code == 200:
                        print 'Uploaded JSON results to logstash server {}'.format(self.logstash_server)
                        break
                    else:
                        print 'response.status_code:{}, response.content:{}'.format(response.status_code, response.content)
                except Exception as e:
                    if i == retry -1:
                        raise
                    print e
                    print "\nWait 3 seconds and retry #{} to upload JSON result to logstash server".format(i+1)
                    time.sleep(3)

    def reboot_client(self):
        result = XMLRPCclient("Restart-Computer")
        temp = time.time()
        while True:
            time.sleep(30)
            result = XMLRPCclient('ipconfig')  # Just check if the XMLRPCserver is running.
            if "Connection refused" in result or "No route to host" in result or "Connection timed out" in result:
                print '\nWait for Windows rebooting\n'
            else:
                break
            if (time.time() - temp) > 300:
                self.log.error("Windows cannot be rebooted or XMLRPCserver is failed to launch.")
                break
        self.log.info("Windows rebooting finished")

        result = XMLRPCclient('Start-Process ".\WD-Discovery\WD Discovery\Launch WD Discovery.exe"')
        time.sleep(30)  # Wait until WD Discovery is launched.

    def run(self):
        self.log.info("Wait 300 seconds for Disk Initialization after factory_reset and sometimes the cloud will take more than 3 minutes to mount CBFS drive.")
        time.sleep(300)
        print "\n### WebDAV performance test is being executed ... ###\n"

        for iteration in xrange(starting_value, iterations+1):
            '''
            To avoid the cache that may affect the performance, reboot the Windows client before every iteration starts.
            '''
            #self.reboot_client()

            self._delete_test_folder("{}:\\WebDAVTestFolder_NAS".format(windows_mount_point))
            self._delete_test_folder("{}:\\WebDAVTestFolder_Windows".format(windows_drive_letter))

            self._create_test_folder("{}:\\WebDAVTestFolder_NAS".format(windows_mount_point))
            self._create_test_folder("{}:\\WebDAVTestFolder_Windows".format(windows_drive_letter))

            '''
            MD5_original = self.MD5("{}:\\5G_Single\\*".format(windows_drive_letter))
            '''
            # Copy the single file from Windows to NAS.
            SINGLE_WRITE_speed = self.robocopy('{}:\\5G_Single'.format(windows_drive_letter), '{}:\\WebDAVTestFolder_NAS'.format(windows_mount_point))
            '''
            if self.MD5('{}:\\WebDAVTestFolder_NAS\\*'.format(windows_mount_point)) != MD5_original:
                self.error_handle('MD5 checksum compare error occurred after SINGLE_WRITE.')
            '''
            # Copy the single file from NAS to Windows.
            SINGLE_READ_speed = self.robocopy('{}:\\WebDAVTestFolder_NAS'.format(windows_mount_point), '{}:\\WebDAVTestFolder_Windows'.format(windows_drive_letter))
            '''
            if self.MD5('{}:\\WebDAVTestFolder_Windows\\*'.format(windows_drive_letter)) != MD5_original:
                self.error_handle('MD5 checksum compare error occurred after SINGLE_READ.')
            '''

            self._delete_test_folder("{}:\\WebDAVTestFolder_NAS".format(windows_mount_point), error_check=True)
            self._delete_test_folder("{}:\\WebDAVTestFolder_Windows".format(windows_drive_letter), error_check=True)

            self._create_test_folder("{}:\\WebDAVTestFolder_NAS".format(windows_mount_point))
            self._create_test_folder("{}:\\WebDAVTestFolder_Windows".format(windows_drive_letter))

            # Copy the standard files from Windows to NAS.
            STANDARD_WRITE_speed = self.robocopy('{}:\\{}'.format(windows_drive_letter, standard_folder), '{}:\\WebDAVTestFolder_NAS'.format(windows_mount_point))

            # Copy the standard files from NAS to Windows.
            STANDARD_READ_speed = self.robocopy('{}:\\WebDAVTestFolder_NAS'.format(windows_mount_point), '{}:\\WebDAVTestFolder_Windows'.format(windows_drive_letter))

            self._delete_test_folder("{}:\\WebDAVTestFolder_NAS".format(windows_mount_point), error_check=True)
            self._delete_test_folder("{}:\\WebDAVTestFolder_Windows".format(windows_drive_letter), error_check=True)

            '''
            STANDARD_WRITE_speed = 0
            STANDARD_READ_speed = 0
            '''
            self.upload_result(iteration=iteration, SINGLE_WRITE_speed=SINGLE_WRITE_speed, SINGLE_READ_speed=SINGLE_READ_speed, STANDARD_WRITE_speed=STANDARD_WRITE_speed, STANDARD_READ_speed=STANDARD_READ_speed)

    def _create_test_folder(self, folder):
        cmd = "New-Item -type directory {0}".format(folder)
        result = XMLRPCclient(cmd)


    def _delete_test_folder(self, folder, error_check=None):
        cmd = "Remove-Item -Recurse -Force {}".format(folder) 
        result = XMLRPCclient(cmd)
        if error_check:
            if "Cannot find path" in result:
                self.error_handle("Cannot find path '{}' because it does not exist.".format(folder))


    def robocopy(self, source, destination):
        retry = 3
        for x in xrange(retry):
            cmd = "robocopy {0} {1} /E /NP /NS /NC /NFL /NDL /W:1 /COPY:D /R:0".format(source, destination)
            result = XMLRPCclient(cmd)
            match = re.search('(\d+)\sBytes/sec', result)
            if match:
                speed = match.group(1)
                speed = float(speed) / float(1024*1024)  # Convert Bytes/sec to MB/sec.
                MB_per_second = '{}'.format(round(speed, 2))
                return MB_per_second
            else:
                if x == retry - 1:
                    self.error_handle('Error occurred while robocopy, there is no XXX Bytes/sec displayed after retrying {} times.'.format(retry))
                else:
                    time.sleep(5)


    def error_handle(self, message):
        self.log.error(message)
        sys.exit(1)


    def MD5(self, file_path):
        cmd = "Get-FileHash {} -Algorithm MD5 | Format-List".format(file_path)
        result = XMLRPCclient(cmd)
        if result:
            MD5 = result.split('Hash      : ')[1].split('\nPath')[0]
            return MD5
        else:
            self.log.error_handle("Error occurred while calculating MD5 of '{}'".format(file_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test script for WebDAV performance')
    parser.add_argument('--uut_ip', help='Destination IP address, ex. 10.136.128.200')
    parser.add_argument('--env', help='Cloud test environment', default='dev1', choices=['dev1', 'qa1', 'prod'])
    parser.add_argument('--port', help='Destination port number', default='5555')
    parser.add_argument('--starting_value', help='The starting value of iteration, by default is 1', default=1)
    parser.add_argument('--iterations', help='number of iterations, by default is 10', default=10)
    parser.add_argument('--windows_client_ip', help='Windows client IP, by default is 192.168.1.137', default='192.168.1.137')
    parser.add_argument('--windows_drive_letter', help='The location of dataset, by default is C', default='C')
    parser.add_argument('--windows_mount_point', help='Windows mount point of NAS share, by default is Z', default='Z')
    parser.add_argument('--standard_folder', help='standard(multiple) files folder name', default='5G_Standard')
    parser.add_argument('--user', help='The username of owner attached in test device', default='desktopappwin2@test.com')
    parser.add_argument('--pw', help='The password of owner attached in test device', default='Wdctest1234')
    parser.add_argument('--adbserver', help='Use public adbserver if using "--adbserver"', action='store_true')
    parser.add_argument('--dry_run', help='Will not upload result to logstash if using "--dry_run"', action='store_true')
    parser.add_argument('--logstash', help='logstash_server IP and port, by default is 10.92.234.101:8000', default='10.92.234.101:8000')
    parser.add_argument('--wifi_mode', help='type of wifi mode, by default is None', choices=['None','2.4G', '5G'], default='None')
    args = parser.parse_args()

    # Assign arguments to variables.
    uut_ip = args.uut_ip
    env = args.env
    port = args.port
    starting_value = int(args.starting_value)
    iterations = int(args.iterations)
    windows_client_ip = args.windows_client_ip
    windows_drive_letter = args.windows_drive_letter
    windows_mount_point = args.windows_mount_point
    standard_folder = args.standard_folder
    user = args.user
    pw = args.pw
    adbserver = args.adbserver   
    dry_run = args.dry_run
    logstash = args.logstash
    wifi_mode = args.wifi_mode

    # Create an object.
    WebDAV_object = desktopapp_throughput()

    # Actions.
    WebDAV_object.run()     # Execute performance test