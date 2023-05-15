# -*- coding: utf-8 -*-
""" This script is used to check in testing device back to inventory server. 
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import argparse
import ast
import json
import os
import sys
import textwrap
# platform modules
try: # Run with source code.
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from platform_libraries.inventoryAPI import InventoryAPI, InventoryException
    from platform_libraries.common_utils import create_logger
except: # Run standalone with belongs file in same location.
    from inventoryAPI import InventoryAPI, InventoryException
    from common_utils import create_logger


log = create_logger()

if __name__ == '__main__':

    # Handle input arguments. 
    parser = argparse.ArgumentParser(description='Checkin testing device back to inventory server.',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-ip', '--uut_ip', help=textwrap.dedent("""\
        Specify device IP to find device.
        Equivalent to set UUT_IP=IP.\
        """), metavar='IP', default='')
    parser.add_argument('-jn', '--job_name', help=textwrap.dedent("""\
        Specify job name to find device.
        Replace default job name if arg supplied.\
        """), metavar='NAME', default='')
    parser.add_argument('-q', '--quiet', help=textwrap.dedent("""\
        Disable debug mode.
        Equivalent to set INVENTORY_DEBUG=False.\
        """), action='store_true', default=False)
    parser.add_argument('-url', '--server_url', help=textwrap.dedent("""\
        Set custom URL to access inventory server.
        Equivalent to set INVENTORY_URL=URL.\
        """), metavar='URL', default='http://sevtw-inventory-server.hgst.com:8010/InventoryServer')
    parser.add_argument('-b', '--uut_broken', help=textwrap.dedent("""\
        Mark this device to be broken.
        Equivalent to set UUT_BROKEN=True.\
        """), action='store_true', default=False)
    parser.add_argument('-dui', '--disable_update_inventory', help=textwrap.dedent("""\
        Do not update checked in device information to inventory server.
        """), action='store_true', default=False)
    args = parser.parse_args()

    # Handle environment variables.
    device_ip = os.getenv('UUT_IP')
    inventory_debug = os.getenv('INVENTORY_DEBUG', True)
    inventory_url = os.getenv('INVENTORY_URL')
    is_operational = not ast.literal_eval(os.getenv('UUT_BROKEN', 'False')) # "True" or "False"
    jenkins_job = '{0}-{1}'.format(os.getenv('JOB_NAME', ''), os.getenv('BUILD_NUMBER', ''))

    # Merge arguments.
    # Input arguments have first priority, and environment variables are second priority.
    device_ip = args.uut_ip or device_ip
    inventory_debug = not args.quiet and inventory_debug
    inventory_url = args.server_url or inventory_url
    is_operational = is_operational if not args.uut_broken else False
    jenkins_job = args.job_name or jenkins_job
    disable_update_inventory = args.disable_update_inventory


    # Checkin device.
    try:
        inventory = InventoryAPI(inventory_url, debug=inventory_debug)

        # Get checked out device data
        if device_ip:
            log.info('Get device with IP: {}.'.format(device_ip))
            checkout_device = inventory.device.get_device_by_ip(device_ip)
        else:
            log.info('Get device with jenkins job: {}.'.format(jenkins_job))
            checkout_device = inventory.device.get_device_by_job(jenkins_job)

        if not checkout_device:
            log.error('Device not found.')
            exit(1)

        log.info('Device information: {}'.format(json.dumps(checkout_device)))

        # Check in the device
        if not inventory.device.check_in(checkout_device['id'], is_operational=is_operational):
            log.error('Failed to check in the device.')
            exit(1)

        log.info('Check in successfully.')

        if not disable_update_inventory:
            try:
                from inventory_update import InventoryUpdate
                InventoryUpdate(inventory_inst=inventory).start(device_ip=checkout_device['internalIPAddress'])
            except Exception, e: # let check in succes even update error.
                log.exception(e)
    except InventoryException, e:
        log.error('Status={0}, Status code={1}, message={2}.'.format(e.status, e.status_code, e.message))
        exit(1)
