# -*- coding: utf-8 -*-
""" Case to check the default log url exist in the device properties
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.bat_scripts.firmware_update import FirmwareUpdate


class CheckNetworkRecovery(KDPTestCase):
    TEST_SUITE = 'KDP_Functional_Device_Test'
    TEST_NAME = 'KDP-5819 - Property persist.wd.network.recovery value disable check'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5819'
    REPORT_NAME = 'Functional'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.network_recovery_prop = 'persist.wd.network.recovery'
        self.link_status_prop = 'device.connectivity.linkstatus'
        self.gateway_prop = 'device.connectivity.gw'
        self.timeout = 8 * 60  # in prod, network recovery should be changed to disabled after 6 mins after OTA

    def test(self):
        env_dict = self.env.dump_to_dict()
        env_dict['force_update'] = True
        firmware_update = FirmwareUpdate(env_dict)
        firmware_update.main()

        self.log.info('Checking the network recovery property after firmware update')
        network_recovery_state = self.get_device_property(self.network_recovery_prop)
        if self.env.cloud_env == 'prod':
            self.TEST_NAME = 'KDP-5818 - Property persist.wd.network.recovery value enable check'
            self.TEST_JIRA_ID = 'KDP-5818,KDP-5852'
            if not network_recovery_state or network_recovery_state == 'disable':
                raise self.err.TestFailure("The {} should be enabled after firmware update, "
                                           "but it's {}!".format(self.network_recovery_prop, network_recovery_state))
            self.log.info('Check if the device connectivity properties are correct, this might need a few minutes')
            retry_interval = 30
            max_retries = self.timeout / retry_interval
            for retries in range(max_retries):
                if self.check_property_retries(retries, max_retries, retry_interval, self.link_status_prop, 'OK'):
                    continue
                if self.check_property_retries(retries, max_retries, retry_interval, self.gateway_prop, 'OK'):
                    continue
                self.log.info("Both properties {} and {} are OK".format(self.link_status_prop, self.gateway_prop))
                break
            else:
                raise self.err.TestFailure("The connectivity properties are not all OK, test failed!")

            retry_interval = 60
            max_retries = self.timeout / retry_interval
            for retries in range(max_retries):
                if self.check_property_retries(retries, max_retries, retry_interval,
                                               self.network_recovery_prop, 'disable'):
                    continue
                break
            else:
                raise self.err.TestFailure("The {} should be changed to disabled after 6 minutes. Test is FAILED!".
                                           format(self.network_recovery_prop))
            self.log.info('The {} is changed to disabled. Test is PASSED!'.format(self.network_recovery_prop))
        else:
            if not network_recovery_state or network_recovery_state == 'disable':
                self.log.info('The {} is "disable" as expected. Test is PASSED!')
            else:
                raise self.err.TestSkipped("The {} should always be disabled in dev1/qa1 env, "
                                           "but it's {}. Test is FAILED!".format(self.network_recovery_prop,
                                                                                 network_recovery_state))

    def get_device_property(self, field):
        return_code, propery_value = self.ssh_client.execute('getprop {}'.format(field))
        if return_code != 0:
            raise self.err.TestSkipped("Fail to get the property: {}!".format(field))
        return propery_value

    def check_property_retries(self, retries, max_retries, retry_interval, property, expect_status):
        # If the properties are not 'OK', return True and retry it
        property_status = self.get_device_property(property)
        if property_status != expect_status:
            self.log.info('The property {} is "{}" but not "{}", retry after {} seconds. {} retries left...'.format(
                property, property_status, expect_status, retry_interval, max_retries - retries))
            time.sleep(retry_interval)
            return True
        else:
            self.log.info('The property {} is "OK" as expected'.format(property))
            return False


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_network_recovery.py.py --uut_ip 10.92.224.68\
        """)

    test = CheckNetworkRecovery(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
