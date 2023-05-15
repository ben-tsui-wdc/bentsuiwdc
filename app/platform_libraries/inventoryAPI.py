"""
A library to access inventory service.

Base on repo: TestAutomation/taut version 7a598ae89fe.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import time
# 3rd party modules
from requests import Request, Session
# platform modules
try:
    from common_utils import create_logger, unicode_to_str
    log_inst = create_logger()
except:
    log_inst = None
try:
    from constants import INVENTORY_SERVER_TW
    default_server_url = INVENTORY_SERVER_TW
except: # Default value for standalone using.
    default_server_url = 'http://sevtw-inventory-server.hgst.com:8010/InventoryServer'


class InventoryAPI(object):

    def __init__(self, server_url=default_server_url, debug=True):
        """
        Inventory Server REST client.

        [Arguments]
            server_url: string (Optional)
                URL to access the inventory server.
            debug: boolean (Optional)
                Print debug messages or not.

        [Environment Variables]
            INVENTORY_URL: string
                Set url to access the inventory server.
            INVENTORY_DEBUG: string
                Flag of versobe mode.
        """
        # Deault settings
        self.MAX_LIST_NUM = 999
        self.RETRY_COUNTS = 10
        self.RETRY_DELAY = 60

        # Handle parameters
        self.url = server_url
        self._debug = debug

        # Prepare connection
        self._session = Session()
        # Default headers
        self.headers = {'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
        # References to encapsulated APIs
        self.device = InventoryAPI.DeviceAPI(self, self._debug, self.RETRY_COUNTS, self.RETRY_DELAY)
        self.power_switch = InventoryAPI.PowerSwitchAPI(self, self._debug)
        self.serial_server = InventoryAPI.SerialServerAPI(self, self._debug)
        self.ssh_gateway = InventoryAPI.SSHGatewayAPI(self, self._debug)
        self.product = InventoryAPI.ProductAPI(self, self._debug)
        self.adb_gateway = InventoryAPI.ADBGatewayAPI(self, self._debug)
        self.adb_server = InventoryAPI.ADBServerAPI(self, self._debug)

    def rest_call(self, request):
        """
        Common function to request server.

        [Arguments]
            request: Request object
                Pregared object for invoking request.
        """
        prepared_request = self._session.prepare_request(request)
        prepared_request.headers = self.headers

        response = self._session.send(prepared_request)
        log("\nREST Call: {}".format(response.url), self._debug)

        json_response = response.json()
        log("JSON Response: {}\n".format(json_response), self._debug)

        if 'statusCode' in json_response and json_response['statusCode'] != 1000:
            raise InventoryException(json_response['status'], json_response['statusCode'], json_response['message'])

        return json_response

    class DeviceAPI(object):

        def __init__(self, invAPI, debug, retry_counts, retry_delay):
            """
            API set of device resource.

            [Arguments]
                invAP: InventoryAPI object
                debug: boolean
                    Print debug messages or not.
                retry_counts: integer
                    The max number to retry.
                retry_delay: integer
                    The number of seconds to delay between retrying. 
            """
            self.invAPI = invAPI
            self.debug = debug
            self.retry_counts = retry_counts
            self.retry_delay = retry_delay

        def list(self):
            """
            List all devices on server.

            [Return Example]
                {'list': [{'adbGateway': {'class': 'com.wdc.ADBGateway', 'id': 64},
                           'adbServer': {'class': 'com.wdc.ADBServer', 'id': 64},
                           'class': 'com.wdc.Device',
                           'dateCreated': '2017-02-03T08:13:02Z',
                           'firmware': '4.0.0-232',
                           'id': 90,
                           'internalIPAddress': '10.136.137.147',
                           'isBusy': False,
                           'isOperational': True,
                           'jenkinsJob': None,
                           'lastUpdated': '2017-02-09T09:08:04Z',
                           'location': 'TW-Testing Lab',
                           'macAddress': '00:14:EE:00:C2:E1',
                           'powerSwitch': {'class': 'com.wdc.PowerSwitch', 'id': 73},
                           'product': {'class': 'com.wdc.Product', 'id': 125},
                           'serialServer': {'class': 'com.wdc.SerialServer', 'id': 65},
                           'sshGateway': {'class': 'com.wdc.SSHGateway', 'id': 65},
                           'uboot': '4.1.1'}],
                 'message': None,
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('List all devices', self.debug)
            url = str.format("{0}/devices", self.invAPI.url)
            data = {'max': self.invAPI.MAX_LIST_NUM}
            request = Request('GET', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def get(self, device_id):
            """
            Get specific device with ID.

            [Return Example]
                {'device': {'adbGateway': None,
                            'adbServer': None,
                            'class': 'com.wdc.Device',
                            'dateCreated': '2017-02-09T09:09:13Z',
                            'firmware': '0.0.001',
                            'id': 109,
                            'internalIPAddress': '1.1.1.1',
                            'isBusy': False,
                            'isOperational': False,
                            'jenkinsJob': None,
                            'lastUpdated': '2017-02-09T09:09:13Z',
                            'location': 'MV-999',
                            'macAddress': 'FF:FF:FF:FF:FF:FF',
                            'powerSwitch': None,
                            'product': {'class': 'com.wdc.Product', 'id': 159},
                            'serialServer': None,
                            'sshGateway': None,
                            'uboot': '0.0.1'},
                 'message': None,
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Get device with device ID:{}'.format(device_id), self.debug)
            url = str.format("{0}/devices/{1}", self.invAPI.url, device_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def create(self, mac_address, product_id, tag=None, internal_ip_address=None, location=None, firmware=None,
                   variant=None, environment=None, uboot=None, power_switch_id=None, ssh_gateway_id=None, serial_server_id=None):
            """
            Create a new device on server.

            [Arguments]
                mac_address: string
                    MAC address of new device.
                product_id: string
                    The ID of platform of new device.
                tag: string (Optional)
                    Tag of new device.
                internal_ip_address: string (Optional)
                    IP address of new device.
                location: string (Optional)
                    Location of new device.
                firmware: string (Optional)
                    Firmware version of new device.
                variant: string (Optional)
                    Variant of new device.
                environment string (Optional)
                    Cloud environment of new device.
                uboot: string (Optional)
                    U-Boot version of new device.
                power_switch_id: string (Optional)
                    The ID of the power switch which is connected to new device.
                ssh_gateway_id: string (Optional)
                    The ID of the SSH gateway of new device.
                serial_server_id: string (Optional)
                    The ID of the serial server of new device.

            [Device Initial Status]
                isBusy=False
                isOperational=True
                jenkinsJob=None

            [Return Example]
                Example refer to get().
            """
            url = str.format("{0}/devices", self.invAPI.url)
            data = {'macAddress': mac_address, 'product': product_id, 'tag': tag, 'internalIPAddress': internal_ip_address,
                    'location': location, 'firmware': firmware, 'variant': variant, 'environment': environment, 'uboot': uboot,
                    'powerSwitch': power_switch_id, 'sshGateway': ssh_gateway_id, 'serialServer': serial_server_id}
            log('Create device with following info:{}'.format(data), self.debug)
            request = Request('POST', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def update(self, device_id, mac_address=None, product_id=None, tag=None, internal_ip_address=None, location=None,
                   firmware=None, variant=None, environment=None, uboot=None, power_switch_id=None,
                   ssh_gateway_id=None, serial_server_id=None, is_busy=None, is_operational=None, jenkins_job=None):
            """
            Update status to specific device with ID.

            [Arguments]
                *** Reset a field with ''. ***
                device_id: string
                    Device ID in server.
                is_busy: boolean (Optional)
                    Set True if this device is used by other job, or set False.
                is_operational: boolean (Optional)
                    Set True if this device works fine, or set False.
                jenkins_job: string (Optional)
                    The title of jenkins job which ordered this device.
                [Others]
                    Please refer to create().

            [Return Example]
                Example refer to get().
            """
            url = str.format("{0}/devices/{1}", self.invAPI.url, device_id)
            data = {'macAddress': mac_address, 'product': product_id, 'tag': tag, 'internalIPAddress': internal_ip_address,
                    'location': location, 'firmware': firmware, 'variant': variant, 'environment': environment, 'uboot': uboot,
                    'powerSwitch': power_switch_id, 'sshGateway': ssh_gateway_id, 'serialServer': serial_server_id,
                    'isBusy': is_busy, 'isOperational': is_operational, 'jenkinsJob': jenkins_job}
            log('Update device:{0} with following info:{1}'.format(device_id, data), self.debug)
            request = Request('PUT', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def delete(self, device_id):
            """
            Delete specific devices with ID.

            [Return Example]
                {'message': 'Device has been successfully deleted',
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Delete device with device ID:{}'.format(device_id), self.debug)
            url = str.format("{0}/devices/{1}", self.invAPI.url, device_id)
            request = Request('DELETE', url)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def check_in(self, device_id, is_operational=True):
            """
            Put device back to server. (isBusy set to false.)

            [Arguments]
                device_id: string
                    Device ID in server.
                is_operational: boolean (Optional)
                    Set True if this device is operational, or set it False to mark it broken.

            [Returns]
                Reture device information (Please refer to get()) if it's success, or reture None.
            """
            log('Checkin decive with device ID:{0} and is_operational:{1}'.format(device_id, is_operational), self.debug)
            url = str.format("{0}/api/device/checkIn/{1}", self.invAPI.url, device_id)
            params = {'isOperational': is_operational}
            request = Request('GET', url, params=params)
            json_response = self.invAPI.rest_call(request)
            if json_response['checkedIn']:
                return self.get(device_id)
            return None

        def check_out(self, device_id, jenkins_job, force=False):
            """
            Get a available device from server. (isBusy set to true.)

            [Arguments]
                device_id: string
                    Device ID in server.
                jenkins_job: string
                    Update jenkins job name to device.
                force: boolean (Optional)
                    Set True to ignore isBusy status.

            [Returns]
                Reture device information (Please refer to get()) if it's success, or reture None.
            """
            log('Checkout decive with device ID:{0} and Jenkins Job:{1}, force={2}'.format(device_id, jenkins_job, force), self.debug)
            url = str.format("{0}/api/device/checkOut/{1}", self.invAPI.url, device_id)
            params = {'jenkinsJob': jenkins_job, 'force': force}
            request = Request('GET', url, params=params)
            json_response = self.invAPI.rest_call(request)
            if json_response['checkedOut']:
                return self.get(device_id)
            return None

        def check_out_retry(self, device_id, jenkins_job, retry_counts=None, retry_delay=None, force=False):
            """
            Check out a available device by device ID with retrying.

            [Arguments]
                retry_counts: integer (Optional)
                    Total counts to retry.
                retry_delay: integer (Optional)
                    Delay time for each retry.
                force: boolean (Optional)
                    Force to check out device.
                [Others]
                    Please refer to check_out().

            [Returns]
                Reture device information (Please refer to get()) if it's success, or reture None.
            """
            if not retry_counts:
                retry_counts = self.retry_counts

            if not retry_delay:
                retry_delay = self.retry_delay

            # Keep looking for a available device and check out it.
            for remaining_count in reversed(xrange(int(retry_counts))):
                try:
                    check_out_device = self.check_out(device_id, jenkins_job, force)
                    if check_out_device: # Found device.
                        remaining_count = 0 # not delay
                        return check_out_device
                except Exception as e:
                    log('An exception raised when checking out device: \n{}.'.format(repr(e)), self.debug)
                finally:
                    if remaining_count > 0: # Retry delay
                        log('Retry after {0} seconds, remaining {1} retries...'.format(retry_delay, remaining_count), self.debug)
                        time.sleep(float(retry_delay))

            return None

        def is_available(self, device_id):
            """
            Check the available status of specific devices with ID.

            [Return Example]
                {'isAvailable': True, 'message': None, 'status': 'SUCCESS', 'statusCode': 1000}
            """
            log('Check if device:{} is available to use'.format(device_id), self.debug)
            url = str.format("{0}/api/device/isAvailable/{1}", self.invAPI.url, device_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response['isAvailable']

        def get_SSH_gateway(self, device_id):
            """
            Check the SSH gateway information of specific devices with ID.

            [Return Example]
                {'message': None,
                 'sshGateway': {'class': 'com.wdc.SSHGateway',
                                'dateCreated': '2017-02-09T09:06:54Z',
                                'id': 65,
                                'ipAddress': '10.136.149.25',
                                'lastUpdated': '2017-02-09T09:06:54Z',
                                'port': '4564'},
                 'status': 'SUCCESS',
                 'statusCode': 1000}
             """
            log('Get SSH Gateway info with device ID:{}'.format(device_id), self.debug)
            url = str.format("{0}/api/device/getSSHGateway/{1}", self.invAPI.url, device_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response['sshGateway']

        def get_serial_server(self, device_id):
            """
            Check the serial server information of specific devices with ID.

            [Return Example]
                {'message': None,
                 'serialServer': {'class': 'com.wdc.SerialServer',
                                  'dateCreated': '2017-02-09T09:06:35Z',
                                  'id': 65,
                                  'ipAddress': '10.136.139.29',
                                  'lastUpdated': '2017-02-09T09:06:35Z',
                                  'port': '2323'},
                 'status': 'SUCCESS',
                 'statusCode': 1000}
             """
            log('Get Serial Server info with device ID:{}'.format(device_id), self.debug)
            url = str.format("{0}/api/device/getSerialServer/{1}", self.invAPI.url, device_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response['serialServer']

        def get_power_switch(self, device_id):
            """
            Check the power switch information of specific devices with ID.

            [Return Example]
                {'message': None,
                 'powerSwitch': {'class': 'com.wdc.PowerSwitch',
                                 'dateCreated': '2017-02-09T09:07:21Z',
                                 'id': 73,
                                 'ipAddress': '10.136.137.147',
                                 'lastUpdated': '2017-02-09T09:07:21Z',
                                 'port': '4'},
                 'status': 'SUCCESS',
                 'statusCode': 1000}
             """
            log('Get Power Switch info with device ID:{}'.format(device_id), self.debug)
            url = str.format("{0}/api/device/getPowerSwitch/{1}", self.invAPI.url, device_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response['powerSwitch']

        def get_device_by_job(self, jenkins_job):
            """
            Get device with jenkins job name.

            [Return Example]
                Example refer to get().
             """
            log('Getting device info with Jenkins Job:{}'.format(jenkins_job), self.debug)
            url = str.format("{0}/api/device/getDeviceByJob", self.invAPI.url)
            params = {'jenkinsJob': jenkins_job}
            request = Request('GET', url, params=params)
            json_response = self.invAPI.rest_call(request)
            return json_response['device']

        def get_device_by_ip(self, ip):
            """
            Get device with internal IP address.

            [Return Example]
                Example refer to get().
             """
            log('Getting device info with ip:{}'.format(ip), self.debug)
            url = str.format("{0}/api/device/getDeviceByIP", self.invAPI.url)
            params = {'ip': ip}
            request = Request('GET', url, params=params)
            json_response = self.invAPI.rest_call(request)
            return json_response['device']

        def matching_check_out(self, product_name, tag=None, device_mac=None, firmware=None, variant=None, environment=None,
                uboot=None, location=None, site=None, jenkins_job=None, force=False, usbattached=None, rebootable=None, updownloadable=None, usbable=None, factoryresetable=None):
            """
            Check out a available device by specific conditions.

            [Arguments]
                product_name: string
                    Matches device by product name.
                tag: string (Optional)
                    Matches device by tag.
                firmware: string (Optional)
                    Matches device by firmware version.
                variant: string (Optional)
                    Matches device by variant.
                environment: string (Optional)
                    Matches device by cloud environment.
                uboot: string (Optional)
                    Matches device by uboot version.
                location: string (Optional)
                    Matches device by location.
                site: string (Optional)
                    Matches device by site, which is the first part value of location, spliting by "-".
                jenkins_job: string (Optional)
                    Jenkins job name to update device after checked out.

            [Returns]
                Reture device information (Please refer to get()) if it's success, or reture None.
            """
            log('Find device with {}'.format(locals()), self.debug)
            
            # Get the list of products
            product_list = self.invAPI.product.list()['list']
            # Get the product we want to checkout
            log('Product looking for: {}'.format(product_name), self.debug)
            product = None
            for p in product_list:
                if p['name'] == product_name:
                    product = p
                    break
            if not product:
                log('ERROR: Product:{} is not found in product list!'.format(product_name), self.debug)
                return None

            # Get all devices for a product
            devices = self.invAPI.product.getDevices(product['id'])['devices']
            if not devices:
                log('ERROR: No devices for product:{}'.format(product_name), self.debug)
                return None

            min = None
            # Find available device from list.
            for d in devices:
                # Skip device by conditions below.
                if tag:
                    if d['tag'] and (d['tag'] != tag):
                        continue
                if device_mac:
                    if d['macAddress'] and (d['macAddress'] != device_mac):
                        continue
                if firmware:
                    if d['firmware'] and (d['firmware'] != firmware):
                        continue
                if variant:
                    if d['variant'] and (d['variant'] != variant):
                        continue
                if environment:
                    if d['environment'] and (d['environment'] != environment):
                        continue
                if uboot:
                    if d['uboot'] and (d['uboot'] != uboot):
                        continue
                if location: # Check the whole value of location.
                    if d['location'] and (d['location'] != location):
                        continue
                if site: # Check the first part value of location, which split by "-".
                    if d['location'] and (d['location'].split('-')[0] != site):
                        continue
                if usbattached and not d['isUSBattached']:
                    continue
                if rebootable and not d['isRebootable']:
                    continue
                if updownloadable and not d['isUpDownloadable']:
                    continue
                if usbable and not d['isUSBable']:
                    continue
                if factoryresetable and not d['isFactoryResetable']:
                    continue
                if (not force) and d['isBusy']: # This device is busy and we don't force check it out.
                    continue
                if not d['isOperational']: # This device is not available.
                    continue
                if not min or sum([v for v in d.values() if isinstance(v, bool)]) < sum([v for v in min.values() if isinstance(v, bool)]):
                    min = d

            if min:
                d = min
                # Got an available device and check out it.
                if self.check_out(d['id'], jenkins_job, force):
                    return self.get(d['id'])['device'] # Get the latest device information.
                # Check out device failed.
                log('Check out device {} failed.'.format(d['id']), self.debug)
                return None

            # No devices found.
            log('No available devices.', self.debug)
            return None

        def matching_check_out_retry(self, product_name, tag=None, device_mac=None, firmware=None, variant=None, environment=None,
                uboot=None, location=None, site=None, jenkins_job=None, retry_counts=None, retry_delay=None, force=False, usbattached=None, rebootable=None, updownloadable=None, usbable=None, factoryresetable=None):
            """
            Check out a available device by specific conditions with retrying.

            [Arguments]
                retry_counts: integer (Optional)
                    Total counts to retry.
                retry_delay: integer (Optional)
                    Delay time for each retry.
                force: boolean (Optional)
                    Force to check out device.
                [Others]
                    Please refer to matching_check_out().

            [Returns]
                Reture device information (Please refer to get()) if it's success, or reture None.
            """
            if not retry_counts:
                retry_counts = self.retry_counts

            if not retry_delay:
                retry_delay = self.retry_delay

            # Keep looking for a available device and check out it.
            for remaining_count in reversed(xrange(int(retry_counts))):
                try:
                    check_out_device = self.matching_check_out(product_name, tag, device_mac, firmware, variant, environment, uboot,
                        location, site, jenkins_job, force, usbattached, rebootable, updownloadable, usbable, factoryresetable)
                    if check_out_device: # Found device.
                        remaining_count = 0 # not delay
                        return check_out_device
                except Exception as e:
                    log('An exception raised when checking out device: \n{}.'.format(repr(e)), self.debug)
                finally:
                    if remaining_count > 0: # Retry delay 
                        log('Retry after {0} seconds, remaining {1} retries...'.format(retry_delay, remaining_count), self.debug)
                        time.sleep(float(retry_delay))

            return None

        def device_view(self, device):
            """ Generate complete dict data from device object (of API response). """
            view = device.copy()
            view.pop('class', None)
            # Get adb gateway
            if view.get('adbGateway'):
                adb_gateway = self.invAPI.adb_gateway.get(view['adbGateway']['id'])
                view['adbGateway'] = {
                    'ipAddress': adb_gateway['adbGateway']['ipAddress'],
                    'port': adb_gateway['adbGateway']['port']
                }
            # Get adb server
            if view.get('adbServer'):
                adb_server = self.invAPI.adb_server.get(view['adbServer']['id'])
                view['adbServer'] = {
                    'ipAddress': adb_server['adbServer']['ipAddress'],
                    'port': adb_server['adbServer']['port']
                }
            # Get product
            product = self.invAPI.product.get(view['product']['id'])
            view['product'] = product['product']['name']
            # Get power switch
            if view.get('powerSwitch'):
                power_switch = self.get_power_switch(view['id'])
                view['powerSwitch'] = {
                    'ipAddress': power_switch['ipAddress'],
                    'port': power_switch['port']
                }
            # Get serial server
            if view.get('serialServer'):
                serial_server = self.get_serial_server(view['id'])
                view['serialServer'] = {
                    'ipAddress': serial_server['ipAddress'],
                    'port': serial_server['port']
                }
            # Get ssh gateway
            if view.get('sshGateway'):
                ssh_gateway = self.get_SSH_gateway(view['id'])
                view['sshGateway'] = {
                    'ipAddress': ssh_gateway['ipAddress'],
                    'port': ssh_gateway['port']
                }
            return unicode_to_str(view)

    class PowerSwitchAPI(object):

        def __init__(self, invAPI, debug):
            """
            API set of Power Switch resource.

            [Arguments]
                invAP: InventoryAPI object
                debug: boolean
                    Print debug messages or not.
            """
            self.invAPI = invAPI
            self.debug = debug

        def list(self):
            """
            List all power switchs on server.

            [Return Example]
                {'list': [{'class': 'com.wdc.PowerSwitch',
                           'dateCreated': '2017-02-09T09:07:21Z',
                           'id': 73,
                           'ipAddress': '10.136.137.147',
                           'lastUpdated': '2017-02-09T09:07:21Z',
                           'port': '4'}],
                 'message': None,
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('List all Power Switches', self.debug)
            url = str.format("{0}/powerSwitches", self.invAPI.url)
            data = {'max': self.invAPI.MAX_LIST_NUM}
            request = Request('GET', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def get(self, power_switch_id):
            """
            Get specific power switch with ID.

            [Return Example]
                {'message': None,
                 'powerSwitch': {'class': 'com.wdc.PowerSwitch',
                                 'dateCreated': '2017-02-09T10:17:17Z',
                                 'id': 78,
                                 'ipAddress': '1.1.1.1',
                                 'lastUpdated': '2017-02-09T10:17:17Z',
                                 'port': '30991'},
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Get Power Switch with ID:{}'.format(power_switch_id), self.debug)
            url = str.format("{0}/powerSwitches/{1}", self.invAPI.url, power_switch_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def create(self, ip_address, port):
            """
            Create a new power switch on server.

            [Arguments]
                ip_address: string
                    IP address of new power switch.
                port: string
                    Port number of new power switch.

            [Return Example]
                Example refer to get().
            """
            log('Create Power Switch with IP Address:{0} and port:{1}'.format(ip_address, port), self.debug)
            url = str.format("{0}/powerSwitches", self.invAPI.url)
            data = {'ipAddress': ip_address, 'port': port}
            request = Request('POST', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def update(self, power_switch_id, ip_address=None, port=None):
            """
            Update status to specific power switch with ID.

            [Arguments]
                power_switch_id: string
                    Power switch ID in server.
                ip_address: string (Optional)
                    IP address to update.
                port: string (Optional)
                    Port number to update.

            [Return Example]
                Example refer to get().
            """
            log('Update Power Switch:{0} with IP Address:{1} and port:{2}'.format(power_switch_id, ip_address, port), self.debug)
            url = str.format("{0}/powerSwitches/{1}", self.invAPI.url, power_switch_id)
            data = {'ipAddress': ip_address, 'port': port}
            request = Request('PUT', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def delete(self, power_switch_id):
            """
            Delete specific power switch with ID.

            [Return Example]
                {'message': 'Power Switch has been successfully deleted',
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Delete Power Switch with ID:{}'.format(power_switch_id), self.debug)
            url = str.format("{0}/powerSwitches/{1}", self.invAPI.url, power_switch_id)
            request = Request('DELETE', url)
            json_response = self.invAPI.rest_call(request)
            return json_response


    class SerialServerAPI(object):

        def __init__(self, invAPI, debug):
            """
            API set of Serial Server resource.

            [Arguments]
                invAP: InventoryAPI object
                debug: boolean
                    Print debug messages or not.
            """
            self.invAPI = invAPI
            self.debug = debug

        def list(self):
            """
            List all serial servers on server.

            [Return Example]
                {'list': [{'class': 'com.wdc.SerialServer',
                           'dateCreated': '2017-02-09T09:06:35Z',
                           'id': 65,
                           'ipAddress': '10.136.139.29',
                           'lastUpdated': '2017-02-09T09:06:35Z',
                           'port': '2323'}],
                 'message': None,
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('List all Serial Servers', self.debug)
            url = str.format("{0}/serialServers", self.invAPI.url)
            data = {'max': self.invAPI.MAX_LIST_NUM}
            request = Request('GET', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def get(self, serial_server_id):
            """
            Get specific serial server with ID.

            [Return Example]
                {'message': None,
                 'serialServer': {'class': 'com.wdc.SerialServer',
                                  'dateCreated': '2017-02-09T10:17:17Z',
                                  'id': 70,
                                  'ipAddress': '1.1.1.1',
                                  'lastUpdated': '2017-02-09T10:17:17Z',
                                  'port': '30991'},
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Get Serial Server with ID:{}'.format(serial_server_id), self.debug)
            url = str.format("{0}/serialServers/{1}", self.invAPI.url, serial_server_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def create(self, ip_address, port):
            """
            Create a new serial server on server.

            [Arguments]
                ip_address: string
                    IP address of new serial server.
                port: string
                    Port number of new serial server.

            [Return Example]
                Example refer to get().
            """
            log('Create Serial Server with IP Address:{0} and port:{1}'.format(ip_address, port), self.debug)
            url = str.format("{0}/serialServers", self.invAPI.url)
            data = {'ipAddress': ip_address, 'port': port}
            request = Request('POST', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def update(self, serial_server_id, ip_address=None, port=None):
            """
            Update status to serial server switch with ID.

            [Arguments]
                serial_server_id: string
                    Serial server ID in server.
                ip_address: string (Optional)
                    IP address to update.
                port: string (Optional)
                    Port number to update.

            [Return Example]
                Example refer to get().
            """
            log('Update Serial Server:{0} with IP Address:{1} and port:{2}'.format(serial_server_id, ip_address, port), self.debug)
            url = str.format("{0}/serialServers/{1}", self.invAPI.url, serial_server_id)
            data = {'ipAddress': ip_address, 'port': port}
            request = Request('PUT', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def delete(self, serial_server_id):
            """
            Delete specific serial server with ID.

            [Return Example]
                {'message': 'Serial Server has been successfully deleted',
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Delete Serial Server with ID:{}'.format(serial_server_id), self.debug)
            url = str.format("{0}/serialServers/{1}", self.invAPI.url, serial_server_id)
            request = Request('DELETE', url)
            json_response = self.invAPI.rest_call(request)
            return json_response


    class SSHGatewayAPI(object):

        def __init__(self, invAPI, debug):
            """
            API set of SSH Gateway resource.

            [Arguments]
                invAP: InventoryAPI object
                debug: boolean
                    Print debug messages or not.
            """
            self.invAPI = invAPI
            self.debug = debug

        def list(self):
            """
            List all SSH gateways on server.

            [Return Example]
                {'list': [{'class': 'com.wdc.SSHGateway',
                           'dateCreated': '2017-02-09T09:06:54Z',
                           'id': 65,
                           'ipAddress': '10.136.149.25',
                           'lastUpdated': '2017-02-09T09:06:54Z',
                           'port': '4564'}],
                 'message': None,
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('List all SSH Gateways', self.debug)
            url = str.format("{0}/SSHGateways", self.invAPI.url)
            data = {'max': self.invAPI.MAX_LIST_NUM}
            request = Request('GET', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def get(self, ssh_gateway_id):
            """
            Get specific SSH gateway with ID.

            [Return Example]
                {'message': None,
                 'sshGateway': {'class': 'com.wdc.SSHGateway',
                                'dateCreated': '2017-02-09T10:17:18Z',
                                'id': 70,
                                'ipAddress': '1.1.1.1',
                                'lastUpdated': '2017-02-09T10:17:18Z',
                                'port': '30991'},
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Get SSH Gateway with ID:{}'.format(ssh_gateway_id), self.debug)
            url = str.format("{0}/SSHGateways/{1}", self.invAPI.url, ssh_gateway_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def create(self, ip_address, port):
            """
            Create a new SSH gateway on server.

            [Arguments]
                ip_address: string
                    IP address of new SSH gateway.
                port: string
                    Port number of new SSH gateway.

            [Return Example]
                Example refer to get().
            """
            log('Create SSH Gateway with IP Address:{0} and port:{1}'.format(ip_address, port), self.debug)
            url = str.format("{0}/SSHGateways", self.invAPI.url)
            data = {'ipAddress': ip_address, 'port': port}
            request = Request('POST', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def update(self, ssh_gateway_id, ip_address=None, port=None):
            """
            Update status to SSH gateway switch with ID.

            [Arguments]
                ssh_gateway_id: string
                    SSH gateway ID in server.
                ip_address: string (Optional)
                    IP address to update.
                port: string (Optional)
                    Port number to update.

            [Return Example]
                Example refer to get().
            """
            log('Update SSH Gateway:{0} with IP Address:{1} and port:{2}'.format(ssh_gateway_id, ip_address, port), self.debug)
            url = str.format("{0}/SSHGateways/{1}", self.invAPI.url, ssh_gateway_id)
            data = {'ipAddress': ip_address, 'port': port}
            request = Request('PUT', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def delete(self, ssh_gateway_id):
            """
            Delete specific serial server with ID.

            [Return Example]
                {'message': 'SSHGateway has been successfully deleted',
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Delete SSH Gateway with ID:{}'.format(ssh_gateway_id), self.debug)
            url = str.format("{0}/SSHGateways/{1}", self.invAPI.url, ssh_gateway_id)
            request = Request('DELETE', url)
            json_response = self.invAPI.rest_call(request)
            return json_response


    class ProductAPI(object):

        def __init__(self, invAPI, debug):
            """
            API set of Product resource.

            [Arguments]
                invAP: InventoryAPI object
                debug: boolean
                    Print debug messages or not.
            """
            self.invAPI = invAPI
            self.debug = debug

        def list(self):
            """
            List all products on server.

            [Return Example]
                {'list': [{'class': 'com.wdc.Product',
                           'dateCreated': '2017-02-03T08:12:43Z',
                           'id': 125,
                           'lastUpdated': '2017-02-03T08:12:43Z',
                           'name': 'Monarch'}],
                 'message': None,
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('List all Products', self.debug)
            url = str.format("{0}/products", self.invAPI.url)
            data = {'max': self.invAPI.MAX_LIST_NUM}
            request = Request('GET', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def get(self, product_id):
            """
            Get specific product with ID.

            [Return Example]
                {'message': None,
                 'product': {'class': 'com.wdc.Product',
                             'dateCreated': '2017-02-09T10:17:11Z',
                             'id': 174,
                             'lastUpdated': '2017-02-09T10:17:11Z',
                             'name': 'DummyProduct_2'},
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Get Product with device ID:{}'.format(product_id), self.debug)
            url = str.format("{0}/products/{1}", self.invAPI.url, product_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def create(self, name):
            """
            Create a new product on server.

            [Arguments]
                name: string
                    Product name.

            [Return Example]
                Example refer to get().
            """
            log('Create Product with product name:{}'.format(name), self.debug)
            url = str.format("{0}/products", self.invAPI.url)
            data = {'name': name}
            request = Request('POST', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def update(self, product_id, name):
            """
            Update status to product switch with ID.

            [Arguments]
                product_id: string
                    Product ID in server.
                name: string
                    Product name.

            [Return Example]
                Example refer to get().
            """
            log('Update Product:{0} with product name:{1}'.format(product_id, name), self.debug)
            url = str.format("{0}/products/{1}", self.invAPI.url, product_id)
            data = {'name': name}
            request = Request('PUT', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def delete(self, product_id):
            """
            Delete specific product with ID.

            [Return Example]
                {'message': 'Product has been successfully deleted,
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Delete Product with ID:{}'.format(product_id), self.debug)
            url = str.format("{0}/products/{1}", self.invAPI.url, product_id)
            request = Request('DELETE', url)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def getDevices(self, product_id):
            """
            Find devices with product ID.

            [Arguments]
                product_id: string
                    Product ID in server.

            [Return Example]
                {'devices': [{'adbGateway': None,
                              'adbServer': None,
                              'class': 'com.wdc.Device',
                              'dateCreated': '2017-02-09T10:17:17Z',
                              'firmware': None,
                              'id': 119,
                              'internalIPAddress': None,
                              'isBusy': False,
                              'isOperational': False,
                              'jenkinsJob': None,
                              'lastUpdated': '2017-02-09T10:17:17Z',
                              'location': None,
                              'macAddress': 'FF:FF:FF:FF:FF:FF',
                              'powerSwitch': None,
                              'product': {'class': 'com.wdc.Product', 'id': 175},
                              'serialServer': None,
                              'sshGateway': None,
                              'uboot': None}],
                 'message': None,
                 'product': {'class': 'com.wdc.Product',
                             'dateCreated': '2017-02-09T10:17:17Z',
                             'id': 175,
                             'lastUpdated': '2017-02-09T10:17:17Z',
                             'name': 'DummyProductNew'},
                 'status': 'SUCCESS',
                 'statusCode': 1000}
             """
            log('Get the devices with product ID:{}'.format(product_id), self.debug)
            url = str.format("{0}/api/product/getDevices/{1}", self.invAPI.url, product_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response


    class ADBGatewayAPI(object):

        def __init__(self, invAPI, debug):
            """
            API set of ADB Gateway resource.

            [Arguments]
                invAP: InventoryAPI object
                debug: boolean
                    Print debug messages or not.
            """
            self.invAPI = invAPI
            self.debug = debug

        def list(self):
            """
            List all ADB gateways on server.

            [Return Example]
                {'list': [{'class': 'com.wdc.ADBGateway',
                           'dateCreated': '2017-02-09T05:42:40Z',
                           'id': 64,
                           'ipAddress': '10.136.144.121',
                           'lastUpdated': '2017-02-09T09:07:10Z',
                           'port': '5555'}],
                 'message': None,
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('List all ADB Gateways', self.debug)
            url = str.format("{0}/ADBGateways", self.invAPI.url)
            data = {'max': self.invAPI.MAX_LIST_NUM}
            request = Request('GET', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def get(self, adb_gateway_id):
            """
            Get specific ADB gateway with ID.

            [Return Example]
                {'adbGateway': {'class': 'com.wdc.ADBGateway',
                                'dateCreated': '2017-02-09T10:17:11Z',
                                'id': 71,
                                'ipAddress': '1.1.1.1',
                                'lastUpdated': '2017-02-09T10:17:11Z',
                                'port': '30991'},
                 'message': None,
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Get ADB Gateway with ID:{}'.format(adb_gateway_id), self.debug)
            url = str.format("{0}/ADBGateways/{1}", self.invAPI.url, adb_gateway_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def create(self, ip_address, port):
            """
            Create a new ADB gateway on server.

            [Arguments]
                ip_address: string
                    IP address of ADB gateway.
                port: string
                    Port number of ADB gateway.

            [Return Example]
                Example refer to get().
            """
            log('Create ADB Gateway with IP Address:{0} and port:{1}'.format(ip_address, port), self.debug)
            url = str.format("{0}/ADBGateways", self.invAPI.url)
            data = {'ipAddress': ip_address, 'port': port}
            request = Request('POST', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def update(self, adb_gateway_id, ip_address=None, port=None):
            """
            Update status to ADB gateway with ID.

            [Arguments]
                adb_gateway_id: string
                    ADB gateway ID in server.
                ip_address: string (Optional)
                    IP address of ADB gateway.
                port: string (Optional)
                    Port number of ADB gateway.

            [Return Example]
                Example refer to get().
            """
            log('Update ADB Gateway:{0} with IP Address:{1} and port:{2}'.format(adb_gateway_id, ip_address, port), self.debug)
            url = str.format("{0}/ADBGateways/{1}", self.invAPI.url, adb_gateway_id)
            data = {'ipAddress': ip_address, 'port': port}
            request = Request('PUT', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def delete(self, adb_gateway_id):
            """
            Delete specific ADB gateway with ID.

            [Return Example]
                {'message': 'ADB Gateway has been successfully deleted',
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Delete ADB Gateway with ID:{}'.format(adb_gateway_id), self.debug)
            url = str.format("{0}/ADBGateways/{1}", self.invAPI.url, adb_gateway_id)
            request = Request('DELETE', url)
            json_response = self.invAPI.rest_call(request)
            return json_response


    class ADBServerAPI(object):

        def __init__(self, invAPI, debug):
            """
            API set of ADB Server resource.

            [Arguments]
                invAP: InventoryAPI object
                debug: boolean
                    Print debug messages or not.
            """
            self.invAPI = invAPI
            self.debug = debug

        def list(self):
            """
            List all ADB servers on server.

            [Return Example]
                {'list': [{'class': 'com.wdc.ADBServer',
                           'dateCreated': '2017-02-09T05:42:49Z',
                           'id': 64,
                           'ipAddress': '10.136.139.30',
                           'lastUpdated': '2017-02-09T09:08:48Z',
                           'port': '5037'}],
                 'message': None,
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('List all ADB Servers', self.debug)
            url = str.format("{0}/ADBServers", self.invAPI.url)
            data = {'max': self.invAPI.MAX_LIST_NUM}
            request = Request('GET', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def get(self, adb_server_id):
            """
            Get specific ADB server with ID.

            [Return Example]
                {'adbServer': {'class': 'com.wdc.ADBServer',
                               'dateCreated': '2017-02-09T10:17:11Z',
                               'id': 71,
                               'ipAddress': '1.1.1.1',
                               'lastUpdated': '2017-02-09T10:17:11Z',
                               'port': '30991'},
                 'message': None,
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Get ADB Server with ID:{}'.format(adb_server_id), self.debug)
            url = str.format("{0}/ADBServers/{1}", self.invAPI.url, adb_server_id)
            request = Request('GET', url)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def create(self, ip_address, port):
            """
            Create a new ADB server on server.

            [Arguments]
                ip_address: string
                    IP address of ADB server.
                port: string
                    Port number of ADB server.

            [Return Example]
                Example refer to get().
            """
            log('Create ADB Server with IP Address:{0} and port:{1}'.format(ip_address, port), self.debug)
            url = str.format("{0}/ADBServers", self.invAPI.url)
            data = {'ipAddress': ip_address, 'port': port}
            request = Request('POST', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def update(self, adb_server_id, ip_address=None, port=None):
            """
            Update status to ADB server with ID.

            [Arguments]
                adb_server_id: string
                    ADB server ID in server.
                ip_address: string (Optional)
                    IP address of ADB gateway.
                port: string (Optional)
                    Port number of ADB gateway.

            [Return Example]
                Example refer to get().
            """
            log('Update ADB Server:{0} with IP Address:{1} and port:{2}'.format(adb_server_id, ip_address, port), self.debug)
            url = str.format("{0}/ADBServers/{1}", self.invAPI.url, adb_server_id)
            data = {'ipAddress': ip_address, 'port': port}
            request = Request('PUT', url, params=data)
            json_response = self.invAPI.rest_call(request)
            return json_response

        def delete(self, adb_server_id):
            """
            Delete specific ADB server with ID.

            [Return Example]
                {'message': 'ADB Server has been successfully deleted',
                 'status': 'SUCCESS',
                 'statusCode': 1000}
            """
            log('Delete ADB Server with ID:{}'.format(adb_server_id), self.debug)
            url = str.format("{0}/ADBServers/{1}", self.invAPI.url, adb_server_id)
            request = Request('DELETE', url)
            json_response = self.invAPI.rest_call(request)
            return json_response


class InventoryException(Exception):
    def __init__(self, status=None, status_code=None, message=None):
        self.status = status
        self.status_code = status_code
        self.message = message


def log(message, debug):
    """ Logging message if debug set as True, or do nothing. 
    """
    if not message:
        return
    elif not debug:
        return

    if log_inst:
        log_inst.info(message)
    else: # Use print instead of logging module if it's used in standalone.
        print message
