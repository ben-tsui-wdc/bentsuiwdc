__author__ = 'Kurt Jensen <kurt.jensen@wdc.com>'

from platform_libraries.adblib import ADB
from platform_libraries.monsoon_wrapper import MonsoonWrapper
import time
import argparse

parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
parser.add_argument('-monsoon_id', help='Monsoon devices address, ex. /dev/tty.usbmodem1421')
args = parser.parse_args()
uut_ip = args.uut_ip

if args.monsoon_id:
    monId = args.monsoon_id
else:
    monId = '/dev/tty.usbmodem1411'



try:
    # Monsoon Power object 
    mon = MonsoonWrapper()

    # Set vout to 4.2V, turn on usbpassthrough, max current at 8 amps
    mon.setOutputValues(usb=1, vout=4.2, maxCurrent=8)
	# Start logging data at 6hz
    mon.startDataLogging(hz=10)
    
    # sleep statement is to allow device to boot up, or adb commands will fail
    time.sleep(30)

    # adb object to connect to device and execute commands
    adb = ADB(uut_ip=uut_ip,port='5555')
    
    # Connect to device via defined ip address:ports
    # Will automatically start the adb-server if not started
    adb.connect()

    # Execute shell command and return stdout, stderr
    # Default is to print console output of command, this can be disabled with consoleOutput=False parameter
    # Default is timeout=60s
    stdout, stderr = adb.executeShellCommand('ls', consoleOutput=True)

    # Put device in low power mode
    adb.executeShellCommand('input keyevent 26')
    # Disconnect device from adb-server
    adb.disconnect()
    adb.killServer()     
    for i in range(0, 5):
        time.sleep(60)
    #Kill monsoon data logging thread and disable Vout on Monsoon
    mon.stopDataLogging()

except KeyboardInterrupt:
	# Disable Monsoon power monitor if interrupted
    mon.stopDataLogging()