# -*- coding: utf-8 -*-
""" Godzilla integration test for Platform BAT
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
from datetime import datetime, timedelta
# platform modules
from middleware.arguments import GodzillaIntegrationTestArgument
from middleware.godzilla_integration_test import GodzillaIntegrationTest
# Sub-tests
from platform_libraries.constants import Godzilla as GZA
from godzilla_scripts.bat_scripts.samba_rw_check import SambaRW
from godzilla_scripts.functional_tests.check_share_default_list import CheckShareDefaultList
from godzilla_scripts.functional_tests.add_public_share_and_check_samba_rw import AddPublicShareAndCheckSambaRW
from godzilla_scripts.functional_tests.add_private_share_and_check_samba_rw import AddPrivateShareAndCheckSambaRW
from godzilla_scripts.functional_tests.add_two_users_with_private_share_and_check_samba_rw import AddTwoUsersWithPrivateShareAndCheckSambaRW
from godzilla_scripts.functional_tests.delete_share import DeleteShare
from godzilla_scripts.functional_tests.check_share_ftp_disabled import CheckShareFTPDisabled
from godzilla_scripts.functional_tests.check_share_ftp_enabled import CheckShareFTPEnabled
from godzilla_scripts.functional_tests.check_share_nfs_disabled import CheckShareNFSDisabled
from godzilla_scripts.functional_tests.check_share_nfs_enabled import CheckShareNFSEnabled
from godzilla_scripts.functional_tests.check_share_user_access import CheckShareUserAccess
from godzilla_scripts.functional_tests.tls_redirect_url_check import TLSRedirectURLCheck
from godzilla_scripts.functional_tests.nasAdmin_disable_enable_tls_redirect import NasAdminDisableEnableTLSRedirect
from godzilla_scripts.functional_tests.nasAdmin_disable_enable_wan_filter import NasAdminDisableEnableWANFilter
from godzilla_scripts.functional_tests.nasAdmin_disable_enable_hw_transcoding import NasAdminDisableEnableHWTranscoding


class PLATFORM_SANITY(GodzillaIntegrationTest):

    TEST_SUITE = 'GODZILLA PLATFORM Sanity'
    TEST_NAME = 'GODZILLA PLATFORM Sanity'
    # Popcorn
    PROJECT = 'godzilla'
    TEST_TYPE = 'functional'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'SANITY'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):

        if self.single_run:
            for test_case in self.single_run:
                self.integration.add_testcases(testcases=[eval(test_case)])
        else:
            if self.env.model:
                self.model = self.env.model
            else:
                self.model = self.ssh_client.get_model_name()

            if self.model in ['PR2100', 'PR4100']:
                self.integration.add_testcases(testcases=[
                    NasAdminDisableEnableHWTranscoding
                ])

            self.integration.add_testcases(testcases=[
                NasAdminDisableEnableTLSRedirect,
                NasAdminDisableEnableWANFilter,
                CheckShareDefaultList,
                (SambaRW, {'TEST_NAME': 'Copy Files To The Public Folder', 'TEST_JIRA_ID': 'GZA-1048'}),
                AddPublicShareAndCheckSambaRW,
                AddPrivateShareAndCheckSambaRW,
                AddTwoUsersWithPrivateShareAndCheckSambaRW,
                DeleteShare,
                CheckShareFTPDisabled,
                CheckShareFTPEnabled,
                CheckShareNFSDisabled,
                CheckShareNFSEnabled,
                (CheckShareUserAccess, {'TEST_NAME': 'Check Share User Access - Read Only', 'user_permission': '1',
                                        'TEST_JIRA_ID': 'GZA-1141'}),
                (CheckShareUserAccess, {'TEST_NAME': 'Check Share User Access - Read Write', 'user_permission': '2',
                                        'TEST_JIRA_ID': 'GZA-1041'}),
                (CheckShareUserAccess, {'TEST_NAME': 'Check Share User Access - Deny', 'user_permission': '3',
                                        'TEST_JIRA_ID': 'GZA-1175'})
            ])
            
            """ Skip TLS redirect due to the TLS URL limitation and it's not stable to get the value
            (TLSRedirectURLCheck, {'TEST_NAME': 'TLS - Verify redirect URL after device firmware update',
                                   'pre_step': 'fw_update', 'TEST_JIRA_ID': 'GZA-8113'}),
            (TLSRedirectURLCheck, {'TEST_NAME': 'TLS - Verify redirect URL after device reboot',
                                   'pre_step': 'reboot', 'TEST_JIRA_ID': 'GZA-8112'}),
            """

            """ Blocked by GZA-8066: 429 too many requests
            (TLSRedirectURLCheck, {'TEST_NAME': 'TLS - Verify redirect URL after device id is changed',
                                   'pre_step': 'factory_reset', 'TEST_JIRA_ID': 'GZA-8114'}),
            """


if __name__ == '__main__':
    parser = GodzillaIntegrationTestArgument("""\
        *** PLATFORM SANITY Test on Kamino Android ***
        Examples: ./run.sh godzilla_scripts/integration_tests/platform_sanity.py --uut_ip 10.136.137.159\
        """)

    # Test Arguments
    parser.add_argument('--single_run', nargs='+', help='Run single case for Platform Sanity Test')
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    test = PLATFORM_SANITY(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
