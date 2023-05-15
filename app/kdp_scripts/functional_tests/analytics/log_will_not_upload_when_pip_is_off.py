# -*- coding: utf-8 -*-
""" Case to confirm that logs will not upload to Splunk server when pip is OFF
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class LogWillNotUploadWhenPipIsOff(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-224 - Logs don\'t uploaded when PIP is disabled'
    TEST_JIRA_ID = 'KDP-224'

    SETTINGS = {
        'uut_owner': True
    }

    def init(self):
        self.analyticpublic_path = '/var/log/analyticpublic.log'
        self.uploaded_folder_path = '/data/kxlog/uploaded'

    def test(self):
        self.log.info("*** Step 1: Disable the PIP status")
        self.uut_owner.disable_pip()

        self.log.info("*** Step 2: Generate a dummy log, run log rotate and upload")
        self.ssh_client.generate_logs(log_number=5, log_type="INFO", log_messages="dummy_test_pip_off")
        self.ssh_client.log_rotate_kdp(force=True)
        self.ssh_client.log_upload_kdp()

        self.log.info("*** Step 3: Check the PIP status is False in the log")
        stdout, stderr = self.ssh_client.execute_cmd('cat {} | grep pip'.format(self.analyticpublic_path))
        if '"pip":"false"' not in stdout:
            raise self.err.TestFailure('The PIP status should be false but it was true!')

        self.log.info("*** Step 4: Check if logs cannot be found in uploaded folder (if folder exist)")
        if self.ssh_client.check_folder_in_device(self.uploaded_folder_path):
            stdout, stderr = self.ssh_client.execute_cmd('grep -r "dummy_test_pip_off" {}'
                                                         .format(self.uploaded_folder_path))
            if stdout:
                raise self.err.TestFailure('When PIP is disabled, the logs should not be found in uploaded folder!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/log_will_not_upload_when_pip_is_off.py --uut_ip 10.92.224.68\
        """)

    test = LogWillNotUploadWhenPipIsOff(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
