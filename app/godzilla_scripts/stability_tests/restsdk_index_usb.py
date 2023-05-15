# -*- coding: utf-8 -*-

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class RestSDKIndexUSB(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Stability'
    TEST_NAME = 'RESTSDK indexing for USB'
    # Popcorn
    TEST_JIRA_ID = 'GZA-7102'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'Stability'

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }


    def declare(self):
        self.target_total_indexed_file = 1098
        self.target_total_indexed_folder = 23
        self.usb_format = 'fat32'
        self.data_source_url = 'http://10.200.141.26/GZA/usb_indexing/1000f%2B5d%2B2psd/'
        self.force = False
        self.not_format_usb = False
        self.max_waiting_time = 60*10

    def init(self):
        # Delete all existing testing USB filesystem.
        for fs in self.uut_owner.get_filesystem().get('filesystems', []):
            if fs.get('name', '').startswith('USB-'): self.uut_owner.delete_filesystem(filesystem_id=fs['id'])
        # Check attached USB drive.
        usbs = self.ssh_client.get_usb_format()
        if not usbs: raise self.err.StopTest("USB not found")
        usb_format = usbs.values()[0] # Expect one USB driver attached.
        self.log.info("USB format: {}".format(usb_format))
        # Check USB format.
        if usb_format != self.usb_format or self.force:
            if self.not_format_usb:
                raise self.err.StopTest("USB format is {}".format(usb_format))
            # Format USB and push data set.
            self.ssh_client.format_usb(self.usb_format)
        # check data set
        usb_path = self.ssh_client.get_usb_path()
        if not usb_path.strip():
            raise self.err.StopTest("Cannot detect USB")
        total, _ = self.ssh_client.execute_cmd("find {} -type f | wc -l".format(usb_path))
        if not total or int(total) < self.target_total_indexed_file:
            if self.data_source_url:
                self.ssh_client.execute_cmd('rm -r {}/*'.format(usb_path))
                self.ssh_client.push_data_set_to_usb(source_url=self.data_source_url, total_files=self.target_total_indexed_file)
            else:
                raise self.err.StopTest("USB data is not ready")
        # Push testing binary.
        self.ssh_client.push_sqlite3_utils()

    def before_test(self):
        # init vars
        self.usb_filesystem_id = None
        self.index_items_in_call = None
        self.index_info_in_log = None

        # Delete all existing testing USB filesystem.
        for fs in self.uut_owner.get_filesystem().get('filesystems', []):
            if fs.get('name', '').startswith('USB-'): self.uut_owner.delete_filesystem(filesystem_id=fs['id'])

        # Record restsdk pid
        self.restsdk_pid_before = self.ssh_client.get_restsdk_pid()
        self.log.info("REST SDK pid: {}".format(self.restsdk_pid_before))
        if not self.restsdk_pid_before:
            raise self.err.StopTest("REST SDK is not running")

        # sqlite db part. Ensure the number of sqlite db doesn't change anymore
        self.index_items_in_sqlite_before = self.ssh_client.wait_for_sqlite_no_change()
        self.log.info("Indexed items: {}".format(self.index_items_in_sqlite_before))

        # Create usb share name with time
        self.usb_filesystem_name = 'USB-{}'.format(time.strftime("%Y%m%d-%H%M%S", time.gmtime()))
        self.log.info("USB filesystem name: {}".format(self.usb_filesystem_name))

        # Get vol id of USB
        usb_vol = self.uut_owner.get_volumes_by(cmp_vl=lambda vl: vl.get('mountPoint', '').startswith('/mnt/USB/USB'))
        if not usb_vol:
            raise self.err.StopTest("USB drive attached, but no USB volume found")
        self.usb_vol_id = usb_vol['volID']
        self.usb_mount_point = usb_vol['mountPoint']
        self.log.info("USB Vol id: {}".format(self.usb_vol_id))
        self.log.info("USB Vol mount point: {}".format(self.usb_mount_point))

    def test(self):
        # Record start time
        start_machine_time = self.ssh_client.get_local_machine_time_in_log_format()
        self.log.info("Start machine time: {}".format(start_machine_time))

        # Create filesystem with vol
        self.usb_filesystem_id = self.uut_owner.create_filesystem(vol_id=self.usb_vol_id, name=self.usb_filesystem_name)
        self.log.info("USB filesystem id: {}".format(self.usb_filesystem_id))

        # TODO: detach and attach USB stick.

        # Wait for indexing complete.
        self.index_items_in_call = self.wait_for_indexing_complete_by_call(self.usb_filesystem_id, self.max_waiting_time) # files + folders
        self.log.info("Indexed files in REST call: {}".format(self.index_items_in_call))
        self.index_info_in_log = self.wait_for_indexing_complete_by_logs(self.usb_mount_point, start_machine_time) # files + folder
        if self.index_info_in_log: self.log.info("Indexed files in log: {}".format(self.index_info_in_log['totalIndexedFiles']))

        self.verify_result()

    def verify_result(self):
        self.log.info("target_total_indexed_file: {}".format(self.target_total_indexed_file))
        self.log.info("target_total_indexed_folder: {}".format(self.target_total_indexed_folder))
        self.log.info("index_items_in_call: {}".format(self.index_items_in_call))
        self.log.info("index_items_in_log: {}".format(self.index_info_in_log['totalIndexedFiles'] if self.index_info_in_log else 'Not Found'))
        target_total_indexed_number = self.target_total_indexed_file + self.target_total_indexed_folder 
        if target_total_indexed_number not in xrange(self.index_items_in_call-1, self.index_items_in_call+2): # for number correct issue.
            raise self.err.TestFailure('Index files in RESK Call is not correct')
        if self.index_info_in_log: 
            if target_total_indexed_number not in xrange(self.index_info_in_log['totalIndexedFiles']-1, self.index_info_in_log['totalIndexedFiles']+2):
               raise self.err.TestFailure('Index files in log is not correct')

    def wait_for_indexing_complete_by_call(self, filesystem_id, max_waiting_time=60*10, allow_no_files=False):
        self.log.info('Wait for indexing complete by REST SDK call...')
        start_time = time.time()
        filesystem = None
        while time.time() - start_time < max_waiting_time:
            filesystem = self.uut_owner.get_filesystem(filesystem_id)
            if 'stats' in filesystem and filesystem['stats'].get('firstScanStatus') == 'complete' \
                    and (allow_no_files or ('firstScanTotalFilesCountExpected' in filesystem['stats'] and filesystem['stats']['firstScanTotalFilesCountExpected'] > 0)) \
                    and (filesystem['stats'].get('firstScanTotalFilesCountExpected', 0) - 1 <= filesystem['stats'].get('firstScanFilesCount', 0) \
                    or filesystem['stats'].get('firstScanFilesCount', 0) >= filesystem['stats'].get('firstScanTotalFilesCountExpected', 0) + 1): # for number correct issue.
                self.log.info('Indexing take {} s'.format(time.time() - start_time))
                return filesystem['stats']['firstScanFilesCount']
            time.sleep(10)
        if filesystem: self.log.warning('Last filesystem info: {}'.format(filesystem))
        self.ssh_client.execute_cmd('echo "CPU usage"; echo "  PID  PPID USER     STAT   VSZ %VSZ CPU %CPU COMMAND"; top -n 1 | grep -i restsdk | grep -v restsdk-serverd')
        raise self.err.StopTest('Indexing is still not complete after {} secs'.format(max_waiting_time))

    def wait_for_indexing_complete_by_logs(self, path, index_start_machine_time=None):
        self.log.info('Wait for indexing complete log appear...')
        for i in xrange(3):
            index_log = self.ssh_client.get_indexing_log(path, index_start_machine_time)
            if index_log:
                self.log.info("Log found: {}".format(index_log))
                return self.ssh_client.fetch_indexing_log(index_log)
            time.sleep(5)
        self.log.error('No index log found!')

    def check_restsdk_pid(self):
        restsdk_pid = self.ssh_client.get_restsdk_pid()
        self.log.info("final restsdk_pid: {}".format(restsdk_pid))
        if self.restsdk_pid_before != restsdk_pid:
            return False
        return True

    def after_test(self):
        self.log.info('Monitor memory usage:')
        self.ssh_client.execute_cmd("free")
        self.ssh_client.execute_cmd("ps | grep restsdk-server | grep -v grep | grep -v restsdk-serverd")
        # check REST SDK
        self.log.info('Check REST SDK PID pass: {}'.format(self.check_restsdk_pid()))
        '''
        # Delete testing filesystem.
        if self.usb_filesystem_id:
            self.uut_owner.delete_filesystem(filesystem_id=self.usb_filesystem_id)
        '''


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** REST SDK index test for Godzilla device ***
        """)
    parser.add_argument('-tf', '--target_total_indexed_file', help='target of number of indexed file', type=int, default=1098)
    parser.add_argument('-td', '--target_total_indexed_folder', help='target of number of indexed file', type=int, default=23)
    parser.add_argument('-uf', '--usb_format', help='USB format in test', default='fat32', choices=['fat32', 'hfs+', 'ntfs', 'exfat'])
    parser.add_argument('-url', '--data_source_url', help='URL of data set', default='http://10.200.141.26/GZA/usb_indexing/usb_indexing_test_v1/')
    parser.add_argument('-f', '--force', help='Force to format USB', action='store_true', default=False)
    parser.add_argument('-nfu', '--not_format_usb', help='Stop test when USB format is not correct', action='store_true', default=False)
    parser.add_argument('-mwt', '--max_waiting_time', help='Max waiting time for indexing', type=int, default=60*10)

    resp = RestSDKIndexUSB(parser.parse_args()).main()
    if resp:
        sys.exit(0)
    sys.exit(1)
