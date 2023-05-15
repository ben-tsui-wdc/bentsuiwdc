# -*- coding: utf-8 -*-
""" Case to check only the logs include both blacklist and whitelist keywords will not upload
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP


class LogIncludeBothBlacklistAndWhitelistKeywordsWillNotUpload(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-1646 [ANALYTICS] Logs include keywords in both blacklist and whitelist will not be uploaded'
    TEST_JIRA_ID = 'KDP-1646'

    SETTINGS = {
        'uut_owner': True
    }

    def init(self):
        self.ramdisk_policy_file = '/etc/kxlog_policy.txt'
        self.black_list_keyword = 'black_list_test'
        self.white_list_keyword = 'white_list_test'
        self.log_file = '/var/log/analyticpublic.log'
        self.log_number = 5
        self.uploaded_log_path = '/data/kxlog/uploaded'
        self.model = self.uut.get('model')

    def before_test(self):
        self.log.info('*** Before test step 1: clean up the uploaded logs')
        if self.ssh_client.check_folder_in_device(self.uploaded_log_path):
            if not self.ssh_client.check_folder_is_empty(self.uploaded_log_path):
                return_code, output = self.ssh_client.execute('rm {}/*'.format(self.uploaded_log_path))
                if return_code != 0:
                    raise self.err.TestFailure('Failed to delete existed log files in upload folder! Return code: {}'.
                                               format(return_code))
                else:
                    self.log.info("Files in {} have been deleted".format(self.uploaded_log_path))

    def test(self):
        self.log.info("*** Step 1: Add the keyword to both black list and white list")
        return_code, output = self.ssh_client.execute("sed -i '/^common: blocklist.*/a {0}' {1}".
                                                      format(self.black_list_keyword, self.ramdisk_policy_file))
        if return_code != 0:
            raise self.err.TestFailure('Failed to add keyword in the black list! Return code: {}'.format(return_code))

        return_code, output = self.ssh_client.execute("sed -i '/^common: allowlist.*/a {0}' {1}".
                                                      format(self.white_list_keyword, self.ramdisk_policy_file))
        if return_code != 0:
            raise self.err.TestFailure('Failed to add keyword in the white list! Return code: {}'.format(return_code))

        self.log.info("*** Step 2: Restart the logpp to let new policy file work")
        self.ssh_client.restart_logpp(debug_mode=True)

        self.log.info("*** Step 3: Generate logs with black/white list keywords and upload logs")
        self.ssh_client.generate_logs(log_number=self.log_number, log_messages="{}_{}".
                                      format(self.black_list_keyword, self.white_list_keyword))
        self.ssh_client.log_rotate_kdp(force=True)
        self.ssh_client.log_upload_kdp(reason="Test")
        if self.model in ['monarch2', 'yodaplus2']:
            # Device will check every minute to see if HDD is awake and move logs from ramdisk to HDD
            # force to move it to save time
            self.log.info("Force to move the logs from ramdisk to HDD")
            self.ssh_client.execute_background('logutil.sh --move /etc/log_move.conf')
            time.sleep(5)

        self.log.info("*** Step 4: Check if the keywork exist in the uploaded logs")
        return_code, output = self.ssh_client.execute('grep -r "{0}_{1}" {2}'.
                                                      format(self.black_list_keyword, self.white_list_keyword,
                                                             self.uploaded_log_path))
        if return_code != 1:
            raise self.err.TestFailure('The black list keyword should not be found in uploaded folder! '
                                       'Test failed! Output: {}'.format(output))
        
    def after_test(self):
        self.log.info("*** After test step 1: Clean up the black list keyword in the policy file")
        return_code, output = self.ssh_client.execute("sed -i '/^{0}/d' {1}".
                                                      format(self.black_list_keyword, self.ramdisk_policy_file))
        if return_code != 0:
            raise self.err.TestFailure('Failed to clean up the black list keyword in the policy file! '
                                       'Return code: {}'.format(return_code))

        self.log.info("*** After test step 2: Clean up the white list keyword in the policy file")
        return_code, output = self.ssh_client.execute("sed -i '/^{0}/d' {1}".
                                                      format(self.white_list_keyword, self.ramdisk_policy_file))
        if return_code != 0:
            raise self.err.TestFailure('Failed to clean up the white list keyword in the policy file! '
                                       'Return code: {}'.format(return_code))

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/log_include_both_blacklist_and_whitelist_keywords_will_not_upload.py --uut_ip 10.92.224.68\
        """)

    test = LogIncludeBothBlacklistAndWhitelistKeywordsWillNotUpload(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
