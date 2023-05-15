# -*- coding: utf-8 -*-
""" 
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.kamino_standalone_test import KaminoStandaloneTest


class UserLogin(KaminoStandaloneTest):

    TEST_SUITE = 'Kamino Standalone Tests'
    TEST_NAME = 'User Login'

    def test(self):
    	self.environment.update_service_urls(client_settings={}, env_version)
        self.uut_owner.get_id_token()


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** DELTET_DATA test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/delete_data.py --uut_ip 10.136.137.159\
        """)

    test = UserLogin(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
