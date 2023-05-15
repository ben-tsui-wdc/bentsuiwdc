# -*- coding: utf-8 -*-
""" This script is used to check out a available device from inventory server. 
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
    # UUT_XX is naming rules of environment variables for check out conditions, which should not conflict with Jenkins Job input variables.
    parser = argparse.ArgumentParser(description='Checkout a available device from inventory server.',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-ip', '--uut_ip', help=textwrap.dedent("""\
        Specify device IP to find device.
        Equivalent to set UUT_IP=IP.\
        """), metavar='IP', default='')
    parser.add_argument('-mac', '--uut_mac', help=textwrap.dedent("""\
        Specify device MAC address to find device.
        Equivalent to set UUT_MAC=MAC.\
        """), metavar='IP', default='')
    parser.add_argument('-f', '--force', help=textwrap.dedent("""\
        Force to checkout the matched device.
        Equivalent to set INVENTORY_FORCE=True.\
        """), action='store_true', default=False)
    parser.add_argument('-fw', '--firmware', help=textwrap.dedent("""\
        Specify firmware version to find device.
        Equivalent to set UUT_FIRMWARE=VERSION.\
        """), metavar='VERSION', default='')
    parser.add_argument('-v', '--variant', help=textwrap.dedent("""\
        Specify variant to find device.
        Equivalent to set UUT_VARIANT=VAR.\
        """), metavar='IP', default='')
    parser.add_argument('-e', '--environment', help=textwrap.dedent("""\
        Specify cloud environment to find device.
        Equivalent to set UUT_ENVIRONMENT=ENV.\
        """), metavar='IP', default='')
    parser.add_argument('-t', '--tag', help=textwrap.dedent("""\
        Specify tag to find device.
        Equivalent to set UUT_TAG=TAG.\
        """), metavar='VERSION', default='')
    parser.add_argument('-jn', '--job_name', help=textwrap.dedent("""\
        Specify job name to update device.
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
    parser.add_argument('-rc', '--retry_count', help=textwrap.dedent("""\
        Set retry count of checkout retrying.
        Equivalent to set INVENTORY_RETRY_COUNT=NUMBER.\
        """), metavar='NUMBER', default='')
    parser.add_argument('-rd', '--retry_delay', help=textwrap.dedent("""\
        Set retry delay time of checkout retrying.
        Equivalent to set INVENTORY_RETRY_DELAY=SECOND.\
        """), metavar='SECOND', default='')
    parser.add_argument('-ub', '--uboot', help=textwrap.dedent("""\
        Specify U-Boot version to find device.
        Equivalent to set UUT_UBOOT=VERSION.\
        """), metavar='VERSION', default='')
    parser.add_argument('-l', '--location', help=textwrap.dedent("""\
        Specify location to find device.
        Equivalent to set UUT_LOCATION=LOCATION.\
        """), metavar='LOCATION', default='')
    parser.add_argument('-p', '--platform', help=textwrap.dedent("""\
        Specify platform to find device.
        Equivalent to set UUT_PLATFORM=NAME.\
        """), metavar='NAME', default='')
    parser.add_argument('-s', '--site', help=textwrap.dedent("""\
        Specify site to find device.
        Equivalent to set UUT_SITE=SITE.\
        """), metavar='SITE', default='')
    parser.add_argument('-ua', '--usbattached', help=textwrap.dedent("""\
        Specify if USBattached.
        Equivalent to set UUT_USBATTACHED=True.\
        """), action='store_true', default=False)
    parser.add_argument('-rb', '--rebootable', help=textwrap.dedent("""\
        Specify if device is rebootable
        Equivalent to set UUT_REBOOTABLE=True.\
        """), action='store_true', default=False)
    parser.add_argument('-ud', '--updownloadable', help=textwrap.dedent("""\
        Specify if device is updownloadable
        Equivalent to set UUT_UPDOWNLOADABLE=True.\
        """), action='store_true', default=False)
    parser.add_argument('-u', '--usbable', help=textwrap.dedent("""\
        Specify if device is usbable
        Equivalent to set UUT_USBABLE=True.\
        """), action='store_true', default=False)
    parser.add_argument('-fr', '--factoryresetable', help=textwrap.dedent("""\
        Specify if device is factoryresetable
        Equivalent to set UUT_FACTORYRESETABLE=True.\
        """), action='store_true', default=False)
    args = parser.parse_args()

    # Handle environment variables.
    device_ip = os.getenv('UUT_IP')
    device_mac = os.getenv('UUT_MAC')
    force_checkout = ast.literal_eval(os.getenv('INVENTORY_FORCE', 'False')) # "True" or "False"
    fw_version = os.getenv('UUT_FIRMWARE')
    inventory_debug = os.getenv('INVENTORY_DEBUG', True)
    inventory_url = os.getenv('INVENTORY_URL')
    jenkins_job = '{0}-{1}'.format(os.getenv('JOB_NAME', ''), os.getenv('BUILD_NUMBER', '')) # Values auto set by jenkins.
    retry_counts = os.getenv('INVENTORY_RETRY_COUNT')
    retry_delay = os.getenv('INVENTORY_RETRY_DELAY')
    variant = os.getenv('UUT_VARIANT')
    environment = os.getenv('UUT_ENVIRONMENT')
    tag = os.getenv('UUT_TAG')
    uboot_version = os.getenv('UUT_UBOOT')
    uut_location = os.getenv('UUT_LOCATION')
    uut_platform = os.getenv('UUT_PLATFORM')
    uut_site = os.getenv('UUT_SITE')
    uut_usbattached = os.getenv('UUT_USBATTACHED', False)
    uut_rebootable =  os.getenv('UUT_REBOOTABLE', False)
    uut_updownloadable =  os.getenv('UUT_UPDOWNLOADABLE', False)
    uut_usbable =  os.getenv('UUT_USBABLE', False)
    uut_factoryresetable =  os.getenv('UUT_FACTORYRESETABLE', False)

    # Merge arguments.
    # Input arguments have first priority, and environment variables are second priority.
    device_ip = args.uut_ip or device_ip
    device_mac = args.uut_mac or device_mac
    force_checkout = args.force or force_checkout
    fw_version = args.firmware or fw_version
    jenkins_job = args.job_name or jenkins_job
    inventory_debug = not args.quiet and inventory_debug
    inventory_url = args.server_url or inventory_url
    retry_counts = args.retry_count or retry_counts
    retry_delay = args.retry_delay or retry_delay
    variant = args.variant or variant
    environment = args.environment or environment
    tag = args.tag or tag
    uboot_version = args.uboot or uboot_version
    uut_location = args.location or uut_location
    uut_platform = args.platform or uut_platform
    uut_site = args.site or uut_site
    uut_usbattached = args.usbattached or uut_usbattached
    uut_rebootable = args.rebootable or uut_rebootable
    uut_updownloadable = args.updownloadable or uut_updownloadable
    uut_usbable = args.usbable or uut_usbable
    uut_factoryresetable = args.factoryresetable or uut_factoryresetable

    if jenkins_job == '-':
        log.error('Need to set jenkins_job.')
        exit(1)
    if uut_platform:
        uut_platform = uut_platform.lower()

    # Check out device.
    try:
        inventory = InventoryAPI(inventory_url, debug=inventory_debug)

        if device_ip: # Device IP has first priority to use.
            log.info('Check out a device with IP: {}.'.format(device_ip))
            device = inventory.device.get_device_by_ip(device_ip)
            if not device:
                log.error('Failed to find out the device with specified IP.')
                exit(1)
            checkout_device = inventory.device.check_out_retry(device['id'], jenkins_job, retry_counts=retry_counts,
                retry_delay=retry_delay, force=force_checkout)

        elif uut_platform: # Find device with matching below conditions.
            log.info('Looking for a available device.')
            checkout_device = inventory.device.matching_check_out_retry(
                uut_platform, tag=tag, device_mac=device_mac, firmware=fw_version, variant=variant, environment=environment, uboot=uboot_version,
                location=uut_location, site=uut_site, jenkins_job=jenkins_job, retry_counts=retry_counts,
                retry_delay=retry_delay, force=force_checkout, usbattached=uut_usbattached, rebootable=uut_rebootable, updownloadable=uut_updownloadable, usbable=uut_usbable, factoryresetable=uut_factoryresetable
            )
        else:
            log.error('Device Platform or Device IP is required.')
            exit(1)

        # handle response
        if checkout_device:
            device_dict = inventory.device.device_view(checkout_device.get('device', checkout_device))
            info_json_string = json.dumps(device_dict)
            log.info('Device information: {}'.format(info_json_string))

            # Save device information to file.
            location = '/root/app/output/'
            if not os.path.exists(location):
                location = './'
            with open(location + 'UUT', 'w') as f:
                f.write(info_json_string)
        else:
            log.error('Failed to check out the device.')
            exit(1)

        log.info('Check out successfully.')
    except InventoryException, e:
        log.error('Status={0}, Status code={1}, message={2}.'.format(e.status, e.status_code, e.message))
        exit(1)
