# -*- coding: utf-8 -*-
""" Case to confirm that logs will upload to Splunk server when pip is ON
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class LogWillUploadWhenPipIsOn(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-229 - Logs upload when PIP is enabled'
    TEST_JIRA_ID = 'KDP-229'

    SETTINGS = {
        'uut_owner': True
    }

    def init(self):
        self.analyticpublic_path = '/var/log/analyticpublic.log'
        self.uploaded_folder_path = '/data/kxlog/uploaded'

    def test(self):
        self.log.info("*** Step 1: Enable the PIP status")
        self.uut_owner.enable_pip()

        self.log.info("*** Step 2: Generate a dummy log, run log rotate and upload")
        self.ssh_client.generate_logs(log_number=5, log_type="INFO", log_messages="dummy_test_pip_on")
        self.ssh_client.log_rotate_kdp(force=True)
        self.ssh_client.log_upload_kdp()

        self.log.info("*** Step 3: Check the PIP status is True in the log")
        stdout, stderr = self.ssh_client.execute_cmd('cat {} | grep pip'.format(self.analyticpublic_path))
        if '"pip":"true"' not in stdout:
            raise self.err.TestFailure('The PIP status should be true but it was false!')

        self.log.info("*** Step 4: Check if logs cannot be found in uploaded folder (if folder exist)")
        if self.ssh_client.check_folder_in_device(self.uploaded_folder_path):
            stdout, stderr = self.ssh_client.execute_cmd('grep -r "dummy_test_pip_on" {}'
                                                         .format(self.uploaded_folder_path))
            if not stdout:
                raise self.err.TestFailure('When PIP is enabled, the logs should be found in uploaded folder!')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/log_will_upload_when_pip_is_on.py --uut_ip 10.92.224.68\
        """)

    test = LogWillUploadWhenPipIsOn(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
