___author___ = 'Kurt Jensen <kurt.jensen@wdc.com>'

from platform_libraries.adblib import ADB
from platform_libraries.device_monitor import AndroidDeviceMonitor
import argparse
import time

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reboot test')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    parser.add_argument('-iter', help='Number of iterations, ex. 100')
    args = parser.parse_args()

    uut_ip = args.uut_ip

    if args.port:
        port = args.port
    else:
        port = '5555'
    if args.iter:
        iterations = int(args.iter)
    else:
        iterations = 1
    if args.uut_ip:
        uut_ip = str(args.uut_ip)
    else:
        uut_ip = '10.104.130.111'

    adb = ADB(uut_ip=uut_ip, port='5555')
    adb.connect()
    time.sleep(5)
    adm = AndroidDeviceMonitor(adb=adb)
    adm.run()
    adm.stop()


