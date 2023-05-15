# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys, time

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP
from platform_libraries.restAPI import RestAPI
#from kdp_scripts.bat_scripts.reboot import Reboot
from ibi_performance.tool.html import HtmlFormat
from godzilla_scripts.tools.csv import CsvFormat


class RebuildFTSKPI(KDPTestCase):

    TEST_SUITE = 'KDP KPI'
    TEST_NAME = 'KDP KPI Test case - Rebuild FTS KPI'
    # Popcorn
    TEST_JIRA_ID = 'KDP-2435'

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }

    def declare(self):
        self.test_result_list = []
        self.existed_data = False
        self.file_numbers = 10
        # Popcorn
        self.VERSION= 'InternalBeta'

    def init(self):
        self.root_folder = KDP.USER_ROOT_PATH
        self.restsdk_original_toml_path = '/usr/local/modules/restsdk/etc/restsdk-server.toml'
        self.restsdk_dev_toml_path = '/data/wd/diskVolume0/restsdk/restsdk-server-dev.toml'

    def before_loop(self):
        self.ssh_client.lock_otaclient_service_kdp()

        self.log.info("Step 1: Prepare the test dataset")
        if not self.existed_data:
            self.log.info("Creating {} fake files".format(self.file_numbers))
            self._create_dataset()
        else:
            self.log.info("Use the existed data in the user root folder")

    def before_test(self):
        """ Todo: Do we need to reboot before testing?
        self.log.info("Rebooting the device at the beginning of test iteration...")
        self.ssh_client.reboot_device()
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=60*20):
            raise self.err.TestError('Device was not shut down successfully!')
        if not self.ssh_client.wait_for_device_boot_completed(timeout=60*20):
            raise self.err.TestError('Device was not boot up successfully!')
        """
        pass

    def test(self):
        self.log.info("Step 2: Clone and modify the restsdk toml file, then restart restsdk service")
        self._clone_and_modify_restsdk_toml_file()
        self.ssh_client.restart_restsdk_service()

        self.log.info("Step 3: Wait and parser the rebuild FTS time")
        self._wait_and_parser_rebuild_fts_time()

        self.log.info("Step 4: Delete the restsdk dev1 toml file and restart the restsdk service")
        self.ssh_client.execute('rm {}'.format(self.restsdk_dev_toml_path))
        self.ssh_client.restart_restsdk_service()
        
        # Update test_result
        self.data.test_result['rebuildFTSTotalFiles'] = self.rebuild_fts_total_files
        self.data.test_result['rebuildFTSTime_avg'] = float(self.rebuild_fts_time)/1000000 # Transfer unit from microsecond to second
        self.data.test_result['rebuildFTSTime_unit'] = 'sec'
        self.data.test_result['count'] = 1
        self.data.test_result['executionTime'] = int(time.time() * 1000)  # millisecond

    def after_test(self):
        self.test_result_list.append(self.data.test_result)

    def after_loop(self):
        # The following is for html_table
        html_inst = HtmlFormat()
        if self.html_acronym_desc:
            html_inst.html_acronym_desc = self.html_acronym_desc
        html_inst.table_title_column = ['product', 'build', 'rebuildFTSTotalFiles', 'rebuildFTSTime_avg', 'rebuildFTSTime_unit']
        html_inst.table_title_column_extend = ['result']
        pass_status_summary = html_inst.html_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # The following is for csv file
        csv_inst = CsvFormat()
        csv_inst.csv_title_column = ['product', 'build', 'rebuildFTSTotalFiles', 'rebuildFTSTime_avg', 'rebuildFTSTime_unit', 'count', 'executionTime']
        csv_inst.csv_table(test_result_list=self.test_result_list, results_folder=self.env.results_folder)

        # Determine if the test is passed or not.
        if not pass_status_summary:
            raise self.err.TestFailure("At leaset one value doesn't meet the target/pass criteria.")

    def _create_dataset(self):
        user_id = self.uut_owner.get_user_id(escape=True)
        user_path = '{}/{}/rebuild_fts_dataset'.format(self.root_folder, user_id)
        if not self.ssh_client.check_folder_in_device(user_path):
            self.ssh_client.execute('mkdir {}'.format(user_path))
        for i in range(int(self.file_numbers)):
            self.ssh_client.create_dummyfiles(file_path="{}/{}.txt".format(user_path, i), file_size=10)

    def _wait_and_parser_rebuild_fts_time(self):
        retry = 0
        retry_delay = 60
        max_retries = 20
        while True:
            result = self.ssh_client.get_fts_rebuild_info()
            self.log.warning(result)
            if not result:
                if retry < max_retries:
                    self.log.info("Cannot find FTS rebuild info, retry after {0} seconds, {1} retries left...".
                                  format(retry_delay, (max_retries - retry)))
                    time.sleep(retry_delay)
                    retry += 1
                else:
                    raise self.err.StopTest(
                        'Cannot find FTS rebuild info after {} retries!'.format(max_retries))
            else:
                self.rebuild_fts_time = result.get('elapsedTime')  # The unit is microsecond
                self.rebuild_fts_total_files = result.get("totalFiles")
                self.log.warning("FTS rebuild time: {}".format(self.rebuild_fts_time))
                break

    def _clone_and_modify_restsdk_toml_file(self):
        self.ssh_client.execute('cp {0} {1}'.format(self.restsdk_original_toml_path, self.restsdk_dev_toml_path))
        self.ssh_client.execute('echo "[test]" >> {}'.format(self.restsdk_dev_toml_path))
        self.ssh_client.execute('echo "forceRebuildFTS = true" >> {}'.format(self.restsdk_dev_toml_path))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Rebuild FTS KPI test on KDP devices ***
        """)
    parser.add_argument('-ed', '--existed_data', help='The folder name of existed data set', action='store_true')
    parser.add_argument('-fn', '--file_numbers', help='How many files to create when no special data set', default=10)
    parser.add_argument('--html_acronym_desc', help='Description which is specified.', default='')

    test = RebuildFTSKPI(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
