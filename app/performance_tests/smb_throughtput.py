__author__  = 'Jason'

from xmlrpclib import ServerProxy
import argparse
import json
import os
import re
import requests
import socket
import time

from platform_libraries import common_utils
from platform_libraries.adblib import ADB


def XMLRPCclient(cmd):
    try:
        server = ServerProxy("http://{}:12345/".format(windows_client_ip))
        return server.command(cmd)  # server.command() return the result which is in string type.
    except socket.error as e:
        e = str(e)
        print "socket.error: {0}\nCould not connect with the socket-server: {1}".format(e, windows_client_ip)


class smb_throughput(object):
    def __init__(self):
        self.log = common_utils.create_logger(overwrite=False)
        if without_adb:
            self.product = None
            self.version = None
        else:
            if adbserver:
                self.adb = ADB(adbServer='10.10.10.10', adbServerPort='5037', uut_ip=uut_ip, port=port)
            else:
                self.adb = ADB(uut_ip=uut_ip, port=port)
            self.adb.connect()
            self.adb.stop_otaclient()
            self.product = self.adb.getModel()
            self.version = self.adb.getFirmwareVersion().split()[0]
        self.logstash_server = 'http://{0}'.format(logstash)

    def upload_result(self, iteration=None, SINGLE_WRITE_speed=None, SINGLE_READ_speed=None, STANDARD_WRITE_speed=None, STANDARD_READ_speed=None):
         # For Report Sequence
        if iteration < 10:
           iteration = '{}_itr_0{}'.format(self.version, iteration)
        else:
           iteration = '{}_itr_{}'.format(self.version, iteration)

        headers = {'Content-Type': 'application/json'}
        data = {'testName': "kpi_windows_samba",
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
            response = requests.post(url=self.logstash_server, data=json.dumps(data), headers=headers)
            if response.status_code == 200:
                print 'Uploaded JSON results to logstash server {}'.format(self.logstash_server)
            else:
                raise Exception('Upload to logstash server {0} failed, {1}, error message: {2}'.format(self.logstash_server, response.status_code, response.content))
            

    def mount(self):
        #cmd = 'NET USE {0}: \\\\{1}\Public /user:guest'.format(windows_mount_point, uut_ip)
        self.log.info("Wait 180 seconds for Disk Initialization after factory_reset before mounting NAS drive")
        time.sleep(180)

        cmd = 'NET USE {0}: \\\\{1}\Public'.format(windows_mount_point, uut_ip)
        result = XMLRPCclient(cmd)
        print "\n### mount ###\n"
        print "{0}".format(cmd)
        print result


    def umount(self):
        cmd = 'NET USE /delete {0}: /y;'.format(windows_mount_point)
        result = XMLRPCclient(cmd)
        print "\n### umount ###\n"
        print "{0}".format(cmd)
        print result


    def run(self):
        # Search pattern for transfer speed.
        pattern = '(\d+)\sBytes/sec'
        
        print "\n### SMB performance test is being executed ... ###\n"

        for iteration in xrange(1, iterations+1):

            # Remove SMBTestFolders from NAS and client.
            cmd = "Remove-Item -Recurse -Force {0}:\\SMBTestFolder_client; Remove-Item -Recurse -Force {1}:\\SMBTestFolder_NAS".format(windows_drive_letter, windows_mount_point)
            result = XMLRPCclient(cmd)

            # Create test folder on NAS and client, respectively.
            cmd = "New-Item -type directory {0}:\\SMBTestFolder_NAS; New-Item -type directory {1}:\\SMBTestFolder_client".format(windows_mount_point, windows_drive_letter)
            result = XMLRPCclient(cmd)

            # Single write, namely, copy files from client to NAS.
            cmd = "robocopy {0}:\\5G_Single {1}:\\SMBTestFolder_NAS /E /NP /NS /NC /NFL /NDL /R:1 /W:1".format(windows_drive_letter, windows_mount_point)
            result = XMLRPCclient(cmd)
            print "{0}".format(cmd)
            print result
            match = re.search(pattern, result)
            if match:
                speed = match.group(1)
                speed = float(speed) / float(1024*1024)  # Convert Bytes/sec to MB/sec.
                SINGLE_WRITE_speed = '{}'.format(round(speed, 2))
            else:
                # Error handle when there is no XXX Bytes/sec displayed.
                print "Error handle" 

            # Single read, namely, copy files from NAS to client.
            cmd = "robocopy {0}:\\SMBTestFolder_NAS {1}:\\SMBTestFolder_client /E /NP /NS /NC /NFL /NDL /R:1 /W:1".format(windows_mount_point, windows_drive_letter)
            result = XMLRPCclient(cmd)
            print "{0}".format(cmd)
            print result
            match = re.search(pattern, result)
            if match:
                speed = match.group(1)
                speed = float(speed) / float(1024*1024)  # Convert Bytes/sec to MB/sec.
                SINGLE_READ_speed = '{}'.format(round(speed, 2))
            else:
                # Error handle when there is no XXX Bytes/sec displayed.
                print "Error handle" 

            # Remove SMBTestFolders from NAS and client.
            #cmd = "RMDIR /S /Q C:\\SMBTestFolder_client;  RMDIR /Q /S {0}:\\SMBTestFolder_NAS".format(windows_mount_point)
            cmd = "Remove-Item -Recurse -Force {0}:\\SMBTestFolder_client; Remove-Item -Recurse -Force {1}:\\SMBTestFolder_NAS".format(windows_drive_letter, windows_mount_point) 
            result = XMLRPCclient(cmd)

            # Create test folder on NAS and client, respectively.
            cmd = "New-Item -type directory {0}:\\SMBTestFolder_NAS; New-Item -type directory {1}:\\SMBTestFolder_client".format(windows_mount_point, windows_drive_letter)
            result = XMLRPCclient(cmd)

            # Standard write, namely, copy files from client to NAS.
            cmd = "robocopy {0}:\\5G_Standard {1}:\\SMBTestFolder_NAS /E /NP /NS /NC /NFL /NDL /R:1 /W:1".format(windows_drive_letter, windows_mount_point)
            result = XMLRPCclient(cmd)
            print "{0}".format(cmd)
            print result
            match = re.search(pattern, result)
            if match:
                speed = match.group(1)
                speed = float(speed) / float(1024*1024)  # Convert Bytes/sec to MB/sec.
                STANDARD_WRITE_speed = '{}'.format(round(speed, 2))
            else:
                # Error handle when there is no XXX Bytes/sec displayed.
                print "Error handle" 

            # Standard read, namely, copy files from NAS to client.
            cmd = "robocopy {0}:\\SMBTestFolder_NAS {1}:\\SMBTestFolder_client /E /NP /NS /NC /NFL /NDL /R:1 /W:1".format(windows_mount_point, windows_drive_letter)
            result = XMLRPCclient(cmd)
            print "{0}".format(cmd)
            print result
            match = re.search(pattern, result)
            if match:
                speed = match.group(1)
                speed = float(speed) / float(1024*1024)  # Convert Bytes/sec to MB/sec.
                STANDARD_READ_speed = '{}'.format(round(speed, 2))
            else:
                # Error handle when there is no XXX Bytes/sec displayed.
                print "Error handle" 

            # Remove SMBTestFolders from NAS ans client.
            #cmd = "RMDIR /S /Q C:\\SMBTestFolder_client;  RMDIR /Q /S {0}:\\SMBTestFolder_NAS".format(windows_mount_point)
            cmd = "Remove-Item -Recurse -Force {0}:\\SMBTestFolder_client; Remove-Item -Recurse -Force {1}:\\SMBTestFolder_NAS".format(windows_drive_letter, windows_mount_point) 
            result = XMLRPCclient(cmd)
 
            self.upload_result(iteration=iteration, SINGLE_WRITE_speed=SINGLE_WRITE_speed, SINGLE_READ_speed=SINGLE_READ_speed, STANDARD_WRITE_speed=STANDARD_WRITE_speed, STANDARD_READ_speed=STANDARD_READ_speed)


    def CreateFolder():
        pass


    def RemoveFolder():
        pass

    def Robocopy():
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test script for SMB performance')
    parser.add_argument('--uut_ip', help='Destination IP address, ex. 10.136.128.200')
    parser.add_argument('--port', help='Destination port number', default='5555')
    parser.add_argument('--iterations', help='number of iterations, by default is 10', default=10)
    parser.add_argument('--windows_client_ip', help='Windows client IP')
    parser.add_argument('--windows_drive_letter', help='The location of dataset, by default is C', default='C')
    parser.add_argument('--windows_mount_point', help='Windows mount point of NAS share, by default is Z', default='Z')
    parser.add_argument('--adbserver', help='Use public adbserver if using "--adbserver"', action='store_true')
    parser.add_argument('--without_adb', help='Don\'t use adb to connect with NAS', action='store_true')
    parser.add_argument('--dry_run', help='Will not upload result to logstash if using "--dry_run"', action='store_true')
    parser.add_argument('--logstash', help='logstash_server IP and port, by default is 10.92.234.101:8000', default='10.92.234.101:8000')
    parser.add_argument('--wifi_mode', help='type of wifi mode, by default is None', choices=['None','2.4G', '5G'], default='None')
    args = parser.parse_args()

    if not args.uut_ip:
        print "\nPlease enter the test device IP address!\n"
        sys.exit(1)
    
    # Assign arguments to variables.
    uut_ip = args.uut_ip
    port = args.port
    iterations = int(args.iterations)
    windows_client_ip = args.windows_client_ip
    windows_drive_letter = args.windows_drive_letter
    windows_mount_point = args.windows_mount_point
    adbserver = args.adbserver  
    without_adb = args.without_adb
    dry_run = args.dry_run
    logstash = args.logstash
    wifi_mode = args.wifi_mode

    # Create an object.
    SMB_object = smb_throughput()

    # Actions.
    SMB_object.umount()  # Clear the environment of Windows client
    SMB_object.mount()   # Mount the NAS share to Windows client
    SMB_object.run()     # Execute performance test
    SMB_object.umount()  # Restore the environment of Windows client
    