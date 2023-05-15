# -*- coding: utf-8 -*-

# std modules
import logging
import time
from argparse import ArgumentParser

# platform modules
from platform_libraries.restAPI import RestAPI
from platform_libraries.ssh_client import SSHClient


class USBIndexing(object):

    def __init__(self, parser):
        self.clean_indexing_logs = parser.clean_indexing_logs
        self.del_usb_fs = parser.del_usb_fs
        self.check_init_idle_status = parser.check_init_idle_status
        self.check_busy_status = parser.check_busy_status
        self.check_completed_init_status = parser.check_completed_init_status
        self.do_usb_indexing = parser.do_usb_indexing
        self.wait_indexing_complete = parser.wait_indexing_complete
        self.wait_indexing_timeout = parser.wait_indexing_timeout
        self.polling_status_timeout = parser.polling_status_timeout
        self.usb_share_name = parser.usb_share_name
        # init rest client.
        self.rest_client = None
        if self.del_usb_fs or self.do_usb_indexing or self.wait_indexing_complete:
            self.uut_ip = parser.uut_ip + ":8001"
            self.rest_client = RestAPI(
                uut_ip=self.uut_ip, env=parser.cloud_env, username=parser.username, password=parser.password, debug=True, 
                stream_log_level=logging.DEBUG, init_session=False)
            self.rest_client.update_device_id()
            self.rest_client.get_id_token()
        # init ssh client
        self.ssh_client = SSHClient(parser.uut_ip, parser.ssh_user, parser.ssh_password, parser.ssh_port)
        self.ssh_client.connect()

    def main(self):
        if self.del_usb_fs: self.delete_all_usb_fs()
        if self.clean_indexing_logs: 
            if self.del_usb_fs: time.sleep(5) # in case of RESTSDK is still prcoessing multimedia.
            self.clean_activity_status_logs()
        if self.check_init_idle_status: self.polling_for(func=self.check_init_idle_log)
        if self.check_busy_status: self.polling_for(func=self.check_busy_log)
        if self.check_completed_init_status: self.polling_for(func=self.check_completed_idle_log)
        if self.do_usb_indexing or self.wait_indexing_complete: self.check_usb_format()
        if self.do_usb_indexing: self.create_usb_fs()
        if self.wait_indexing_complete: self.wait_for_indexing_complete_by_call()

    def check_usb_format(self):
        usbs = self.ssh_client.get_usb_format()
        if not usbs: raise AssertionError("USB not found")
        usb_format = usbs.values()[0] # Expect one USB driver attached.
        self.ssh_client.log.info("USB format: {}".format(usb_format))

    def delete_all_usb_fs(self):
        for fs_id in self.get_all_usb_fs_id():
            self.rest_client.delete_filesystem(filesystem_id=fs_id)
        self.ssh_client.log.info("USB filesystem are deleted")

    def get_all_usb_fs_id(self):
        fs_ids = []
        for fs in self.rest_client.get_filesystem().get('filesystems', []):
            if fs.get('name', '').startswith('USB-') or (self.usb_share_name and self.usb_share_name == fs.get('name', '')):
                fs_ids.append(fs['id'])
        return fs_ids

    def create_usb_fs(self):
        usb_filesystem_name = 'USB-{}'.format(time.strftime("%Y%m%d-%H%M%S", time.gmtime()))
        self.ssh_client.log.info("USB filesystem name: {}".format(usb_filesystem_name))

        # Get vol id of USB
        usb_vol = self.rest_client.get_volumes_by(cmp_vl=lambda vl: vl.get('mountPoint', '').startswith('/mnt/USB/USB'))
        if not usb_vol:
            raise AssertionError("USB drive attached, but no USB volume found")
        usb_vol_id = usb_vol['volID']
        usb_mount_point = usb_vol['mountPoint']
        self.ssh_client.log.info("USB Vol id: {}".format(usb_vol_id))
        self.ssh_client.log.info("USB Vol mount point: {}".format(usb_mount_point))

        # Create filesystem with vol
        self.rest_client.create_filesystem(vol_id=usb_vol_id, name=usb_filesystem_name)
        self.ssh_client.log.info("Triggered USB indexing")

    def wait_for_indexing_complete_by_call(self, allow_no_files=False):
        # Expect there is only one USB attached on device.
        fs_ids = self.get_all_usb_fs_id()
        if not fs_ids: raise AssertionError("No USB filesystem found")
        filesystem_id = fs_ids[0]
        self.ssh_client.log.info('Wait for indexing complete by REST SDK call...')
        start_time = time.time()
        filesystem = None
        while time.time() - start_time < self.wait_indexing_timeout:
            filesystem = self.rest_client.get_filesystem(filesystem_id)
            if 'stats' in filesystem and filesystem['stats'].get('firstScanStatus') == 'complete' \
                    and (allow_no_files or ('firstScanTotalFilesCountExpected' in filesystem['stats'] and filesystem['stats']['firstScanTotalFilesCountExpected'] > 0)) \
                    and (filesystem['stats'].get('firstScanTotalFilesCountExpected', 0) - 1 <= filesystem['stats'].get('firstScanFilesCount', 0) \
                    or filesystem['stats'].get('firstScanFilesCount', 0) >= filesystem['stats'].get('firstScanTotalFilesCountExpected', 0) + 1):
                self.ssh_client.log.info('Indexing take {} s'.format(time.time() - start_time))
                return
            time.sleep(10)
        if filesystem: self.log.warning('Last filesystem info: {}'.format(filesystem))
        raise AssertionError('Wait indexing timeout')

    def check_init_idle_log(self):
        for status in self.get_activity_status_logs():
            if 'idle' in status:
                self.ssh_client.log.info("init status found")
                return True
        self.ssh_client.log.info("init status not found")
        return False

    def check_busy_log(self):
        for status in self.get_activity_status_logs():
            if 'busy' in status:
                self.ssh_client.log.info("busy status found")
                return True
        self.ssh_client.log.info("busy status not found")
        return False

    def check_completed_idle_log(self):
        busy_found = False
        for status in self.get_activity_status_logs():
            if 'busy' in status: busy_found = True
            if busy_found and 'idle' in status:
                self.ssh_client.log.info("completed idle status found")
                return True
        self.ssh_client.log.info("completed idle status not found")
        return False

    def polling_for(self, func):
        start_time = time.time()
        while time.time() - start_time < self.polling_status_timeout: 
            if func(): return
            time.sleep(30)
        raise AssertionError('Activity status not found')

    def get_activity_status_logs(self):
        output, _ = self.ssh_client.execute_cmd("grep -oE 'sdk status is \[idle\]|sdk status is \[busy\]' /var/log/analyticprivate.log")
        return output.split('\n')

    def clean_activity_status_logs(self):
        self.ssh_client.execute_cmd("echo > /var/log/analyticprivate.log")
        self.ssh_client.log.info("Empty /var/log/analyticprivate.log")


if __name__ == '__main__':
    parser = ArgumentParser("""\
        *** REST SDK index tools for Godzilla device ***
        """)
    parser.add_argument('-env', '--cloud_env', help='Cloud test environment', default='qa1', choices=['dev1', 'qa1', 'prod'])
    parser.add_argument('-ip', '--uut_ip', help='Destination UUT IP address', metavar='IP')
    parser.add_argument('-u', '--username', help='User account', metavar='NAME')
    parser.add_argument('-p', '--password', help='User password', metavar='PW')
    parser.add_argument('-ssh_user', '--ssh_user', help='The username of SSH server', default="sshd")
    parser.add_argument('-ssh_password', '--ssh_password', help='The password of SSH server', metavar='PWD', default="Test1234")
    parser.add_argument('-ssh_port', '--ssh_port', help='The port of SSH server', type=int, metavar='PORT', default=22)
    parser.add_argument('-duf', '--del_usb_fs', help='Delete existing USB filesystem', action='store_true', default=False)
    parser.add_argument('-cil', '--clean_indexing_logs', help='Clean analyticprivate.log', action='store_true', default=False)
    parser.add_argument('-ciis', '--check_init_idle_status', help='Check init idle status in RESTSDK log', action='store_true', default=False)
    parser.add_argument('-cbs', '--check_busy_status', help='Check busy status in RESTSDK log', action='store_true', default=False)
    parser.add_argument('-ccis', '--check_completed_init_status', help='Check completed idle status in RESTSDK log', action='store_true', default=False)
    parser.add_argument('-dui', '--do_usb_indexing', help='Perform USB indexing', action='store_true', default=False)
    parser.add_argument('-wic', '--wait_indexing_complete', help='Wait for USB indexing complete', action='store_true', default=False)
    parser.add_argument('-wit', '--wait_indexing_timeout', help='Timeout value for waiting USB indexing', type=int, default=600)
    parser.add_argument('-pst', '--polling_status_timeout', help='Timeout value for waiting RESTSDK status in log', type=int, default=320)
    parser.add_argument('-usn', '--usb_share_name', help='USB share name to delete', default=None)

    USBIndexing(parser.parse_args()).main()
