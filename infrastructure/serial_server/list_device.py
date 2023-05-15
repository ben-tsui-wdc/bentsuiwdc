# -*- coding: utf-8 -*-
""" Simple tool to list all device.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import argparse
import json
import os
import sys
import telnetlib
import time
import re

def print_without_new_line(msg):
    print '\r'+' '*90+'\r',
    sys.stdout.flush()
    print msg,
    sys.stdout.flush()

def show_device_info(server_ip, port, console_password=None):
    try:
        print_without_new_line('Port {0}: connecting...'.format(port))
        tn = telnetlib.Telnet(server_ip, port)
        print_without_new_line('\rPort {0}: accessing device...'.format(port))
        mtype = guess_model_by_PS(tn, console_password)
        if mtype == 0:
            platform = 'RaspberryPi'
            ip = show_OS3_ip(tn)
            mac = show_mac(tn, platform)
        elif mtype == 1:
            platform = show_OS4_platform(tn)
            ip = show_ip(tn)
            mac = show_mac(tn, platform)
        elif mtype == 2:
            platform = show_Linux_platform(tn)
            ip = show_OS3_ip(tn)
            mac = show_mac(tn, platform)
        elif mtype == 3:
            platform = 'Sequoia'
            ip = show_Sequoia_ip(tn)
            mac = show_mac(tn, platform)
        else:
            platform = 'Unknown'
            ip = 'Unknown'
            mac = 'Unknown'
        tn.close()
        print_without_new_line('\rPort {0} => {1}: {2} ({3})\n'.format(port, platform, ip, mac))
        return port, platform, ip, mac.upper()
    except:
        #import traceback
        #print traceback.format_exc()
        print_without_new_line('\rPort {0}: might occupied by someone.\n'.format(port))
        return None

def read_until(tn, re_pattern=None, timeout=10, raise_error=True, ignore_ps_line=False):
    start_time = time.time()
    while True:
        string = tn.read_until('\n', timeout=1)
        if ignore_ps_line:
            if '#' in string:
                continue
        if re_pattern:
            matches = re.findall(re_pattern, string)
            if matches:
                return matches.pop()
        else:
            # Wait for some message.
            if string.replace('\n', '').replace('\r', ''):
                return string
        if time.time() - start_time > timeout:
            if raise_error:
                raise RuntimeError('Read timeout.')
            else:
                return ''

def send_and_get_first_line(tn, cmd, timeout=20):
    tn.write(cmd)
    try:
        output = tn.read_until('\n', timeout=3)
        # check first line, some device only has 1 line
        line = output.strip()
        if '@' in line and (line.endswith('$') or line.endswith('#')):
            return output
        # consume sent cmd and return next line
        return tn.read_until('\n', timeout)
    except Exception as e:
        # 'Waiting cmd response timeout'
        return ''

def guess_model_by_PS(tn, console_password=None):
    # Clear screen.
    reset_command_line(tn, console_password)
    # Check PS.
    print_without_new_line('\rChecking device type...')
    tn.write("\n")
    string = read_until(tn, timeout=3)
    if 'pi@r' in string: # Raspberry
        return 0
    elif 'mini' in string: # OS4
        return 1
    elif 'root' in string: # Other OS3 or Linux based
        return 2
    elif '$' in string: # Sequoia
        return 3
    else:  # Unknown
        return 4

def reset_command_line(tn, console_password=None, timeout=25):
    # for handle login or other broken cmd
    pws_dict = {
        'idx': -1,
        'pws': [
            '0502e94f11f527cb',  # KDP
            '',  # old KDP
            'adminadmin'  # GZA
    ]}
    if console_password:
        pws = [console_password] + pws_dict['pws']

    def get_pw(pws_dict):
        pws_dict['idx'] = (pws_dict['idx'] + 1) % len(pws_dict['pws'])
        return pws_dict['pws'][pws_dict['idx']]

    tn.read_very_eager()
    read_pw_msg_timeout = 5
    start = time.time()
    while time.time() - start < timeout:
        line = send_and_get_first_line(tn, '\x03', timeout=1)  # send ^c
        line = line.strip()
        if '@' in line and (line.endswith('$') or line.endswith('#')):  # normal line
            return
        elif line == '>':  # resolve unfinished string
            tn.read_very_eager()
            line = send_and_get_first_line(tn, '"')  # finish string by "
            if line == '>':
                send_and_get_first_line(tn, "'")  # finish string by '
            tn.read_very_eager()
        else:  # trying to enter password
            enter_msg = "Please press Enter"
            pw_msg = "Password:"
            output = read_until(tn, re_pattern='{}|{}'.format(enter_msg, pw_msg), timeout=read_pw_msg_timeout, raise_error=False)
            if not output:
                continue
            if timeout < 30:
                timeout = 60
                print_without_new_line('\rneed a password to login, increase timeout to {} secs for trying to enter password...'.format(timeout))
            if enter_msg in output:
                tn.write("\n")
                read_until(tn, re_pattern=pw_msg, timeout=read_pw_msg_timeout, raise_error=False)
            pw = get_pw(pws_dict)
            print_without_new_line('\rtrying to login with "{}"...'.format(pw))
            tn.write("{}\n".format(pw))
            time.sleep(3)
            tn.read_very_eager()

def show_OS3_platform(tn):
    tn.read_very_eager()
    tn.write("getDeviceModelName.sh\n")
    matched_string = read_until(
        tn, re_pattern=r'MyCloud[a-zA-Z0-9]*', ignore_ps_line=True)
    return re.findall(r'[a-zA-Z0-9]+', matched_string).pop()

def show_Linux_platform(tn):
    tn.read_very_eager()
    tn.write("cat /etc/model\n")
    matched_string = read_until(
        tn, re_pattern=r'MyCloud[a-zA-Z0-9]*|yodaplus[0-9]*|monarch[0-9]|pelican[0-9]|drax|rocket', ignore_ps_line=True)
    return re.findall(r'[a-zA-Z0-9]+', matched_string).pop()

def show_OS4_platform(tn):
    tn.read_very_eager()
    #tn.write("getprop | grep ro.board.platform | grep -Eo ': \[[a-zA-Z]*]' | grep -Eo '[a-zA-Z]+'\n")
    tn.write("getprop | grep ro.hardware\n")
    matched_string = read_until(tn, re_pattern=r': \[[a-zA-Z]*]')
    return re.findall(r'[a-zA-Z]+', matched_string).pop()

def show_ip(tn):
    tn.read_very_eager()
    tn.write("ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1'\n")
    return read_until(tn, re_pattern=r'[0-9]+(?:\.[0-9]+){3}\r\n', timeout=3, raise_error=False).strip()

def show_OS3_ip(tn):
    tn.read_very_eager()
    tn.write("ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | grep -v 172\n")
    return read_until(tn, re_pattern=r'[0-9]+(?:\.[0-9]+){3}\r\n', timeout=3, raise_error=False).strip()

def show_Sequoia_ip(tn):
    tn.read_very_eager()
    tn.write("ip addr | grep -Eo 'inet (inet:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1'\n")
    return read_until(tn, re_pattern=r'[0-9]+(?:\.[0-9]+){3}\r\n', timeout=3, raise_error=False).strip()

def show_mac(tn, platform=None):
    tn.read_very_eager()
    if 'yoda' in platform:
        tn.write("cat /sys/class/net/wlan0/address\n")
    elif 'MyCloudEX2Ultra' in platform:
        tn.write("cat /sys/class/net/egiga0/address\n")
    elif 'MyCloud' in platform:
        tn.write("cat /sys/class/net/bond0/address\n")
    else:
        tn.write("cat /sys/class/net/eth0/address\n")
    try:
        return read_until(tn, re_pattern=r'(?:[0-9a-fA-F]:?){12}')
    except:
        return ''

# USB ports
def scan_ttyUSB():
    root, subdirs, files = os.walk('/dev').next()
    usb_ports = [int(f.strip('ttyUSB')) for f in files if f.startswith('ttyUSB')]
    usb_ports.sort()
    return usb_ports

def read_portfile(path):
    # Read portfile
    with open(path, 'r') as fp:
        port_map = json.load(fp)
    # Get existing port number and sorting.
    usb_ports = port_map.values()
    usb_ports.sort()
    return usb_ports

def get_all_devices_from_serial_server(
        server_ip, start_port=0, portfile=None, scan_with_ttyUSB=False, total_device=0, console_password='adminadmin'):
    if total_device:
        usb_ports = xrange(total_device)
    elif scan_with_ttyUSB: # Get all ttyUSB
        usb_ports = scan_ttyUSB()
    else: # Get all records.
        if not os.path.exists(portfile):
            print 'Portfile', portfile, 'does not exist.'
            sys.exit(1)
        usb_ports = read_portfile(portfile)
        # Records have already added start port number.
        start_port = 0

    print 'Total devices:', len(usb_ports)

    devices = {}
    # Get device IP one by one.
    for port in usb_ports:
        connect_port = port + start_port
        ret = show_device_info(server_ip, port=connect_port, console_password=console_password)
        if ret:
            devices[ret[3]] = {'ip': ret[2], 'port': ret[0], 'platform': ret[1]}

    return devices 


if __name__ == '__main__':
    # Arguments
    parser = argparse.ArgumentParser(description='List all attached device information')
    parser.add_argument('-port', '--start-port', help='Starting port number to scan', type=int, default='20000')
    parser.add_argument('-ip', '--server-ip', help='Destination server IP', default='localhost')
    parser.add_argument('-pf', '--portfile', help='List all device with portfile', default='/home/user/Workspace/etc/portfile')
    parser.add_argument('-swtty', '--scan-with-ttyUSB', help='List all device with scan local ttyUSB notes', action='store_true', default=False)
    parser.add_argument('-td', '--total-device', help='Total device on server for remote access (not need port file)', type=int, default=0)
    parser.add_argument('-cp', '--console-password', help='Password for console', default='adminadmin')

    args = parser.parse_args()
    start_port = args.start_port
    server_ip = args.server_ip
    portfile = args.portfile
    scan_with_ttyUSB = args.scan_with_ttyUSB
    total_device = args.total_device
    console_password = args.console_password

    devices = get_all_devices_from_serial_server(server_ip, start_port, portfile, scan_with_ttyUSB, total_device, console_password)
    print 'done.'
