# -*- coding: utf-8 -*-
""" Test cases to check restsdk service is loaded.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import re
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP


class LoadRestsdkmodule(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-214 - Rest-sdk Daemon Check'
    # Popcorn
    TEST_JIRA_ID = 'KDP-214'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        self.log.info("Checking RestSDK client")
        restsdk_daemon = self.ssh_client.get_restsdk_service()
        if not restsdk_daemon:
            raise self.err.TestFailure('Cannot find RestSDK service!')

        stdout, stderr = self.ssh_client.execute_cmd('ls -l {}/data/db/'.format(self.ssh_client.get_restsdk_dataDir()), quiet=False)
        regex = re.compile(r".+\..+")  # {name}.{extention}
        restsdk_db_files = filter(regex.match, stdout.split())
        check_list = ['index.db', 'index.db-shm', 'index.db-wal']
        if not all(file in restsdk_db_files for file in check_list):
            raise self.err.TestFailure('RestSDK db files are not matching!\nExpect files: {0}\nCurrent files: {1}'.
                                       format(check_list, restsdk_db_files))
        self.ssh_client.check_restsdk_service()

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Load REST-SDK Module Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/load_restsdk_module.py --uut_ip 10.92.224.68\
        """)

    test = LoadRestsdkmodule(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
