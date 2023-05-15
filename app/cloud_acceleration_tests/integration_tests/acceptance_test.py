# -*- coding: utf-8 -*-
""" Cloud Acceleration acceptance test.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
# platform modules
from platform_libraries.test_result import ResultList
from middleware.arguments import IntegrationTestArgument
from middleware.integration_test import IntegrationTest
# Sub-tests
from cloud_acceleration_tests.functional_tests.create_share import CreateShareTest
from cloud_acceleration_tests.subtests.access_deleted_file import AccessDeletedFileTest
from cloud_acceleration_tests.subtests.access_modified_file import AccessModifiedFileTest
from cloud_acceleration_tests.subtests.access_moved_file import AccessMovedFileTest
from cloud_acceleration_tests.subtests.delete_cache import DeleteCacheTest
from cloud_acceleration_tests.subtests.file_perm_allow import FilePermAllowTest
from cloud_acceleration_tests.subtests.file_perm_not_allow import FilePermNotAllowTest
from cloud_acceleration_tests.subtests.multiple_1st_access import MultipleFisrtAccessTest
from cloud_acceleration_tests.subtests.multiple_2nd_access import MultipleSecondAccessTest
from cloud_acceleration_tests.subtests.multiple_access_deleted_file import MultipleAccessDeletedFileTest
from cloud_acceleration_tests.subtests.multiple_access_modified_file import MultipleAccessModifiedFileTest
from cloud_acceleration_tests.subtests.multiple_access_moved_file import MultipleAccessMovedFileTest
from cloud_acceleration_tests.subtests.multiple_file_perm_allow import MultipleFilePermAllowTest
from cloud_acceleration_tests.subtests.multiple_file_perm_not_allow import MultipleFilePermNotAllowTest
from cloud_acceleration_tests.subtests.ns_access_with_incorrect_device_id import AccessCacheWithIncorrectDeviceIDTest
from cloud_acceleration_tests.subtests.ns_access_with_incorrect_file_id import AccessCacheWithIncorrectFileIDTest
from cloud_acceleration_tests.subtests.ns_access_with_incorrect_token import AccessCacheWithIncorrectTokenTest
from cloud_acceleration_tests.subtests.ns_access_without_token import AccessCacheWithoutTokenTest
from cloud_acceleration_tests.subtests.single_1st_access import SingleFisrtAccessTest
from cloud_acceleration_tests.subtests.single_2nd_access import SingleSecondAccessTest
from cloud_acceleration_tests.subtests.single_offline_access import SingleOfflineAccessTest


class RESTSDK_BAT(IntegrationTest):

    TEST_SUITE = 'Cloud Acceleration'
    TEST_NAME = 'Cloud_Acceleration'

    def declare(self):
        # 55KB photo
        self.photo_url = 'http://fileserver.hgst.com/test/Images50GB/JPG/EXIF_images/hari_1219.jpg'
        self.display_photo_size = None
        self.do_test_auth_by_param = False
        self.do_test_auth_by_header = True

    def init(self):
        if not self.display_photo_size: self.display_photo_size = ''
        self.name_of_share_photo = 'Share {} Photo & Get Cache Information'.format(self.display_photo_size)

        if self.do_test_auth_by_header:
            self.integration.add_testcases(testcases=[
                # Single Access
                (CreateShareTest, {
                    'file_url': self.photo_url,
                    'check_mime_type': 'image/jpeg', 'TEST_NAME': self.name_of_share_photo
                }),
                #(SingleOfflineAccessTest, {'TEST_NAME': 'Single Access - Auth Header: 1st Offline Access'}),
                (SingleFisrtAccessTest, {'TEST_NAME': 'Single Access - Auth Header: 1st Access'}),
                #(SingleOfflineAccessTest, {'TEST_NAME': 'Single Access - Auth Header: 2nd Offline Access'}),
                (SingleSecondAccessTest, {'TEST_NAME': 'Single Access - Auth Header: 2nd Access'}),
                (AccessCacheWithIncorrectDeviceIDTest, {'TEST_NAME': 'Single Access - Auth Header: Access With Incorrect Device ID'}),
                (AccessCacheWithIncorrectFileIDTest, {'TEST_NAME': 'Single Access - Auth Header: Access With Incorrect File ID'}),
                (AccessCacheWithIncorrectTokenTest, {'TEST_NAME': 'Single Access - Auth Header: Access With Incorrect Token'}),
                (AccessCacheWithoutTokenTest, {'TEST_NAME': 'Single Access - Auth Header: Access Without Token'}),
                (DeleteCacheTest, {'TEST_NAME': 'Auth Header: Delete Cache'}),
                (SingleFisrtAccessTest, {'TEST_NAME': 'Single Access - Auth Header: 1st Access After Delete Cache'}),
                (SingleSecondAccessTest, {'TEST_NAME': 'Single Access - Auth Header: 2nd Access After Delete Cache'}),
                (FilePermNotAllowTest, {'TEST_NAME': 'Single Access - Auth Header: FilePerm: Allow To NotAllow'}),
                (FilePermAllowTest, {'TEST_NAME': 'Single Access - Auth Header: FilePerm: NotAllow To Allow'}),
                (AccessModifiedFileTest, {'TEST_NAME': 'Single Access - Auth Header: Access Modified File'}),
                (AccessMovedFileTest, {'TEST_NAME': 'Single Access - Auth Header: Access Moved File'}),
                (AccessDeletedFileTest, {'TEST_NAME': 'Single Access - Auth Header: Access Deleted File'}),

                # Multiple Access
                (CreateShareTest, {
                    'file_url': self.photo_url,
                    'check_mime_type': 'image/jpeg', 'TEST_NAME': self.name_of_share_photo
                }),
                (MultipleFisrtAccessTest, {'TEST_NAME': 'Multiple Access - Auth Header: 1st Access'}),
                (MultipleSecondAccessTest, {'TEST_NAME': 'Multiple Access - Auth Header: 2nd Access'}),
                (DeleteCacheTest, {'TEST_NAME': 'Auth Header: Delete Cache'}),
                (MultipleFisrtAccessTest, {'TEST_NAME': 'Multiple Access - Auth Header: 1st Access After Delete Cache'}),
                (MultipleSecondAccessTest, {'TEST_NAME': 'Multiple Access - Auth Header: 2nd Access After Delete Cache'}),
                (MultipleFilePermNotAllowTest, {'TEST_NAME': 'Multiple Access - Auth Header: FilePerm: Allow To NotAllow'}),
                (MultipleFilePermAllowTest, {'TEST_NAME': 'Multiple Access - Auth Header: FilePerm: NotAllow To Allow'}),
                (MultipleAccessModifiedFileTest, {'TEST_NAME': 'Multiple Access - Auth Header: Access Modified File'}),
                (MultipleAccessMovedFileTest, {'TEST_NAME': 'Multiple Access - Auth Header: Access Moved File'}),
                (MultipleAccessDeletedFileTest, {'TEST_NAME': 'Multiple Access - Auth Header: Access Deleted File'}),
            ])

        if self.do_test_auth_by_param:
            self.integration.add_testcases(testcases=[
                # Single Access by auth param
                (CreateShareTest, {
                    'file_url': self.photo_url, 'auth_by_header': False,
                    'check_mime_type': 'image/jpeg', 'TEST_NAME': self.name_of_share_photo
                }),
                #(SingleOfflineAccessTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: 1st Offline Access'}),
                (SingleFisrtAccessTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: 1st Access'}),
                #(SingleOfflineAccessTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: 2nd Offline Access'}),
                (SingleSecondAccessTest, {'auth_by_header': False, 'TEST_NAME': 'Single Access - Auth Param: 2nd Access'}),
                (AccessCacheWithIncorrectDeviceIDTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: Access With Incorrect Device ID'}),
                (AccessCacheWithIncorrectFileIDTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: Access With Incorrect File ID'}),
                (DeleteCacheTest, {'auth_by_header': False,'TEST_NAME': 'Auth Param: Delete Cache'}),
                (SingleFisrtAccessTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: 1st Access After Delete Cache'}),
                (SingleSecondAccessTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: 2nd Access After Delete Cache'}),
                (FilePermNotAllowTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: FilePerm: Allow To NotAllow'}),
                (FilePermAllowTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: FilePerm: NotAllow To Allow'}),
                (AccessModifiedFileTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: Access Modified File'}),
                (AccessMovedFileTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: Access Moved File'}),
                (AccessDeletedFileTest, {'auth_by_header': False,'TEST_NAME': 'Single Access - Auth Param: Access Deleted File'}),

                # Multiple Access by auth param
                (CreateShareTest, {
                    'file_url': self.photo_url, 'auth_by_header': False,
                    'check_mime_type': 'image/jpeg', 'TEST_NAME': self.name_of_share_photo
                }),
                (MultipleFisrtAccessTest, {'auth_by_header': False,'TEST_NAME': 'Multiple Access - Auth Param: 1st Access'}),
                (MultipleSecondAccessTest, {'auth_by_header': False,'TEST_NAME': 'Multiple Access - Auth Param: 2nd Access'}),
                (DeleteCacheTest, {'auth_by_header': False,'TEST_NAME': 'Auth Param: Delete Cache'}),
                (MultipleFisrtAccessTest, {'auth_by_header': False,'TEST_NAME': 'Multiple Access - Auth Param: 1st Access After Delete Cache'}),
                (MultipleSecondAccessTest, {'auth_by_header': False,'TEST_NAME': 'Multiple Access - Auth Param: 2nd Access After Delete Cache'}),
                (MultipleFilePermNotAllowTest, {'auth_by_header': False,'TEST_NAME': 'Multiple Access - Auth Param: FilePerm: Allow To NotAllow'}),
                (MultipleFilePermAllowTest, {'auth_by_header': False,'TEST_NAME': 'Multiple Access - Auth Param: FilePerm: NotAllow To Allow'}),
                (MultipleAccessModifiedFileTest, {'auth_by_header': False,'TEST_NAME': 'Multiple Access - Auth Param: Access Modified File'}),
                (MultipleAccessMovedFileTest, {'auth_by_header': False,'TEST_NAME': 'Multiple Access - Auth Param: Access Moved File'}),
                (MultipleAccessDeletedFileTest, {'auth_by_header': False,'TEST_NAME': 'Multiple Access - Auth Param: Access Deleted File'}),
            ])


    def after_test(self):
        """ Post handle test result. """
        self.data.test_result = self.post_handle_dumplicate_case(
            result_list=self.data.test_result, test_name=self.name_of_share_photo)
        self.data.test_result = self.post_handle_dumplicate_case(
            result_list=self.data.test_result, test_name='Auth Header: Delete Cache')
        self.data.test_result = self.post_handle_dumplicate_case(
            result_list=self.data.test_result, test_name='Auth Param: Delete Cache')
        self.log.info('{} results export to xml report.'.format(len(self.data.test_result)))

    def post_handle_dumplicate_case(self, result_list, test_name):
        # Collect dumplicate case.
        dumplicates = []
        for idx, sub_test_result in enumerate(result_list):
            if sub_test_result['testName'] == test_name:
                dumplicates.append((idx, sub_test_result))
        
        if 2 > len(dumplicates):
            return result_list

        first_row_idx = dumplicates[0][0] # The idx of first dumplicate row.
        # Keep first row on the given result_list and check all dumplicate cases are pass.
        for idx, sub_test_result in dumplicates:
            # TODO: Add more error type if we need it.
            if {k for k in ['error_message', 'failure_message'] if k in sub_test_result}:
                # The error type of first failed case.
                error_type = 'error_message' if 'error_message' in sub_test_result else 'failure_message'
                # Update the error message to first row
                result_list[first_row_idx][error_type] = sub_test_result[error_type]
                break

        # The other sub_test_result are removed from result_list.
        new_list = ResultList()
        for idx, sub_test_result in enumerate(result_list):
            if idx != first_row_idx and sub_test_result['testName'] == test_name:
                self.log.info('Remove the test result of "{}"" from xml report.'.format(test_name))
                continue
            new_list.append(sub_test_result)
        return new_list


if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** RESTSDK_BAT on Kamino Android ***
        Examples: ./run.sh cloud_acceleration_tests/integration_tests/restsdk_bat --uut_ip 10.136.137.159\
        """)
    parser.add_argument('--photo_url', help='URL of test photo to download from photo server', metavar='http://fileserver.hgst.com/test/Images50GB/JPG/EXIF_images/hari_1219.jpg')
    parser.add_argument('--display_photo_size', help='Display size of photo size', metavar='')
    parser.add_argument('--do_test_auth_by_header', help='Run auth_by_header tests', action='store_true')
    parser.add_argument('--do_test_auth_by_param', help='Run auth_by_param tests', action='store_true')

    test = RESTSDK_BAT(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
