# -*- coding: utf-8 -*-
""" This script is used to update firmware information.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import argparse
import ast
import json
import os
import sys
import textwrap
from pprint import pformat
# platform modules
from platform_libraries.adblib import ADB
from platform_libraries.common_utils import create_logger
from platform_libraries.inventoryAPI import InventoryAPI, InventoryException


log = create_logger()

class InventoryUpdate(object):

    def __init__(self, inventory_url=None, debug=False, inventory_inst=None):
        if inventory_inst:
            self.inventory_inst = inventory_inst
        elif inventory_url:
            self.inventory_inst = InventoryAPI(inventory_url, debug=debug)
        else:
            raise ValueError('Need inventory_url or inventory_inst')
        self.debug = debug

    def update_one_device(self, device_ip):
        log.info('Update device: {}'.format(device_ip))
        self._update_device(device_ip=device_ip)

    def update_all_device(self):
        for device in self.inventory_inst.device.list()['list']:
            if device['isBusy'] or not device['isOperational']:
                continue
            log.info('Update device: {}'.format(device['internalIPAddress']))
            self._update_device(device_ip=device['internalIPAddress'])

    def _update_device(self, device_ip):
        try: 
            # Get device from inventory server.
            inv_device_src = self.inventory_inst.device.get_device_by_ip(device_ip)
            inv_device = self.inventory_inst.device.device_view(inv_device_src)
            # Get update information via ADB
            constant_info, update_info = self._get_device_info(
                ip=inv_device['adbGateway']['ipAddress'], port=inv_device['adbGateway']['port']
            )
            # Check tarfet device is the same one or not.
            if inv_device['macAddress'] != constant_info['mac_address']:
                log.info('MAC Address has changed.')
                return False
            # Update "firmware", "variant", "uboot" and "environment".
            # Always update device.
            self.inventory_inst.device.update(device_id=inv_device['id'], **update_info)
            return True
        except Exception, e:
            log.exception(e)
            return False

    def _get_device_info(self, ip, port):
        # Get device information
        adb = ADB(uut_ip=ip, port=port)
        adb.connect()
        model_name = adb.getModel()
        if model_name in ('yoda', 'yodaplus'):
            mac_address = adb.get_mac_address(interface='wlan0')
        else:
            mac_address = adb.get_mac_address()

        device = {
            'model': model_name,
            'mac_address': mac_address,
            'firmware': adb.getFirmwareVersion(),
            'variant': adb.get_variant(),
            'uboot': adb.get_uboot(),
            'environment': adb.get_environment()
        }
        if self.debug:
            log.info('Device:\n {}'.format(pformat(device)))
        adb.disconnect()

        # Check vlaue and classify for update.
        constant_info = {}
        update_info = {}
        if device['model']: constant_info['model'] = device['model']
        if device['mac_address']: constant_info['mac_address'] = device['mac_address'].upper()
        # TODO: Check value if we need.
        if device['firmware']: update_info['firmware'] = device['firmware']
        if device['variant']: update_info['variant'] = device['variant']
        if device['uboot']: update_info['uboot'] = device['uboot']
        if device['environment']: update_info['environment'] = device['environment']
        return constant_info, update_info

    def start(self, device_ip=None):
        """ Update one specied device or all. """
        if device_ip:
            self.update_one_device(device_ip)
        else:
            self.update_all_device()


if __name__ == '__main__':

    # Handle input arguments. 
    parser = argparse.ArgumentParser(description='Checkin testing device back to inventory server.',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-ip', '--uut_ip', help=textwrap.dedent("""\
        Specify device IP to update.
        """), metavar='IP', default='')
    parser.add_argument('-q', '--quiet', help=textwrap.dedent("""\
        Disable debug mode.
        """), action='store_true', default=False)
    parser.add_argument('-url', '--server_url', help=textwrap.dedent("""\
        Set custom URL to access inventory server.
        """), metavar='URL', default='http://sevtw-inventory-server.hgst.com:8010/InventoryServer')
    args = parser.parse_args()

    # Handle input  variables.
    device_ip = args.uut_ip
    debug = not args.quiet
    inventory_url = args.server_url

    # Update devices
    try:
        InventoryUpdate(inventory_url, debug).start(device_ip=device_ip)
    except Exception, e:
        log.exception(e)
        exit(1)
