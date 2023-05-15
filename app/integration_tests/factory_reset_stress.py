# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from bat_scripts_new.factory_reset import FactoryReset


class FactoryResetStress(FactoryReset):

    TEST_SUITE = 'Factory_Reset_Test'
    TEST_NAME = 'Factory_Reset_Test'
    # Popcorn
    TEST_JIRA_ID = 'KAM-14130,KAM-13972'
    REPORT_NAME = 'Stress'

    TEST_FAILED = False

    def before_test(self):
        if self.env.loop_times != 1 and self.env.iteration != 1:
            self.log.info("Clean rest api session info before next iteration")
            if self.env.cloud_env == 'prod':
                with_cloud_connected = False
            else:
                with_cloud_connected = True
            self.uut_owner.init_session(with_cloud_connected=with_cloud_connected)
            self.log.warning("Wait 30 secs before testing due to KAM200-4323")
            time.sleep(30)

    def test(self):
        try:
            super(FactoryResetStress, self).test()
            test_result = 'Passed'
        except Exception as ex:
            self.log.error('Factory reset failed! Error message: {}'.format(repr(ex)))
            test_result = 'Failed'
            self.TEST_FAILED = True
            raise

        self.log.info("*** Factory reset Test Result: {} ***".format(test_result))
        self.data.test_result['factoryResetResult'] = test_result

    def after_loop(self):
        if self.TEST_FAILED:
            raise self.err.TestFailure('At least 1 of the iterations failed!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Factory reset stress test on Kamino Android ***
        Examples: ./start.sh integration_tests/factory_reset_stress.py -ip 10.136.137.159 -env qa1\
                  --loop_times 200 --logstash http://10.92.234.42:8000 \
        """)
    # Test Arguments
    parser.add_argument('-noapi', '--no_rest_api', help='Not use restapi to reboot device', action='store_true')
    args = parser.parse_args()

    test = FactoryResetStress(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)