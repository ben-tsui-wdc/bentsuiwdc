___author___ = 'Kurt Jensen <kurt.jensen@wdc.com>'

from platform_libraries.adblib import ADB
import time
import argparse

parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
parser.add_argument('-server_ip', help='Destination adb server IP address, ex. 192.168.203.14')
parser.add_argument('-server_port', help='Destination adb server port number, ex. 5555 (default)')
args = parser.parse_args()

uut_ip = args.uut_ip
if args.port:
    devicePort = args.port
else:
    devicePort = '5555'
if args.server_port:
    adbServerPort = args.server_port
else:
    adbServerPort = None
if args.server_ip:
    adbServer = args.server_ip
else:
    adbServer = None

try:
    # adb object to connect to device and execute commands
    adb = ADB(adbServer=adbServer, adbServerPort=adbServerPort, uut_ip=uut_ip, port=devicePort)
    # Connect to device via defined ip address:port
    adb.connect()

    # Execute command and return stdout, stderr
    # Default is to print console output of command, this can be disabled with consoleOutput=False parameter
    # Default is timeout=60s
    stdout, stderr = adb.executeShellCommand('ls', consoleOutput=True)

    print stdout
    time.sleep(1)

    # Copy file from local machine to ADB connected device
    #adb.push(local='testfile', remote='/data')
    # Copy file from ADB connected device to local machine
    #adb.pull(remote='/data/testfile', local='/output')
    # Disconnect from device
    adb.disconnect()      


except KeyboardInterrupt:
    adb.disconnect()
    print 'Exiting!'