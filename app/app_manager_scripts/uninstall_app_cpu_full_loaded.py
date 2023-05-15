# -*- coding: utf-8 -*-
""" Test case to test uninstall app while CPU usage up to 90-100%
    https://jira.wdmv.wdc.com/browse/KAM-32524
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.uninstall_app import UninstallApp


class UninstallAppCPUFullLoaded(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32524 - Uninstall app while CPU usage up to 90-100%'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32524'
    PRIORITY = 'Critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.check_pm_list = False
        self.app_id = None
        self.stress_tool = 'cpu_stress'
        self.stress_tool_path = 'app_manager_scripts/{}'.format(self.stress_tool)
        self.cpu_stress_folder = '/data/wd/diskVolume0'

    def before_test(self):
        env_dict = self.env.dump_to_dict()
        env_dict['app_id'] = self.app_id
        env_dict['check_pm_list'] = self.check_pm_list
        self.uninstall_app = UninstallApp(env_dict)
        self.uninstall_app.before_test()

    def test(self):
        self.log.info('Start to run stress tool to let test device with CPU 90~100 percent loaded ...')
        self.adb.push(local=self.stress_tool_path, remote=self.cpu_stress_folder)
        response = False
        check_cpu_stress = False
        timeout = 60
        self.timing.start()
        while not check_cpu_stress:
            while not response and not self.timing.is_timeout(timeout):
                response = self.adb.executeShellCommand('busybox nohup {0}/{1} -c 4'.format(self.cpu_stress_folder, self.stress_tool))[0]
                time.sleep(1)
            check_cpu_stress = self.adb.executeShellCommand('top -m 5 -n 2')[0]
            if not self.stress_tool in check_cpu_stress:
                if self.timing.is_timeout(timeout):
                    raise self.err.TestSkipped('Execute {} failed ! Skipped the test !!'.format(self.stress_tool))
                    break
                check_cpu_stress = False
        time.sleep(10)
        self.uninstall_app.test()
        self.log.info("*** Uninstall app while CPU usage up to 90-100%, Test PASSED !!!")

    def after_test(self):
        self.log.info('Start to kill {} progress ...'.format(self.stress_tool))
        self.adb.executeShellCommand("busybox pgrep {} | xargs kill".format(self.stress_tool))


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Uninstall app while CPU usage up to 90-100% test ***
        Examples: ./start.sh app_manager_scripts/uninstall_app_cpu_full_loaded.py -ip 10.92.234.16 -env qa1 
        --app_id com.wdc.importapp.ibi -chkpl
        """)

    parser.add_argument('-appid', '--app_id', help='App ID to uninstalled')
    parser.add_argument('-chkpl', '--check_pm_list', help='Check pm list of app package', action='store_true')
    
    test = UninstallAppCPUFullLoaded(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)