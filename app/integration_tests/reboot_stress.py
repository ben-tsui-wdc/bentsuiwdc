# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from bat_scripts_new.reboot import Reboot


class RebootStress(Reboot):

    TEST_SUITE = 'Reboot_Stress_Test'
    TEST_NAME = 'Reboot_Stress_Test'
    # Popcorn
    TEST_JIRA_ID = 'KAM-14131,KAM-13971'
    REPORT_NAME = 'Stress'

    TEST_FAILED = False

    def test(self):
        try:
            super(RebootStress, self).test()
            test_result = 'Passed'
        except Exception as ex:
            self.log.error('Reboot failed! Error message: {}'.format(repr(ex)))
            test_result = 'Failed'
            self.TEST_FAILED = True

        self.log.info("*** Reboot Test Result: {} ***".format(test_result))
        self.data.test_result['rebootStressResult'] = test_result

    def after_loop(self):
        if self.TEST_FAILED:
            raise self.err.TestFailure('At least 1 of the iterations failed!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Reboot stress test on Kamino Android ***
        Examples: ./start.sh integration_tests/reboot_stress.py -ip 10.136.137.159 -env qa1 \
                  --loop_times 500 --wait_device --no_rest_api --logstash http://10.92.234.42:8000 \
        """)
    # Test Arguments
    parser.add_argument('-wait', '--wait_device', help='Wait for device boot completed', action='store_true')
    parser.add_argument('-noapi', '--no_rest_api', help='Not use restapi to reboot device', action='store_true')
    
    test = RebootStress(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)