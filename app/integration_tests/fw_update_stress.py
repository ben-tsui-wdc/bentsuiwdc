# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from bat_scripts_new.fw_update_utility import FWUpdateUtility


class FWUpdateStress(FWUpdateUtility):

    TEST_SUITE = 'Firmware_Update_Stress_Test'
    TEST_NAME = 'Firmware_Update_Stress_Test'
    # Popcorn
    TEST_JIRA_ID = 'KAM-15038,KAM-13986'
    REPORT_NAME = 'Stress'

    TEST_FAILED = False

    # Do not attach owner when the test starts
    SETTINGS = {
        'disable_firmware_consistency': True,
        'uut_owner': False
    }

    def test(self):
        try:
            super(FWUpdateStress, self).test()
            test_result = 'Passed'
        except Exception as ex:
            self.log.error('Firmware update failed! Error message: {}'.format(repr(ex)))
            test_result = 'Failed'
            self.TEST_FAILED = True

        self.log.info("*** Firmware Update Test Result: {} ***".format(test_result))
        self.data.test_result['fwUpdateStressResult'] = test_result

    def after_loop(self):
        if self.TEST_FAILED:
            raise self.err.TestFailure('At least 1 of the iterations failed!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Firmware update stress test on Kamino Android ***
        Examples: ./start.sh integration_tests/fw_update_stress.py -ip 10.136.137.159 -env prod -var user \
                  --loop_times 200 --local_image --keep_fw_img --logstash http://10.92.234.42:8000 \
        """)
    # Test Arguments
    parser.add_argument('--clean_restsdk_db', help='Clear restsdk database', action='store_true', default=False)
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    parser.add_argument('--keep_fw_img', action='store_true', default=False, help='Keep downloaded firmware')
    parser.add_argument('--file_server_ip', default='fileserver.hgst.com', help='File server IP address')
    args = parser.parse_args()

    test = FWUpdateStress(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)