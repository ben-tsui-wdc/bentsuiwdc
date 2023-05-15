# -*- coding: utf-8 -*-
""" Test cases to connect 5G from 2G [KDP-286]
"""
__author__ = "Vodka Chen <vodka.chen@wdc.com>"
__author_2__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP
from platform_libraries.common_utils import ClientUtils


class WifiChange5GTo2G(KDPTestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'KDP-286: Change connect Wi-Fi AP 5G to 2.4G'
    # Popcorn
    TEST_JIRA_ID = 'KDP-286'
    REPORT_NAME = 'Functional'

    SETTINGS = {
        'uut_owner': True,
        'serial_client': True,
        'ssh_client': True
    }
    
    def declare(self):
        self.timeout = 300

    def init(self):
        self.client_utils = ClientUtils()
        self.test_file = 'TEST_WIFI_KDP_286.png'
        self.upload_file_path = '{0}/{1}/{2}'.format(KDP.USER_ROOT_PATH,
                                                     self.uut_owner.get_user_id(escape=True), self.test_file)

    def before_test(self):
        pass

    def test(self):
        self.log.info("Connect 5G Wi-Fi")
        self.serial_client.retry_for_connect_WiFi_kdp(ssid=self.wifi_ssid_5g, password=self.wifi_password_5g)
        self.env.check_ip_change_by_console()

        self.log.info('Create a dummy file and upload to test device')
        self._verify_upload_files()

        self.log.info("Change to connect 2G Wi-Fi")
        self.serial_client.retry_for_connect_WiFi_kdp(ssid=self.wifi_ssid_2g, password=self.wifi_password_2g)
        self.env.check_ip_change_by_console()

        self.log.info('Try to upload a file after Wi-Fi change')
        self._verify_upload_files()

    def after_test(self):
        self.client_utils.delete_local_file(self.test_file)
        self._delete_remote_file()
        self.log.info("Revert Wi-Fi setting if SSID does not match the default one")
        if self.env.ap_ssid and not self.serial_client.verify_ssid_is_match(self.env.ap_ssid):
            self.serial_client.retry_for_connect_WiFi_kdp(ssid=self.env.ap_ssid, password=self.env.ap_password)
            self.env.check_ip_change_by_console()

    def _verify_upload_files(self):
        self.client_utils.create_random_file(self.test_file)
        self.log.info("Get the local file checksum")
        checksum_original = self.client_utils.md5_checksum(self.test_file)
        self._delete_remote_file()

        with open(self.test_file, 'rb') as f:
            self.uut_owner.chuck_upload_file(file_object=f, file_name=self.test_file)
        if self.ssh_client.check_file_in_device(self.upload_file_path):
            self.log.info('Upload test file to device successfully!')
        else:
            raise self.err.TestFailure('Upload test file to device failed!')

        self.log.info("Getting remote file checksum")
        checksum_upload = self.ssh_client.get_file_md5_checksum(self.upload_file_path)
        self.log.info('Local file md5: {}'.format(checksum_original))
        self.log.info('Remote file md5: {}'.format(checksum_upload))
        if checksum_upload != checksum_original:
            raise self.err.TestFailure('File md5 checksum comparison failed!')

    def _delete_remote_file(self):
        if self.ssh_client.check_file_in_device(self.upload_file_path):
            self.log.info("{0} exist in NAS, delete it".format(self.test_file))
            data_id = self.uut_owner.get_data_id_list(type='file', data_name=self.test_file)
            self.uut_owner.delete_file(data_id)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** change wifi and verify ***
        Examples: ./run.sh functional_tests/wifi_change_5G_to_2G.py --uut_ip 10.92.224.68 \
        """)
    parser.add_argument('--wifi_ssid_2g', help="", default='R7000_24')
    parser.add_argument('--wifi_password_2g', help="", default='fituser99')
    parser.add_argument('--wifi_ssid_5g', help="", default='R7000_50')
    parser.add_argument('--wifi_password_5g', help="", default='fituser99')
    test = WifiChange5GTo2G(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
