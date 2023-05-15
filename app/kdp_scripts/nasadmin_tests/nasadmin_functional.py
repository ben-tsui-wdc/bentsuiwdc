# -*- coding: utf-8 -*-
""" KDP nasAdmin functional tests.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPIntegrationTestArgument
from middleware.kdp_integration_test import KDPIntegrationTest
from kdp_scripts.test_utils.kdp_test_utils import reset_device
from kdp_scripts.test_utils.test_case_utils import nsa_add_argument_2nd_user
# Sub-tests
from auth.get_public_key import GetPublicKey
from auth.invalidate_token_test import InvalidateTokenTest
from auth.post_auth import PostAuth
from auth.post_auth_400 import PostAuth400
from auth.post_auth_401 import PostAuth401
from auth.post_auth_409 import PostAuth409
from auth.post_auth_415 import PostAuth415
from auth.put_auth import PutAuth
from auth.put_auth_400 import PutAuth400
from auth.put_auth_401 import PutAuth401
from auth.put_auth_415 import PutAuth415
from device.get_device import GetDeviceInfo
from device.get_device_fresh_device import GetDeviceInfoFreshDevice
from others.erase_settings_test import EraseSettingsTest
from system.system_reset import SystemReset
from system.system_reset_400 import SystemReset400
from system.system_reset_401 import SystemReset401
from system.system_reset_415 import SystemReset415
from system.write_system_log import WriteSystemLog
from system.write_system_log_400 import WriteSystemLog400
from system.write_system_log_401 import WriteSystemLog401
from system.write_system_log_415 import WriteSystemLog415
from users.get_2nd_user import Get2ndUser
from users.get_user import GetUser
from users.get_user_400 import GetUser400
from users.get_user_401 import GetUser401
from users.get_user_403 import GetUser403
from users.patch_2nd_user import Patch2ndUser
from users.patch_2nd_user_400 import Patch2ndUser400
from users.patch_user import PatchUser
from users.patch_user_400 import PatchUser400
from users.patch_user_401 import PatchUser401
from users.patch_user_403 import PatchUser403
from users.patch_user_409 import PatchUser409
from users.patch_user_415 import PatchUser415
from users.run_when_restsdk_unreachable import RunWhenRestsdkUnreachable
from users.share_access_full_device_test import ShareAccessFullDeviceTest
from users.share_link_lose_check_test import ShareLinkLoseTest
from users.wsdd_status_test import WSDDStatusTest
from validation.get_validation import GetValidation
from validation.get_validation_401 import GetValidation401


class NasAdminFunctionalTests(KDPIntegrationTest):

    TEST_SUITE = 'nasAdmin functional test'
    TEST_NAME = 'nasAdmin functional test'
    REPORT_NAME = 'functional'

    def init(self):
        if self.single_run:
            self.integration.add_testcases(testcases=[eval(self.single_run)])
        else:
            if not self.env.is_nasadmin_supported():
                raise self.err.TestFailure('nasAdmin is not supported')

            # auth endpoints
            self.integration.add_testcases(testcases=[
                GetPublicKey, (InvalidateTokenTest, self.get_args_for_2nd_user()), PostAuth, PutAuth
            ])
            if not self.disable_negative_test:
                self.integration.add_testcases(testcases=[
                    PostAuth400, PostAuth401, PostAuth409, PostAuth415,
                    PutAuth400, PutAuth401, PutAuth415
                ])

            # users endpoints
            self.integration.add_testcases(testcases=[
                GetUser, (Get2ndUser, self.get_args_for_2nd_user()),
                PatchUser, (Patch2ndUser, self.get_args_for_2nd_user()),
                # ShareAccessFullDeviceTest,  # need to resolve mount error during the test.
                RunWhenRestsdkUnreachable,
                (ShareLinkLoseTest, self.get_args_for_2nd_user()), WSDDStatusTest,
            ])
            if not self.disable_negative_test:
                self.integration.add_testcases(testcases=[
                    GetUser400, GetUser401, (GetUser403, self.get_args_for_2nd_user()),
                    PatchUser400, PatchUser401, PatchUser403, PatchUser409, PatchUser415,
                    Patch2ndUser400
                ])

            # device endpoints
            self.integration.add_testcases(testcases=[
                GetDeviceInfo, GetDeviceInfoFreshDevice  # may move it to head of test for saving time
            ])

            # system endpoints
            self.integration.add_testcases(testcases=[
                SystemReset, WriteSystemLog
            ])
            if not self.disable_negative_test:
                self.integration.add_testcases(testcases=[
                    SystemReset400, SystemReset401, SystemReset415,
                    WriteSystemLog400, WriteSystemLog401, WriteSystemLog415
                ])

            # validation endpoints
            self.integration.add_testcases(testcases=[
                GetValidation
            ])
            if not self.disable_negative_test:
                self.integration.add_testcases(testcases=[
                    GetValidation401
            ])

            # others
            self.integration.add_testcases(testcases=[
                EraseSettingsTest
            ])

    def after_test(self):
        if not self.disable_reset_device: reset_device(self)

    def get_args_for_2nd_user(self):
        return {
            'username_2nd': self.username_2nd,
            'password_2nd': self.password_2nd,
            'detach_2nd_user': self.detach_2nd_user
        }


if __name__ == '__main__':
    parser = KDPIntegrationTestArgument("""\
        *** nasAdmin functional tests ***
        """)
    # Test Arguments
    nsa_add_argument_2nd_user(parser)
    parser.add_argument('--single_run', help='Run single case')
    parser.add_argument('-dnt', '--disable_negative_test', help='Not run negative test',
                        action='store_true', default=False)
    parser.add_argument('-drd', '--disable_reset_device', help='Not reset device after test done',
                        action='store_true', default=False)

    test = NasAdminFunctionalTests(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
