""" Unit test for inventory API.

Base on repo: TestAutomation/taut version 7a598ae89fe.
"""
# std modules
import unittest
# platform modules
from platform_libraries.inventoryAPI import InventoryAPI


class TestInventoryAPI(unittest.TestCase):

    # FIXME: if find any other good way to pass input arguments.
    SERVER_URL = 'http://sevtw-inventory-server.hgst.com:8010/InventoryServer'
    DEBUG = False 

    def setUp(self):
        inv = InventoryAPI(self.SERVER_URL, self.DEBUG)
        self.device = inv.device
        self.power_switch = inv.power_switch
        self.serial_server = inv.serial_server
        self.ssh_gateway = inv.ssh_gateway
        self.product = inv.product
        self.adb_gateway = inv.adb_gateway
        self.adb_server = inv.adb_server

    def test_product_class(self):
        dummy_product = {'name': 'DummyProduct'}
        dummy_product_update = {'name': 'DummyProductNew'}
        dummy_device = {'mac_address': 'FF:FF:FF:FF:FF:FF'}
        # Test list function
        result = self.product.list()
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Create a new dummy product first, and use it to test the other functions
        result = self.product.create(**dummy_product)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        p_id = result['product']['id']

        # Test get function
        result = self.product.get(p_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['product']['name'], dummy_product['name'])

        # Test update function
        result = self.product.update(p_id, **dummy_product_update)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Check update result by get function
        result = self.product.get(p_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['product']['name'], dummy_product_update['name'])

        # Test getDevice function, we'll need to create one dummy device first
        result = self.device.create(product_id=p_id, **dummy_device)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        d_id = result['device']['id']

        result = self.product.getDevices(p_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['devices'][0]['product']['id'], p_id)

        # Delete dummy device
        result = self.device.delete(d_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Test delete function
        result = self.product.delete(p_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

    def test_device_class(self):
        def _create_dummy_product(name):
            dummy_product = {'name': name}
            result = self.product.create(**dummy_product)
            self.assertIn('status', result)
            self.assertEqual(result['status'], 'SUCCESS')
            return result['product']['id']

        def _delete_dummy_product(p_id):
            result = self.product.delete(p_id)
            self.assertIn('status', result)
            self.assertEqual(result['status'], 'SUCCESS')

        dummy_device = {'mac_address': 'FF:FF:FF:FF:FF:FF',
                        'tag': 'TAG1',
                        'internal_ip_address': '1.1.1.1',
                        'location': 'MV-999',
                        'firmware': '0.0.001',
                        'variant': 'user',
                        'environment': 'QA1',
                        'uboot': '0.0.1',
                        'product_id': _create_dummy_product(name='DummyProduct_1'),
                        'power_switch_id': None,
                        'ssh_gateway_id': None,
                        'serial_server_id': None}
        dummy_device_update = {'mac_address': 'EE:EE:EE:EE:EE:EE',
                               'tag': 'TAG2',
                               'internal_ip_address': '2.2.2.2',
                               'location': 'MV-888',
                               'firmware': '0.0.002',
                               'variant': 'prod',
                               'environment': 'PROD',
                               'uboot': '0.0.2',
                               'product_id': _create_dummy_product(name='DummyProduct_2'),
                               'is_operational': True}
        # Test list function
        result = self.device.list()
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Create a new dummy device first, and use it to test the other functions
        result = self.device.create(**dummy_device)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        d_id = result['device']['id']

        # Test get function
        result = self.device.get(d_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['device']['product']['id'], dummy_device['product_id'])
        self.assertEqual(result['device']['tag'], dummy_device['tag'])
        self.assertEqual(result['device']['macAddress'], dummy_device['mac_address'])
        self.assertEqual(result['device']['internalIPAddress'], dummy_device['internal_ip_address'])
        self.assertEqual(result['device']['location'], dummy_device['location'])
        self.assertEqual(result['device']['firmware'], dummy_device['firmware'])
        self.assertEqual(result['device']['variant'], dummy_device['variant'])
        self.assertEqual(result['device']['environment'], dummy_device['environment'])
        self.assertEqual(result['device']['uboot'], dummy_device['uboot'])
        self.assertEqual(result['device']['powerSwitch'], dummy_device['power_switch_id'])
        self.assertEqual(result['device']['sshGateway'], dummy_device['ssh_gateway_id'])
        self.assertEqual(result['device']['serialServer'], dummy_device['ssh_gateway_id'])

        # Test update function
        result = self.device.update(d_id, **dummy_device_update)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Check update result by get function
        result = self.device.get(d_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['device']['product']['id'], dummy_device_update['product_id'])
        self.assertEqual(result['device']['tag'], dummy_device_update['tag'])
        self.assertEqual(result['device']['macAddress'], dummy_device_update['mac_address'])
        self.assertEqual(result['device']['internalIPAddress'], dummy_device_update['internal_ip_address'])
        self.assertEqual(result['device']['location'], dummy_device_update['location'])
        self.assertEqual(result['device']['firmware'], dummy_device_update['firmware'])
        self.assertEqual(result['device']['variant'], dummy_device_update['variant'])
        self.assertEqual(result['device']['environment'], dummy_device_update['environment'])
        self.assertEqual(result['device']['uboot'], dummy_device_update['uboot'])
        self.assertEqual(result['device']['isOperational'], dummy_device_update['is_operational'])
        # Test is_available function
        result = self.device.is_available(d_id)
        self.assertEqual(result, True)

        # Test check_out function
        result = self.device.check_out(d_id, jenkins_job='unit_test')
        self.assertNotEqual(result, None)

        # Test get_device_by_job function
        result = self.device.get_device_by_job('unit_test')
        self.assertEqual(result['id'], d_id)

        # Test get_device_by_ip function
        result = self.device.get_device_by_ip(result['internalIPAddress'])
        self.assertEqual(result['id'], d_id)

        # Test check_in function with isOperational = False
        result = self.device.check_in(d_id, is_operational=False)
        self.assertNotEqual(result, None)

        # Check isOperational value
        result = self.device.get(d_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['device']['isOperational'], False)

        # Recovery device
        result = self.device.update(d_id, **dummy_device_update)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Test matching_check_out_retry function
        # Get device product name first, the product_id is DummyProduct_2 after testing update function
        result = self.product.get(dummy_device_update['product_id'])
        if result.get('status') == 'SUCCESS':
            def _check_parameter_test_response(response, d_id, jenkins_job):
                self.assertEqual(response['id'], d_id)
                self.assertEqual(response['jenkinsJob'], jenkins_job)
                result = self.device.check_in(d_id)
                self.assertNotEqual(response, None)

            p_name = result['product']['name']
            d_tag = dummy_device_update['tag']
            d_fw = dummy_device_update['firmware']
            d_variant = dummy_device_update['variant']
            d_environment = dummy_device_update['environment']
            d_uboot = dummy_device_update['uboot']
            d_location = dummy_device_update['location']
            d_site = d_location.split('-')[0]

            # Test with product_name parameter
            device = self.device.matching_check_out_retry('NOT_EXIST',  retry_counts='1', retry_delay='0.001')
            self.assertEqual(device, None)

            # Test with jenkins_job parameter
            jenkins_job = 'unit_test_1'
            device = self.device.matching_check_out_retry(p_name, jenkins_job=jenkins_job, retry_counts='1', retry_delay='10')
            _check_parameter_test_response(device, d_id, jenkins_job)

            # Test with tag parameter
            jenkins_job = 'unit_test_2'
            device = self.device.matching_check_out_retry(p_name, tag=d_tag, jenkins_job=jenkins_job, retry_counts='1', retry_delay='10')
            _check_parameter_test_response(device, d_id, jenkins_job)

            # Test with firmware parameter
            jenkins_job = 'unit_test_2'
            device = self.device.matching_check_out_retry(p_name, firmware=d_fw, jenkins_job=jenkins_job, retry_counts='1', retry_delay='10')
            _check_parameter_test_response(device, d_id, jenkins_job)

            # Test with variant parameter
            jenkins_job = 'unit_test_2'
            device = self.device.matching_check_out_retry(p_name, variant=d_variant, jenkins_job=jenkins_job, retry_counts='1', retry_delay='10')
            _check_parameter_test_response(device, d_id, jenkins_job)

            # Test with environment parameter
            jenkins_job = 'unit_test_2'
            device = self.device.matching_check_out_retry(p_name, environment=d_environment, jenkins_job=jenkins_job, retry_counts='1', retry_delay='10')
            _check_parameter_test_response(device, d_id, jenkins_job)

            # Test with uboot parameter
            jenkins_job = 'unit_test_3'
            device = self.device.matching_check_out_retry(p_name, uboot=d_uboot, jenkins_job=jenkins_job, retry_counts='1', retry_delay='10')
            _check_parameter_test_response(device, d_id, jenkins_job)

            # Test with location parameter
            jenkins_job = 'unit_test_4'
            device = self.device.matching_check_out_retry(p_name, location=d_location, jenkins_job=jenkins_job, retry_counts='1', retry_delay='10')
            _check_parameter_test_response(device, d_id, jenkins_job)

            # Test with site parameter
            jenkins_job = 'unit_test_5'
            device = self.device.matching_check_out_retry(p_name, site=d_site, jenkins_job=jenkins_job, retry_counts='1', retry_delay='10')
            _check_parameter_test_response(device, d_id, jenkins_job)

            # Test with all parameters
            jenkins_job = 'unit_test_6'
            device = self.device.matching_check_out_retry(p_name, tag=d_tag, firmware=d_fw, variant=d_variant,
                environment=d_environment, uboot=d_uboot, location=d_location, site=d_site,
                jenkins_job=jenkins_job, retry_counts='1', retry_delay='10')
            _check_parameter_test_response(device, d_id, jenkins_job)

            # Test retry feature
            import time
            start_time = time.time()
            device = self.device.matching_check_out_retry(p_name, firmware='d_fw', retry_counts='5', retry_delay='1')
            total_exec_time = time.time() - start_time
            self.assertEqual(device, None)
            self.assertGreaterEqual(total_exec_time, (5-1)*1)
        else:
            self.fail('Get device product name failed, cannot test matching_check_out_retry command!')

        # Test get_SSH_gateway function
        result = self.device.get_SSH_gateway(d_id)
        self.assertEqual(result, dummy_device['ssh_gateway_id'])

        # Test get_serial_server function
        result = self.device.get_serial_server(d_id)
        self.assertEqual(result, dummy_device['serial_server_id'])

        # Test get_power_switch function
        result = self.device.get_power_switch(d_id)
        self.assertEqual(result, dummy_device['power_switch_id'])

        # Test delete function
        result = self.device.delete(d_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Clean dummy products
        _delete_dummy_product(p_id=dummy_device['product_id'])
        _delete_dummy_product(p_id=dummy_device_update['product_id'])

    def test_power_switch_class(self):
        dummy_ps = {'ip_address': '1.1.1.1',
                    'port': '30991'}
        dummy_ps_update = {'ip_address': '2.2.2.2',
                           'port': '30999'}
        # Test list function
        result = self.power_switch.list()
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Create a new dummy device first, and use it to test the other functions
        result = self.power_switch.create(**dummy_ps)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        ps_id = result['powerSwitch']['id']

        # Test get function
        result = self.power_switch.get(ps_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['powerSwitch']['ipAddress'], dummy_ps['ip_address'])
        self.assertEqual(result['powerSwitch']['port'], dummy_ps['port'])

        # Test update function
        result = self.power_switch.update(ps_id, **dummy_ps_update)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Check update result by get function
        result = self.power_switch.get(ps_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['powerSwitch']['ipAddress'], dummy_ps_update['ip_address'])
        self.assertEqual(result['powerSwitch']['port'], dummy_ps_update['port'])

        # Test delete function
        result = self.power_switch.delete(ps_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

    def test_serial_server_class(self):
        dummy_ss = {'ip_address': '1.1.1.1',
                    'port': '30991'}
        dummy_ss_update = {'ip_address': '2.2.2.2',
                           'port': '30999'}
        # Test list function
        result = self.serial_server.list()
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Create a new dummy device first, and use it to test the other functions
        result = self.serial_server.create(**dummy_ss)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        ss_id = result['serialServer']['id']

        # Test get function
        result = self.serial_server.get(ss_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['serialServer']['ipAddress'], dummy_ss['ip_address'])
        self.assertEqual(result['serialServer']['port'], dummy_ss['port'])

        # Test update function
        result = self.serial_server.update(ss_id, **dummy_ss_update)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Check update result by get function
        result = self.serial_server.get(ss_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['serialServer']['ipAddress'], dummy_ss_update['ip_address'])
        self.assertEqual(result['serialServer']['port'], dummy_ss_update['port'])

        # Test delete function
        result = self.serial_server.delete(ss_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

    def test_ssh_gateway_class(self):
        dummy_sg = {'ip_address': '1.1.1.1',
                    'port': '30991'}
        dummy_sg_update = {'ip_address': '2.2.2.2',
                           'port': '30999'}
        # Test list function
        result = self.ssh_gateway.list()
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Create a new dummy device first, and use it to test the other functions
        result = self.ssh_gateway.create(**dummy_sg)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        sg_id = result['sshGateway']['id']

        # Test get function
        result = self.ssh_gateway.get(sg_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['sshGateway']['ipAddress'], dummy_sg['ip_address'])
        self.assertEqual(result['sshGateway']['port'], dummy_sg['port'])

        # Test update function
        result = self.ssh_gateway.update(sg_id, **dummy_sg_update)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Check update result by get function
        result = self.ssh_gateway.get(sg_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['sshGateway']['ipAddress'], dummy_sg_update['ip_address'])
        self.assertEqual(result['sshGateway']['port'], dummy_sg_update['port'])

        # Test delete function
        result = self.ssh_gateway.delete(sg_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

    def test_adb_gateway_class(self):
        dummy_ag = {'ip_address': '1.1.1.1',
                    'port': '30991'}
        dummy_ag_update = {'ip_address': '2.2.2.2',
                           'port': '30999'}
        # Test list function
        result = self.adb_gateway.list()
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Create a new dummy device first, and use it to test the other functions
        result = self.adb_gateway.create(**dummy_ag)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        sg_id = result['adbGateway']['id']

        # Test get function
        result = self.adb_gateway.get(sg_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['adbGateway']['ipAddress'], dummy_ag['ip_address'])
        self.assertEqual(result['adbGateway']['port'], dummy_ag['port'])

        # Test update function
        result = self.adb_gateway.update(sg_id, **dummy_ag_update)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Check update result by get function
        result = self.adb_gateway.get(sg_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['adbGateway']['ipAddress'], dummy_ag_update['ip_address'])
        self.assertEqual(result['adbGateway']['port'], dummy_ag_update['port'])

        # Test delete function
        result = self.adb_gateway.delete(sg_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

    def test_adb_server_class(self):
        dummy_as = {'ip_address': '1.1.1.1',
                    'port': '30991'}
        dummy_as_update = {'ip_address': '2.2.2.2',
                           'port': '30999'}
        # Test list function
        result = self.adb_server.list()
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Create a new dummy device first, and use it to test the other functions
        result = self.adb_server.create(**dummy_as)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        sg_id = result['adbServer']['id']

        # Test get function
        result = self.adb_server.get(sg_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['adbServer']['ipAddress'], dummy_as['ip_address'])
        self.assertEqual(result['adbServer']['port'], dummy_as['port'])

        # Test update function
        result = self.adb_server.update(sg_id, **dummy_as_update)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

        # Check update result by get function
        result = self.adb_server.get(sg_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['adbServer']['ipAddress'], dummy_as_update['ip_address'])
        self.assertEqual(result['adbServer']['port'], dummy_as_update['port'])

        # Test delete function
        result = self.adb_server.delete(sg_id)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'SUCCESS')

if __name__ == '__main__':
    unittest.main()
