# -*- coding: utf-8 -*-
""" Case to check the log package contains syslog
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import os
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.common_utils import execute_local_cmd


class CheckDebugLogPackageContainsSyslog(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-3869 - [ANALYTICS] Export debug log package should contains the syslog'
    TEST_JIRA_ID = 'KDP-3869'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.log_package_url = "http://{}:33284/cgi-bin/logs.sh".format(self.env.uut_ip)
        self.download_file = "/tmp/debug_logs.tar.gz"
        self.local_unzip_path = "/tmp/debug_log_folder"
        self.check_folder_list = [
            'debug',
            'system_info',
            'system_info/kdpappmgr',
            'var'
        ]

        self.check_file_list = [
            'system_info/current_status/df_output',
            'system_info/current_status/du_restsdk-data.log',
            'system_info/current_status/free_output',
            'system_info/current_status/ifconfig_output',
            'system_info/current_status/mdadm_output',
            'system_info/current_status/mount_output',
            'system_info/current_status/proc_partitions.txt',
            'system_info/current_status/proc_mdstat.txt',
            'system_info/current_status/process_list',
            'system_info/current_status/top_info.txt',
            'system_info/restsdk/activity_stats.log',
            'system_info/restsdk/debug_vars.log',
            'system_info/restsdk/device.log',
            'system_info/restsdk/goroutine.log',
            'system_info/current_status/netstat.txt',
            'system_info/kdpappmgr/docker-ps',
            'system_info/kdpappmgr/docker-images',
            'system_info/kdpappmgr/docker-stats'
        ]

    def test(self):
        self.log.info("*** Step 1: Download the debug log package")
        if os.path.exists(self.download_file):
            self.log.info("Delete existed debug log package")
            execute_local_cmd(cmd='rm {}'.format(self.download_file))
        execute_local_cmd(cmd='curl {} -o {}'.format(self.log_package_url, self.download_file))

        self.log.info("*** Step 2: Unzip the log package")
        if os.path.exists(self.local_unzip_path):
            self.log.info("Delete existed unzip debug log folder")
            execute_local_cmd(cmd='rm -rf {}'.format(self.local_unzip_path))
        execute_local_cmd(cmd='mkdir {}'.format(self.local_unzip_path))
        execute_local_cmd(cmd='tar -xvzf {} -C {}'.format(self.download_file, self.local_unzip_path))

        self.log.info("*** Step 3: Check if specific folders and files are exist")
        for folder in self.check_folder_list:
            self.log.info("Checking folder: {}".format(folder))
            if not os.path.exists("{}/{}".format(self.local_unzip_path, folder)):
                raise self.err.TestFailure('The expected folder: {} was not in the downloag package!'.format(folder))

        for file in self.check_file_list:
            self.log.info("Checking file: {}".format(file))
            if not os.path.exists("{}/{}".format(self.local_unzip_path, file)):
                raise self.err.TestFailure('The expected file: {} was not in the downloag package!'.format(file))

    def after_test(self):
        self.log.info("*** After Test Step 1: Remove the download package if it's exist")
        if os.path.exists(self.local_unzip_path):
            execute_local_cmd(cmd='rm -rf {}'.format(self.local_unzip_path))
        if os.path.exists(self.download_file):
            execute_local_cmd(cmd='rm {}'.format(self.download_file))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_log_package_contains_syslog.py --uut_ip 10.92.224.68\
        """)

    test = CheckDebugLogPackageContainsSyslog(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
