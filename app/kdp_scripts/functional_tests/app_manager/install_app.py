# -*- coding: utf-8 -*-
""" Test case to install app from ECR
    https://jira.wdmv.wdc.com/browse/KDP-203
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
# 3rd party
import requests


class InstallApp(KDPTestCase):

    TEST_SUITE = 'KDP_APP_Manager_Test'
    TEST_NAME = 'KDP-203 - Install App'
    TEST_JIRA_ID = 'KDP-203,KDP-2013,KDP-2066'

    def declare(self):
        self.uninstall_app = False
        self.app_id = None
        self.add_install_multiple_app_ticket = False
        self.install_again_during_installation = False
        self.check_app_install = False
        self.check_proxy_to_app = False
        self.check_internal_port_to_app = False
        self.check_mount_points = False
        self.check_container_env = False
        self.install_again_after_installed = False

    def init(self):
        if self.add_install_multiple_app_ticket:  # only append ticket ID, remember to run it for other app test.
            self.TEST_JIRA_ID = '{},KDP-2326'.format(self.TEST_JIRA_ID)
        if self.install_again_during_installation:
            self.TEST_JIRA_ID = '{},KDP-2504'.format(self.TEST_JIRA_ID)
        if self.check_proxy_to_app:
            self.TEST_JIRA_ID = '{},KDP-2004'.format(self.TEST_JIRA_ID)
        if self.check_internal_port_to_app:
            self.TEST_JIRA_ID = '{},KDP-2317'.format(self.TEST_JIRA_ID)
        if self.check_mount_points:
            self.TEST_JIRA_ID = '{},KDP-2061'.format(self.TEST_JIRA_ID)
        if self.check_container_env:
            self.TEST_JIRA_ID = '{},KDP-4305'.format(self.TEST_JIRA_ID)
        if self.install_again_after_installed:
            self.TEST_JIRA_ID = '{},KDP-2510'.format(self.TEST_JIRA_ID)

    def before_test(self):
        if not self.check_app_install:
            return
        if self.uut_owner.get_app_state_kdp(self.app_id) == 'installed':
            self.uut_owner.uninstall_app(self.app_id)
            if not self.uut_owner.wait_for_app_uninstall_completed(self.app_id):
                raise self.err.TestFailure('APP({}) is failed to uninstall'.format(self.app_id))
        self.container_id = None
        self.docker_inspect_info_dict = None

    def test(self):
        self.uut_owner.install_app_kdp(self.app_id)

        if self.install_again_during_installation:
            try:
                self.log.info('Making a call to install App({}) again during installation'.format(self.app_id))
                self.uut_owner.install_app_kdp(self.app_id)
                raise AssertionError('Success make a call to install App({}) again during installation'.format(self.app_id))
            except Exception as e:
                if '409' in str(e):
                    self.log.info('Got 409 status as expected')
                    self.log.info('*** Install APP again during installation test is PASSED')
                else:
                    raise AssertionError('Got an unexpected error {}'.format(e))

        if not self.uut_owner.wait_for_app_install_completed(self.app_id):
            raise self.err.TestFailure('APP({}) is not install successfully, test Failed !!!'.format(self.app_id))
        self.log.info('*** App({}) has been installed. Test PASSED !!!'.format(self.app_id))

        if self.check_proxy_to_app:  # KDP-2004
            if 'com.plexapp.mediaserver.smb' not in self.app_id:
                self.log.warning('Test app is not Plex')
                return
            self.log.info('Wait for more 10 secs to make sure Plex is ready...')
            time.sleep(10)
            self.log.info('Making call to verify the proxy to Plex APP')
            self.log.info(
                'GET http://{}:{}/sdk/v1/apps/com.plexapp.mediaserver.smb/proxy/myplex/pinRedirect?access_token='.
                    format(self.uut_owner.uut_ip, self.uut_owner.port, self.uut_owner.access_token))
            resp = requests.get(
                url='http://{}:{}/sdk/v1/apps/com.plexapp.mediaserver.smb/proxy/myplex/pinRedirect'.format(
                    self.uut_owner.uut_ip, self.uut_owner.port),
                params={'access_token': self.uut_owner.access_token}
            )
            self.log.info('Call status: {}'.format(resp.status_code))
            self.log.debug('Call response content: {}'.format(resp.content))
            assert 'plex' in resp.content, 'Response content seems not the page to Plex APP'
            self.log.info('*** Proxy to APP test is PASSED')

        if self.check_internal_port_to_app:  # KDP-2317
            if 'com.wdc.filebrowser' not in self.app_id:
                self.log.warning('Test app is not filebrowser')
                return
            self.log.info('Wait for more 10 secs to make sure filebrowser is ready...')
            time.sleep(10)
            self.log.info('Getting app port')
            resp = self.uut_owner.get_app_info_kdp(app_id='com.wdc.filebrowser')
            port = resp['port']
            self.log.info('Making call to verify the internal port to filebrowser APP')
            self.log.info(
                'GET http://{}:{}/sdk/v1/apps/com.wdc.filebrowser/proxy/filebrowser'.
                    format(self.uut_owner.uut_ip, port))
            resp = requests.get(
                url='http://{}:{}/sdk/v1/apps/com.wdc.filebrowser/proxy/filebrowser'.format(
                    self.uut_owner.uut_ip, port)
            )
            self.log.info('Call status: {}'.format(resp.status_code))
            self.log.debug('Call response content: {}'.format(resp.content))
            assert 'FileBrowser' in resp.content, 'Response content seems not the page to filebrowser APP'
            self.log.info('*** Access internal port of APP test is PASSED')

        if self.check_mount_points:  # KDP-2061
            self.log.info('Checking mount points...')
            for mp in self.get_docker_inspect_info_dict()['Mounts']:
                target, source = mp['Target'] if 'Target' in mp else mp['Destination'], mp['Source']
                if not source.startswith('/data'):
                    self.log.info('Not verify mount point: {} -> {}'.format(target, source))
                    continue
                self.log.info('Verifying mount point: {} -> {}'.format(target, source))
                try:
                    self.log.info('Touching a file in container')
                    exitcode, output = self.ssh_client.execute(
                        "docker exec {} touch '{}/test'".format(self.container_id, target))
                    assert exitcode == 0, 'Failed to touch {}/test'.format(target)

                    self.log.info('Verifying the file in device')
                    exitcode, output = self.ssh_client.execute("ls '{}/test'".format(source))
                    assert exitcode == 0, 'Failed to find {}/test, seem the mount point is not working'.\
                        format(source)
                finally:
                    self.log.info('Deleting a file in container')
                    exitcode, output = self.ssh_client.execute(
                        "docker exec {} rm '{}/test'".format(self.container_id, target))
                    assert exitcode == 0, 'Failed to delete {}/test'.format(target)

                    self.log.info('Verifying the file in device')
                    exitcode, output = self.ssh_client.execute("ls '{}/test'".format(source))
                    assert exitcode != 0, 'Failed to delete {}/test, seem the mount point is not working'.format(
                        source)
            self.log.info('*** Mount point check test is PASSED')

        if self.check_container_env:  # KDP-4305
            product = self.uut.get('model')
            if 'monarch' in product:
                model_name = "WD_MODEL_NAME=My Cloud Home"
            elif 'pelican' in product:
                model_name = "WD_MODEL_NAME=My Cloud Home Duo"
            elif 'yodaplus' in product:
                model_name = "WD_MODEL_NAME=ibi"
            else:
                assert AssertionError('Unknown device')

            self.log.info('Checking env...')
            info_dict = self.get_docker_inspect_info_dict()
            assert 'Config' in info_dict, 'No "Config" field in inspect info'
            assert 'Env' in info_dict['Config'], 'No "Env" field in inspect info'
            for line in info_dict['Config']['Env']:
                if model_name in line:
                    break
            else:
                assert AssertionError('Not found: "{}" in inspect info'.format(model_name))
            self.log.info('*** Env check test is PASSED')

        if self.install_again_after_installed:  # KDP-2510
            self.log.info('Making a call to install App({}) again after installation'.format(self.app_id))
            self.uut_owner.install_app_kdp(self.app_id)
            self.log.info('*** Install APP again test is PASSED')

    def get_container_id(self):
        if not self.container_id:
            self.container_id = self.ssh_client.get_container_id(self.app_id)
        return self.container_id

    def get_docker_inspect_info_dict(self):
        if not self.docker_inspect_info_dict:
            container_id = self.get_container_id()
            assert container_id, 'Not found a container for App({})'.format(self.app_id)
            self.docker_inspect_info_dict = self.ssh_client.docker_inspect(container_id)
        return self.docker_inspect_info_dict

    def after_test(self):
        if self.uninstall_app:
            self.log.info('Start to Uninstall App({}) ...'.format(self.app_id))
            self.uut_owner.uninstall_app(self.app_id)
            if not self.uut_owner.wait_for_app_uninstall_completed(self.app_id):
                self.log.error('Failed to uninstall app ...')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Install App Test Script ***
        Examples: ./run.sh kdp_scripts/functional_tests/app_manager/install_app.py --uut_ip 10.92.224.68 --uninstall_app\
        """)

    parser.add_argument('-appid', '--app_id', help='App ID to installed')
    parser.add_argument('-aimat', '--add_install_multiple_app_ticket', help='Add install multiple app ticket',
                        action='store_true')
    parser.add_argument('-iadi', '--install_again_during_installation',
                        help='Verify call response for installing APP again during installation', action='store_true')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test',
                        action='store_true')
    parser.add_argument('-uninstall_app', '--uninstall_app', help='Uninstall installed app after test',
                        action='store_true')
    parser.add_argument('-cpta', '--check_proxy_to_app', help='For Plex only. Verify the proxy to APP page',
                        action='store_true')
    parser.add_argument('-cipta', '--check_internal_port_to_app', help='For filebrowser only. Verify the port of APP page',
                        action='store_true')
    parser.add_argument('-cmp', '--check_mount_points', help='Verify mount points of APP', action='store_true')
    parser.add_argument('-cce', '--check_container_env', help='Verify env field of APP', action='store_true')
    parser.add_argument('-iaai', '--install_again_after_installed',
                        help='Verify call response for APP installed', action='store_true')

    test = InstallApp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
