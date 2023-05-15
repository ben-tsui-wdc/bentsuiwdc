__author__ = 'Kurt Jensen <kurt.jensen@wdc.com>'

from platform_libraries.monsoon_wrapper import MonsoonWrapper
import time
import argparse

parser = argparse.ArgumentParser(description='Test script to use monsoon_wrap library')
parser.add_argument('-monsoon_id', help='Monsoon devices address, ex. /dev/ttyACM0')
parser.add_argument('-hz', help='HZ value for averaging current data. Monsoon collects data at 5000 Hz')
parser.add_argument('-minutes', help='Number of minutes to output Vout')
args = parser.parse_args()

if args.monsoon_id:
    monId = args.monsoon_id
else:
    monId = None

if args.hz:
    hz = int(args.hz)
else:
    hz = 10
if args.minutes:
    minutes = int(args.minutes)
else:
    minutes=7

# Monsoon Power object 

try:
    mon = MonsoonWrapper(device=monId, prometheusDevice='monarch_pm')
    #Set vout to 4.2V, turn on usbpassthrough, max current at 8 amps
    mon.setOutputValues(usb=1, vout=4.2, maxCurrent=8)
    # Start logging data at 5hz
    mon.startDataLogging(hz=hz, logstashUpload=True)

    # Log power data for additional time
    for i in range(minutes):
        print i
        time.sleep(60)        
        
        #Kill monsoon data logging thread and disable Vout on Monsoon
    mon.stopDataLogging()
    time.sleep(5)

except KeyboardInterrupt:
    # Disable Monsoon power monitor if interrupted
    mon.stopDataLogging()