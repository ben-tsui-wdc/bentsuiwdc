# -*- coding: utf-8 -*-
""" This script is used to audit devices on inventory server. 
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import argparse
import json
import smtplib
import textwrap
import time
import urllib2
from pprint import pformat
# platform modules
from platform_libraries.adblib import ADB
from platform_libraries.common_utils import create_logger
from platform_libraries.inventoryAPI import InventoryAPI, InventoryException
from platform_libraries.powerswitchclient import PowerSwitchClient


# TODO: convert this script to class format.
def audit(filter_conditions=None, fix_device=False, dry_run=False):
    """ The devices which doesn't need to check status in Inventory Server. """
    exclusion_list = ['mac-client', 'dd-wrt', 'yodaplus-irvine']  # exclusion_list, so far it is hard-code.
    result_product = inv.product.list()
    if result_product['status'] != 'SUCCESS':
        log.info('Inventory Server seems down.')
        return
    exclusion_product_id_list = []
    for product in result_product['list']:
        if product['name'] in exclusion_list:
            exclusion_product_id_list.append(product['id']) 

    """ Audit all devices on Inventory Server. """
    broken_devices = []

    result_device = inv.device.list()    
    if result_device['status'] != 'SUCCESS':
        log.info('Inventory Server seems down.')
        return

    for device in result_device['list']:
        try:
            if device.get('product').get('id') in exclusion_product_id_list:
                continue
            if not audit_it(device, filter_conditions):
                continue
            if not device['isOperational']:
                continue

            log.info('Checking device: \n{}'.format(pformat(device)))
            is_available = check_device(device)
            if is_available: # Device works
                update_device_on_server(device_ip=device['internalIPAddress'])
                continue
            # Device is down.
            broken_devices.append(device)
            device['recovered'] = False
            if not dry_run: mark_device_as_disabled(device_id=device['id'])
            if fix_device:
                success = recover_device(device)
                if success:
                    if not dry_run: mark_device_as_available(device_id=device['id'])
                    device['recovered'] = True
                    continue
        except:
            log.exception('Exception occurred during audit device.')
    send_notification(broken_devices)
    log.info('Done.')

def audit_it(device, filter_conditions):
    """ Device filter """
    if not filter_conditions:
        return True
    if not isinstance(filter_conditions, dict):
        raise ValueError('Need dict')
    for key, value in filter_conditions.iteritems():
        if key == 'id':
            if isinstance(value, list):
                if device['id'] in value: return True
            if device['id'] == value: return True

        if device['location']:
            if key == 'site':
                site, _ = device['location'].split('-', 1)
                if site == value: return True
            if key == 'location':
                if device['location'] == value: return True
    return False

def check_device(device):
    if is_jenkins_job_building(jenkins_job=device['jenkinsJob']): # Device is in use.
        log.info('Device is building jenkins job.')
        return True
    # TODO: Add more check mechanism if we need. 
    is_available = test_restsdk(device['internalIPAddress'])
    if is_available:
        log.info('RESTSDK of device is work.')
        return True
    log.error('Device is down.')
    return False # device really does not work.

def test_restsdk(device_ip):
    test_url = 'http://{0}'.format(device_ip)
    try:
        log.info('Send request: {}'.format(test_url))
        response = urllib2.urlopen(test_url, timeout=30)
    except urllib2.HTTPError: # Expect 404 error or other HTTTP error.
        return True
    except: # Normal case here is Timeout error or Connection refused error when device down.
        log.exception('Exception occurred during test restsdk.')
        return False

def is_jenkins_job_building(jenkins_job):
    if not jenkins_job:
        return False
    # Make sure Jenkins job is building.
    try:
        job_name, build_number = jenkins_job.rsplit('-', 1)
        jenkins_url = 'http://autojenkins.wdmv.wdc.com/job/{0}/{1}/api/json'.format(job_name, build_number)
        log.info('Send request: {}'.format(jenkins_url))
        response = urllib2.urlopen(jenkins_url)
        result = json.load(response)
        if result['building']:
            return True
        return False
    except:
        log.exception('Exception occurred during check job status.')
        return False

def recover_device(device):
    log.info('Do recover device...')
    is_device_reboot = reboot_device(device)
    if not is_device_reboot:
        return False
    time.sleep(60*5)
    return wait_device(device)

def reboot_device(device):
    log.info('Reboot device...')
    if not device['powerSwitch']:
        log.info('Power switch not found, do nothing.')
        return False
    resp = inv.device.get_power_switch(device_id=device['id'])
    power_server = resp['ipAddress']
    power_port = resp['port']

    # Reboot device by power switch
    log.info('Reboot device on Power switch: {0} Port: {1}'.format(power_server, power_port))
    power_switch = PowerSwitchClient(power_server)
    log.info('Powering off the device')
    power_switch.power_off(power_port)
    time.sleep(5)  # interval between power off and on
    log.info('Powering on the device')
    power_switch.power_on(power_port)
    return True

def wait_device(device):
    log.info('Wait for device boot completede...')
    timeout = 60*10
    adb = ADB(uut_ip=device['internalIPAddress'])
    if not adb.wait_for_device_boot_completed(timeout=timeout):
        log.error('Device seems down.')
        return False
    adb.disconnect()
    return True

def mark_device_as_disabled(device_id):
    log.info('Mark device as disabled')
    inv.device.update(device_id, is_operational=False)

def mark_device_as_available(device_id):
    log.info('Mark device as available')
    inv.device.update(device_id, is_operational=True)

def update_device_on_server(device_ip):
    log.info('Update device information on inventory server')
    try:
        from inventory_update import InventoryUpdate
        InventoryUpdate(inventory_inst=inv).start(device_ip=device_ip)
    except Exception, e:
        log.exception(e)

def send_notification(devices):
    log.info('Send notification...')
    recovered_devices = []
    broken_devices = []
    for device in devices:
        try:
            view = inv.device.device_view(device)
            view.pop('recovered', None)
        except:
            log.exception('Exception occurred during create view.')
            view = device
        if device['recovered']:
            recovered_devices.append(view)
        else:
            broken_devices.append(view)
    log.warning('Recovered device: \n{}'.format(pformat(recovered_devices)))
    log.warning('Broken device: \n{}'.format(pformat(broken_devices)))
    outout_content(recovered_devices, broken_devices)
    # Use Jenkins Plugin to send e-mail.
    '''
    send_mail(
        FROM='audit',
        TO=['Estvan.Huang@wdc.com'],
        SUBJECT='Device is down',
        TEXT='Device information: \n{}'.format(pformat(device))
    )
    '''

def outout_content(recovered_devices, broken_devices, file_path='output/content.txt'):
    try:
        # Create content
        content = ''
        if recovered_devices:
            content += '<h2>Recovered Devices:</h2><pre><code>' + \
                pformat(recovered_devices) + \
                '</pre></code>'
        if broken_devices:
            content += '<h2>Broken Devices:</h2><pre><code>' + \
                pformat(broken_devices) + \
                '</pre></code>'
        # Write to file
        if content:
            with open(file_path, 'w') as f:
                f.write(content)
            log.info('Outout content to {}'.format(file_path))
            return True
    except Exception as e:
        log.exception('Exception occurred during outout content.')
    return False

def send_mail(FROM, TO, SUBJECT, TEXT, SERVER='10.92.224.77'):
    message = """\
    From: %s
    To: %s
    Subject: %s

    %s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    # Send the mail
    server = smtplib.SMTP(SERVER)
    server.sendmail(FROM, TO, message)
    server.quit()


# Input Arguments
parser = argparse.ArgumentParser(description='Audit devices on inventory server.')
parser.add_argument('-dr', '--dry_run', help=textwrap.dedent("""\
    Audit devices without updating status to server.\
    """), action='store_true', default=False)
parser.add_argument('-fix', '--fix_device', help=textwrap.dedent("""\
    Try to fix the broken devices.\
    """), action='store_true', default=False)
parser.add_argument('-id', '--device_id', help=textwrap.dedent("""\
    Specify device id list to audit.\
    """), nargs='+', type=int, metavar='ID1 ID2')
parser.add_argument('-l', '--location', help=textwrap.dedent("""\
    Specify location to audit.\
    """), metavar='LOCATION')
parser.add_argument('-s', '--site', help=textwrap.dedent("""\
    Specify site to audit.\
    """), metavar='SITE')
parser.add_argument('-url', '--server_url', help=textwrap.dedent("""\
    Set custom URL to access inventory server.\
    Equivalent to set INVENTORY_URL=URL.\
    """), metavar='URL', default='http://sevtw-inventory-server.hgst.com:8010/InventoryServer')
args = parser.parse_args()

inv = InventoryAPI(args.server_url)
log = create_logger()

filter_conditions = {}
if args.device_id:
    filter_conditions['id'] = args.device_id
if args.location:
    filter_conditions['location'] = args.location
if args.site:
    filter_conditions['site'] = args.site

audit(filter_conditions=filter_conditions, fix_device=args.fix_device, dry_run=args.dry_run)
