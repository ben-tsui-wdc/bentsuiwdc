# -*- coding: utf-8 -*-
""" Test case to check the restsdk module
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import re
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class LoadRestsdkModule(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Load RestSDK Module Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1076'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        self.log.info("Checking OTA client")
        restsdk_daemon = self.ssh_client.get_restsdk_service()
        if not restsdk_daemon:
            raise self.err.TestFailure('Cannot find RestSDK service!')

        stdout, stderr = self.ssh_client.execute_cmd('ls -l /mnt/HD/HD_a2/restsdk-data/data/db/', quiet=False)
        regex = re.compile(r".+\..+")  # {name}.{extention}
        restsdk_db_files = filter(regex.match, stdout.split())
        check_list = ['index.db', 'index.db-shm', 'index.db-wal']
        if not all(file in restsdk_db_files for file in check_list):
            raise self.err.TestFailure('RestSDK db files are not matching!\nExpect files: {0}\nCurrent files: {1}'.
                                       format(check_list, restsdk_db_files))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Load RestSDK Module Check test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/load_restsdk_module.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = LoadRestsdkModule(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
