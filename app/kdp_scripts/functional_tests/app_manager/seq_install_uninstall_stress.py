# -*- coding: utf-8 -*-
""" Test case to loop and sequential install app -> uninstall app to test app manager.
    https://jira.wdmv.wdc.com/browse/KDP-457
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.functional_tests.app_manager.install_app import InstallApp
from kdp_scripts.functional_tests.app_manager.uninstall_app import UninstallApp


class SeqInstallUninstallAppStress(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-457 - Sequential Install and Uninstall app stress test'
    REPORT_NAME = 'Stress'
    TEST_JIRA_ID = 'KDP-457,KDP-203,KDP-208'

    def before_loop(self):
        self.TEST_FAILED = False
        install_env_dict = self.env.dump_to_dict()
        install_env_dict['app_id'] = self.app_id
        install_env_dict['check_app_install'] = self.check_app_install
        self.install_app = InstallApp(install_env_dict)
        uninstall_env_dict = self.env.dump_to_dict()
        uninstall_env_dict['app_id'] = self.app_id
        self.uninstall_app = UninstallApp(uninstall_env_dict)
        self.install_app.before_test()

    def test(self):
        try:
            self.install_app.test()
            self.log.info('Interval time between Install and Unstall App, sleep {} secs ... '.format(self.interval_time))
            time.sleep(int(self.interval_time))
            self.uninstall_app.test()
            test_result = 'Passed'
        except Exception as ex:
            self.log.error('Sequence install & uninstall app failed! Error message: {}'.format(repr(ex)))
            test_result = 'Failed'
            self.TEST_FAILED = True
            raise
        self.log.info("*** Install & Uninstall App Test Result: {} ***".format(test_result))
        self.data.test_result['KDPSeqInstallUninstallAppResult'] = test_result

    def after_loop(self):
        self.install_app.after_test()
        if self.TEST_FAILED:
            raise self.err.TestFailure('At least 1 of the iterations failed!')

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Sequential Install&Uninstall App stress test ***
        Examples: ./start.sh kdp_scripts/functional_tests/app_manager/seq_install_uninstall_stress.py -ip 10.92.234.16 -env qa1 \
                  --loop_times 50 --logstash http://10.92.234.101:8000 \
        """)

    parser.add_argument('-itime', '--interval_time', default=15, help='Interval time between Install and Uninstall app')
    parser.add_argument('-appid', '--app_id', help='App ID to installed')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    
    test = SeqInstallUninstallAppStress(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)