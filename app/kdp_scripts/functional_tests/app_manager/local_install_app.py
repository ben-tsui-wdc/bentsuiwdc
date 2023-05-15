# -*- coding: utf-8 -*-
""" Test case to local install APP.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import os
import sys
# platform modules
import time

from middleware.arguments import KDPInputArgumentParser
from install_app import InstallApp
from platform_libraries.shell_cmds import ShellCommands
# 3rd party
import requests


class LocalInstallApp(InstallApp):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-2060 - Install App locally'
    TEST_JIRA_ID = 'KDP-2060'

    def declare(self):
        super(LocalInstallApp, self).declare()
        self.app_id = 'nginx'
        self.uninstall_app = True
        self.file_server_ip = '10.200.141.26'
        self.app_json_url_path = '/KDP/app_mgr/local_install/nginx.json'
        self.app_image_url_path = '/KDP/app_mgr/local_install/nginx-arm64.docker'

    def init(self):
        super(LocalInstallApp, self).init()
        self.app_json_url = 'http://{}{}'.format(self.file_server_ip, self.app_json_url_path)
        self.app_image_url = 'http://{}{}'.format(self.file_server_ip, self.app_image_url_path)

    def before_test(self):
        super(LocalInstallApp, self).before_test()
        self.json_name = self.app_json_url_path.rsplit('/', 1).pop()
        self.image_name = self.app_image_url_path.rsplit('/', 1).pop()
        self.log.info('Downloading test files...')
        if not os.path.exists(self.json_name):
            ShellCommands().executeCommand(cmd="wget {} .".format(self.app_json_url))
        if not os.path.exists(self.image_name):
            ShellCommands().executeCommand(cmd="wget {} .".format(self.app_image_url))
        self.uut_owner.clean_user_root()

    def test(self):
        self.log.info('Uploading test file to the device')
        self.uut_owner.upload_file(file_name=self.json_name, file_object=open(self.json_name))
        self.uut_owner.upload_file(file_name=self.image_name, file_object=open(self.image_name))

        self.log.info('Making call to install APP locally')
        self.log.info(
            'PUT http://{}:{}/sdk/v1/apps/nginx?downloadURL=file://nginx-arm64.docker&configURL=file://nginx.json'.
                format(self.uut_owner.uut_ip, self.uut_owner.port))
        resp = requests.put(
            url='http://{}:{}/sdk/v1/apps/nginx?downloadURL=file://nginx-arm64.docker&configURL=file://nginx.json'.
                format(self.uut_owner.uut_ip, self.uut_owner.port),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer {}'.format(self.uut_owner.get_id_token())
            }
        )
        self.log.info('Call status: {}'.format(resp.status_code))
        self.log.debug('Call response content: {}'.format(resp.content))
        assert resp.status_code == 204, 'Bad response status code: {}'.format(resp.status_code)

        if not self.uut_owner.wait_for_app_install_completed(self.app_id, ignore_error=True):
            raise self.err.TestFailure('APP({}) is not install successfully, test Failed !!!'.format(self.app_id))
        self.log.info('*** App({}) has been installed. Test PASSED !!!'.format(self.app_id))

    def after_test(self):
        try:
            super(LocalInstallApp, self).after_test()
        except Exception as e:
            self.log.info(e)  # got 404 after remove this APP
        self.uut_owner.clean_user_root()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Install App locally ***
        """)
    parser.add_argument('-fsi', '--file_server_ip', help='File server IP', default='10.200.141.26')
    parser.add_argument('-ajup', '--app_json_url_path', help='URL path to Json file of test APP',
                        default='/KDP/app_mgr/local_install/nginx.json')
    parser.add_argument('-aiup', '--app_image_url_path', help='URL path to APP image of test APP',
                        default='/KDP/app_mgr/local_install/nginx-arm64.docker')

    test = LocalInstallApp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
