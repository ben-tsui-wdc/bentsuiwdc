# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v2/system/clientLogs - 200
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import json
import os
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.test_utils import read_lines_to_string, run_test_with_data


class WriteSystemLog(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Write new log entry to system logs'
    # Popcorn
    TEST_JIRA_ID = 'KDP-4982'

    def test(self):
        run_test_with_data(
            test_data=read_lines_to_string(os.path.dirname(__file__) + '/../test_data/WriteSystemLog200.txt'),
            test_method=self.write_client_logs_test
        )

    def write_client_logs_test(self, payload_str):
        payload = json.loads(payload_str)
        level = payload['level']
        if 'error' in level: level = 'err'

        if payload.get('private'):
            self.ssh_client.clearAnalyticPrivateLog()
        else:
            self.ssh_client.clearAnalyticPublicLog()

        self.nasadmin._write_client_logs(payload_str)

        self.log.info("Checking system logs")
        if payload.get('private'):
            system_logs = self.ssh_client.getClientLogFromAnalyticPrivateLog()
        else:
            system_logs = self.ssh_client.getClientLogFromAnalyticPublicLog()

        for line in system_logs:
            if level in line: # match "level" first.
                msg_match = True
                for k, v in payload['message'].iteritems():
                    if isinstance(v, str):
                        match_value = '"{}"'.format(v)
                    elif isinstance(v, bool):
                        match_value = str(v).lower()
                    else:
                        match_value = v
                    if '"{}":'.format(k, match_value) not in line:
                        msg_match = False
                        break
                if msg_match:
                    return
        raise self.err.TestFailure('Not found log message: {} with level: {}'.format(
            payload['message'], payload['level']))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Write system log test ***
        """)

    test = WriteSystemLog(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
