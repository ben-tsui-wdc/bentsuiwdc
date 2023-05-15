# -*- coding: utf-8 -*-
""" This script is used to re-mapping serial port on inventory server with specify serial server. 
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import argparse
import sys
from os.path import dirname
# platform modules
sys.path.append(dirname(__file__)+'/../../app/')
from platform_libraries.inventoryAPI import InventoryAPI
# infrastructure modules
from list_device import get_all_devices_from_serial_server


def get_all_devices_from_inventory_server(inv_inst, only_available_devices=False):
    result_device = inv_inst.device.list()
    if result_device['status'] != 'SUCCESS':
        print 'Inventory Server seems down.'
        return []

    if only_available_devices:
        devices = [device for device in result_device['list'] if not device['isOperational']]
    else:
        devices = [device for device in result_device['list']]

    # Append IP and port.
    for d in devices:
        if not d.get('serialServer'):
            continue
        ss = inv_inst.device.get_serial_server(d['id'])
        d['serialServer']['ipAddress'] = ss['ipAddress']
        d['serialServer']['port'] = ss['port']

    return devices

def get_all_serail_from_inventory_server(inv_inst, serial_server_ip):
    result_serial = inv_inst.serial_server.list()
    if result_serial['status'] != 'SUCCESS':
        print 'Inventory Server seems down.'
        return []
    return filter(lambda item: item['ipAddress'] == serial_server_ip, result_serial['list'])

def remapping(inv_inst, inv_devices, inv_serails, srl_devices, serial_server_ip, dry_run=False):
    rm_list = [] # List to clean up serial data.
    updte_list = [] # List to update serial data.

    print '\nInformation comparing...\n'

    for inv_d in inv_devices:
        inv_d_mac = inv_d['macAddress'].upper()
        # Serial has data of this device.
        if inv_d_mac in srl_devices:
            srl_d = srl_devices[inv_d_mac]
            # Inventory don't have serail data.
            if not inv_d['serialServer']:
                updte_list.append((inv_d, srl_d))
                print '{}: None -> {}:{}'.format(inv_d_mac, serial_server_ip, srl_d['port'])
            # Inventory data is not correct.
            elif inv_d['serialServer']['ipAddress'] != serial_server_ip or inv_d['serialServer']['port'] != str(srl_d['port']):
                rm_list.append(inv_d)
                updte_list.append((inv_d, srl_d))
                print '{}: {}:{} -> {}:{}'.format(inv_d_mac, inv_d['serialServer']['ipAddress'], inv_d['serialServer']['port'], serial_server_ip, srl_d['port'])
            else: # Inventory data is correct
                continue
        # Serial has no data of this device.
        elif inv_d['serialServer'] and inv_d['serialServer']['ipAddress'] == serial_server_ip:
            rm_list.append(inv_d)
            print '{}: {}:{} -> None'.format(inv_d_mac, inv_d['serialServer']['ipAddress'], inv_d['serialServer']['port'])

    if dry_run or (not rm_list and not updte_list):
        return

    print '\nUpdate Inventory Server...\n'

    for d in rm_list:
        print '{}: Set serial port to null...'.format(d['macAddress'].upper())
        inv_inst.device.update(device_id=d['id'], serial_server_id='')
    for d, s in updte_list:
        serial_item = filter(lambda item: item['port'] == str(s['port']), inv_serails)[0]
        print '{}: Set serial port to {}...'.format(d['macAddress'].upper(), s['port'])
        inv_inst.device.update(device_id=d['id'], serial_server_id=serial_item['id'])


if __name__ == '__main__':
    # Input Arguments
    parser = argparse.ArgumentParser(description='Re-mapping serial port on inventory server.')
    # Inventory server
    parser.add_argument('-dr', '--dry-run', help='Re-mapping serial port without update to server.', action='store_true', default=False)
    parser.add_argument('-oad', '--only-available-devices', help='Only re-mapping for available devices on inventory server.', action='store_true', default=False)
    parser.add_argument('-url', '--inventory-server-url', help='Set URL to access inventory server. e.g. http://10.92.234.32:8010/InventoryServer', metavar='URL', required=True)
    # Serial server
    parser.add_argument('-port', '--start-port', help='Starting port number to scan', type=int, default='20000')
    parser.add_argument('-ip', '--serial-server-ip', help='Destination serial server IP. e.g. 10.92.224.60', required=True)
    parser.add_argument('-pf', '--portfile', help='List all device with portfile', default='/home/user/Workspace/etc/portfile')
    parser.add_argument('-swtty', '--scan-with-ttyUSB', help='List all device with scan local ttyUSB notes', action='store_true', default=False)
    parser.add_argument('-td', '--total-device', help='Total device on server for remote access (not need port file)', type=int, default=0)
    args = parser.parse_args()
    inv_inst = InventoryAPI(args.inventory_server_url)
    print '\nList all device on inventory server...\n'
    inv_devices = get_all_devices_from_inventory_server(inv_inst, only_available_devices=args.only_available_devices)
    print '\nList all serial port on inventory server...\n'
    inv_serails = get_all_serail_from_inventory_server(inv_inst, args.serial_server_ip)
    print '\nList all device on serial server...\n'
    srl_devices = get_all_devices_from_serial_server(args.serial_server_ip, args.start_port, args.portfile, args.scan_with_ttyUSB, args.total_device)
    remapping(inv_inst, inv_devices, inv_serails, srl_devices, args.serial_server_ip, dry_run=args.dry_run)
    print 'done.'
