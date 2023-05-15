# -*- coding: utf-8 -*-
""" Case to check the log package contains syslog
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import json
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckLogUploadFrequency(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-223 - Check Log upload frequency'
    TEST_JIRA_ID = 'KDP-223'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.log_config_file = "/etc/kxlog_config.json"
        self.check_log_file = "/var/log/analyticpublic.log"

    def test(self):
        self.log.info("*** Step 1: Load the config file and check the log upload frequency")
        stdout, stderr = self.ssh_client.execute_cmd('cat {}'.format(self.log_config_file))
        config_json = json.loads(stdout)
        config_list = config_json.get('works')
        log_upload_freq = None
        for config in config_list:
            if config.get('id') == 'FilterAndUploader':
                log_upload_freq = config.get('scheduler')
                break

        if not log_upload_freq or log_upload_freq != '~hour':
            raise self.err.TestFailure('The log upload frequency config: {} is incorrect!'.format(log_upload_freq))

        self.log.info("*** Step 2: Restart the logpp and check the logs to see the config really works")
        self.ssh_client.restart_logpp(debug_mode=True)
        stdout, stderr = self.ssh_client.execute_cmd(
            'grep -r \'"msgid":"LogPP","scheduler":"~hour","message":"work config"\' {}'.format(self.check_log_file))
        if not stdout:
            raise self.err.TestFailure('Cannot find the log frequency information in {}!'.format(self.check_log_file))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_log_upload_frequency.py --uut_ip 10.92.224.68\
        """)

    test = CheckLogUploadFrequency(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
