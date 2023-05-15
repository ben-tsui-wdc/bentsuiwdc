# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import sys, time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
#from kdp_scripts.bat_scripts.reboot import Reboot
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat


class AppInstallUninstall(KDPTestCase):

    TEST_SUITE = 'KDP KPI'
    TEST_NAME = 'KDP KPI Test case - Boot Time KPI'
    # Popcorn
    TEST_JIRA_ID = ''

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }


    def declare(self):
        self.test_result_list = []
        self.html_format = '2'
        # Popcorn
        self.VERSION= 'InternalBeta'


    def init(self):
        pass


    def before_loop(self):
        stdout, stderr = self.ssh_client.execute_cmd('ls /var/run/restsdk/userRoots')
        user_id = stdout.replace('auth0|', 'auth0\|')
        stdout, stderr = self.ssh_client.execute_cmd('curl "https://dev1-gza-ondevice-apps.s3-us-west-2.amazonaws.com/testKDPApps/nginx/nginx-arm64.docker" -o /var/run/restsdk/userRoots/{}/nginx-arm64.docker'.format(user_id))
        # Check file size of nginx-arm64.docker
        stdout, stderr = self.ssh_client.execute_cmd('ls -l /var/run/restsdk/userRoots/{}/nginx-arm64.docker'.format(user_id))
        if int(stdout.split()[4]) < 120073088:
            raise self.err.TestError("It's failed to download nginx-arm64.docker")
        stdout, stderr = self.ssh_client.execute_cmd('curl "https://dev1-gza-ondevice-apps.s3-us-west-2.amazonaws.com/testKDPApps/nginx/nginx.json" -o /var/run/restsdk/userRoots/{}/nginx.json'.format(user_id))
        # Check keyword in content of nginx.json 
        stdout, stderr = self.ssh_client.execute_cmd('cat /var/run/restsdk/userRoots/{}/nginx.json'.format(user_id))
        if '"appId": "com.nginx.test"' in stdout and '"companyName": "Nginx"' in stdout:
            pass
        else:
            raise self.err.TestError("It's failed to download nginx.json.")


    def before_test(self):
        pass


    def test(self):
        # Install app
        start_time = time.time()
        status_code = self.uut_owner.install_app_kdp(self.app_id, app_url=self.app_url, config_url=self.config_url , retry_times=None)
        # Check app installation status
        while time.time() - start_time < 300:
            try:
                apps_status = self.uut_owner.get_app_info_kdp(app_id=self.app_id)
                if apps_status.get('id') != self.app_id:
                    raise self.err.TestError("The app_id is {} rather than {}.".format(apps_status.get('id'), self.app_id))
                if apps_status.get('state') == 'installing':
                    time.sleep(1)
                elif apps_status.get('state') == 'installed':
                    break
                else:
                    raise self.err.StopTest("There is unexpected state occurred while installing app ({})".format(apps_status))
            except Exception as err:
                raise
        install_duration = time.time() - start_time
        if install_duration > 300:
            raise self.err.TestError("Installing app ({}) took {} seconds to complete!".format(self.app_id, install_duration))
        # Uninstall app
        start_time = time.time()
        status_code = self.uut_owner.uninstall_app(app_id=self.app_id)
        # Check app installation status
        while time.time() - start_time < 300:
            try:
                apps_status = self.uut_owner.get_installed_apps(app_id=self.app_id)
                if apps_status.get('id') != self.app_id:
                    raise self.err.TestError("The app_id is {} rather than {}.".format(apps_status.get('id'), self.app_id))
                if apps_status.get('state', None) == 'uninstalling':
                    time.sleep(0.5)
                else:
                    raise self.err.StopTest("There is unexpected state occurred while deleting app ({})".format(apps_status))
            except Exception as err:
                if "404 Client Error: Not Found" in str(err):
                    self.log.info(str(err))
                    break
                else:
                    raise
        uninstall_duration = time.time() - start_time
        if uninstall_duration > 300:
            raise self.err.TestError("Uninstalling app ({}) took {} seconds to complete!".format(self.app_id, uninstall_duration))
        # Update test_result
        self.data.test_result['InstallTime_avg'] = install_duration
        self.data.test_result['InstallTime_unit'] = 'sec'
        self.data.test_result['UninstallTime_avg'] = uninstall_duration
        self.data.test_result['UninstallTime_unit'] = 'sec'
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # millisecond


    def after_test(self):
        self.test_result_list.append(self.data.test_result)


    def after_loop(self):
        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        if self.html_format == '2':
            html_inst.table_title_column = ['product', 'build', 'InstallTime_avg', 'InstallTime_unit', 'UninstallTime_avg', 'UninstallTime_unit']
            html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)
        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'build', 'InstallTime_avg', 'InstallTime_unit', 'UninstallTime_avg', 'UninstallTime_unit', 'count', 'executionTime']
        csv_inst.csv_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)
        # Remove the files of nginx
        stdout, stderr = self.ssh_client.execute_cmd('ls /var/run/restsdk/userRoots')
        user_id = stdout.replace('auth0|', 'auth0\|')
        stdout, stderr = self.ssh_client.execute_cmd('rm -fr /var/run/restsdk/userRoots/{}/nginx-arm64.docker'.format(user_id))
        stdout, stderr = self.ssh_client.execute_cmd('rm -fr /var/run/restsdk/userRoots/{}/nginx.json'.format(user_id))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Desktop_Sync_BAT on Kamino Android ***
        Examples: ./run.sh kdp_scripts/performance_tests/app_install_uninstall.py --uut_ip 192.168.0.42:8001 --cloud_env dev1 --ssh_ip 192.168.0.42 --ssh_user sshd --ssh_password 123456 --debug  --loop_times 1  --dry_run  --stream_log_level INFO -dupr
        """)
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')
    parser.add_argument('--app_id', help='app id', default='nginx')
    parser.add_argument('--app_url', help='downloadURL', default='file://nginx-arm64.docker')
    parser.add_argument('--config_url', help='configURL', default='file://nginx.json')

    test = AppInstallUninstall(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
