# -*- coding: utf-8 -*-
""" Case to check the default log url exist in the device properties
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP


class CheckDefaultUrlExistInProperties(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-2011 - Check the default config URL is saved in the device properties'
    TEST_JIRA_ID = 'KDP-2011'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        model_name = self.ssh_client.get_model_name()
        self.event_url = KDP.LOG_EVENT_URL.get("{}_{}".format(model_name, self.env.cloud_env))
        self.upload_url = KDP.LOG_UPLOAD_URL.get("{}_{}".format(model_name, self.env.cloud_env))
        if not self.event_url or not self.upload_url:
            raise self.err.TestSkipped(
                'Cannot find the value in constant, please check if the model name: {} and env: {} is correct!'.
                    format(model_name, self.env.cloud_env))

    def test(self):
        self.log.info("*** Step 1: Check if the default event url is in propertis and value is correct")
        stdout, stderr = self.ssh_client.execute_cmd('getprop | grep "\[wd.log.event.url\]"')
        if self.event_url not in stdout:
            raise self.err.TestFailure(
                'The default event url should be: {}, but it did not match the value in the properties: {}!'.
                    format(self.event_url, stdout))

        self.log.info("*** Step 2: Check if the default upload url is in propertis and value is correct")
        stdout, stderr = self.ssh_client.execute_cmd('getprop | grep "\[wd.log.upload.url\]"')
        if self.upload_url not in stdout:
            raise self.err.TestFailure(
                'The default upload url should be: {}, but it did not match the value in the properties: {}!'.
                    format(self.upload_url, stdout))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_default_url_exist_in_properties.py --uut_ip 10.92.224.68\
        """)

    test = CheckDefaultUrlExistInProperties(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
