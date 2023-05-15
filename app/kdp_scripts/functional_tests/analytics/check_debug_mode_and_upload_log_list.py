# -*- coding: utf-8 -*-
""" Case to confirm the app log path /var/log/apps will reserve 10 MB space
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import urllib2
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.bat_scripts.reboot import Reboot

class CheckDebugModeAndUploadLogList(KDPTestCase):

    TEST_SUITE = 'KDP_Functional_Analytics'
    TEST_NAME = 'KDP-1111 - [ANALYTICS] Check the upload log list when user debug mode is on or off'
    TEST_JIRA_ID = 'KDP-1111'

    SETTINGS = {
        'uut_owner': True
    }

    def init(self):
        # Todo: atop_upload.log need to find a way to generate log
        self.default_debug_mode = {
            'dev1': ['1'],
            'qa1': ['0', ''],
            'prod': ['0', '']
        }
        self.debug_mode_off_logs = {
            'analyticpublic.log',
            'otaclient.log',
            'wdpublic.log',
            'kern_upload.log',
            # 'atop_upload.log',
            'appMgr.log',
            'nasAdmin.log'
        }
        self.debug_mode_on_logs = {
            'analyticpublic.log',
            'analyticprivate.log',
            'otaclient.log',
            'wdlog.log',
            'kern_upload.log',
            # 'atop_upload.log',
            'appMgr.log'
        }
        self.uploaded_log_path = '/data/kxlog/debug'
        self.debug_mode_property = 'persist.wd.log.debug'

    def test(self):
        self.log.info('*** Step 1: Check if default debug mode property is correct')
        default_debug_mode = self.default_debug_mode.get(self.env.cloud_env)
        debug_mode = self.get_debug_mode()
        if debug_mode not in default_debug_mode:
            raise self.err.TestFailure('Expect the default property {} is {} but it is {}!'.
                                       format(self.debug_mode_property, default_debug_mode, debug_mode))

        self.log.info('*** Step 2: Create dummy logs and upload them, check if specific log list is uploaded')
        if default_debug_mode[0] == '1':
            upload_log_list = self.debug_mode_on_logs
        else:
            upload_log_list = self.debug_mode_off_logs
        self.create_dummy_log_and_check_log_upload(upload_log_list)

        self.log.info('*** Step 3: Change the debug mode property')
        if default_debug_mode[0] == '1':
            new_debug_mode = '0'
            upload_log_list = self.debug_mode_off_logs
        else:
            new_debug_mode = '1'
            upload_log_list = self.debug_mode_on_logs
        self.change_debug_mode(new_debug_mode)

        self.log.info('*** Step 4: Create dummy logs and upload them, check if specific log list is uploaded')
        self.create_dummy_log_and_check_log_upload(upload_log_list)

    def after_test(self):
        self.log.info("Restore the debug mode value to default")
        default_debug_mode = self.default_debug_mode.get(self.env.cloud_env)[0]
        self.change_debug_mode(default_debug_mode)

    def get_debug_mode(self):
        return_code, output = self.ssh_client.execute('getprop {}'.format(self.debug_mode_property))
        if return_code not in (0, 1):
            raise self.err.TestFailure('Failed to setup the property! Return code: {}'.format(return_code))
        return output

    def change_debug_mode(self, debug_mode_status):
        return_code, output = self.ssh_client.execute('setprop {} {}'.format(self.debug_mode_property,
                                                                             debug_mode_status))
        if return_code not in (0, 1):
            raise self.err.TestFailure('Failed to setup the property! Return code: {}'.format(return_code))
        self.log.info('The property {} is set to {}, reboot the device to let the settings work'.
                      format(self.debug_mode_property, debug_mode_status))
        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=False']
        reboot = Reboot(env_dict)
        reboot.no_rest_api = True
        reboot.main()

    def check_logs_are_uploaded(self, upload_log_list):
        for file in upload_log_list:
            if not self.ssh_client.check_file_in_device('{}/*-{}.1'.format(self.uploaded_log_path, file)):
                raise self.err.TestFailure('The log: {} was not uploaded as expected!'.format(file))

    def create_dummy_log_and_check_log_upload(self, upload_log_list):
        for file in upload_log_list:
            self.ssh_client.execute_cmd('dd if=/dev/zero of=/var/log/{} bs=1K count=500 status=none'.format(file))
        # kern.log will be filtered and saved to kern_upload.log so we need to generate real logs
        self.ssh_client.execute('echo "2023-01-11T01:11:11.111111+00:00 di=8KbvnE99Lk info kernel: '
                                '[ 22.087535] [KML] md: md1 stopped." >> /var/log/kern.log')
        self.ssh_client.execute('find {} -maxdepth 1 -type f -delete'.format(self.uploaded_log_path))
        self.ssh_client.log_rotate_kdp(force=True)
        self.ssh_client.log_upload_kdp(reason="Test")
        self.check_logs_are_uploaded(upload_log_list)
        self.log.info('Logs in the list are uploaded as expected.')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Unauthenticalted ports check script ***
        Examples: ./run.sh kdp_scripts/functional_tests/analytics/check_app_log_reserve_space.py --uut_ip 10.92.224.68\
        """)

    test = CheckDebugModeAndUploadLogList(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
