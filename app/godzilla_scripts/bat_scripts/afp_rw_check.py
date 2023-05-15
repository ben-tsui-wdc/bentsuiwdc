# -*- coding: utf-8 -*-
""" Test cases to check AFP Read/Write test.
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import os
import time

# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.inventoryAPI import InventoryAPI, InventoryException
from platform_libraries.ssh_client import SSHClient
from platform_libraries.common_utils import delete_local_file


class AFPRW(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Basic AFP Read Write Test'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1193'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.inventory_server_ip = '10.6.160.250'
        self.mac_server_ip = ''
        self.mac_os = ''
        self.mac_username = 'fitlab'
        self.mac_password = "fituser"
        self.afp_user = 'admin'
        self.afp_password = 'adminadmin'
        self.timeout = 60*10
        self.share_folder = "Public"

    def init(self):
        self.timestamp = int(time.time())  # Add timestamp to avoid running on the same MAC client
        self.share_location = '{0}/{1}'.format(self.env.ssh_ip, self.share_folder)
        self.mountpoint = '/Volumes/afp_{0}_{1}'.format(self.timestamp, self.env.uut_ip.split('.')[-1])
        self.count = 1
        self.filename = 'test{0}MB_{1}_{2}'.format(self.count, self.timestamp, self.env.uut_ip.split('.')[-1])
        self.inventory = InventoryAPI('http://{}:8010/InventoryServer'.format(self.inventory_server_ip), debug=True)
        self.device_in_inventory = None

    def before_test(self):
        if not self.mac_server_ip:
            self.log.info("Checkout a MAC OS client from Iventory Server")
            self.device_in_inventory = self._checkout_device(uut_platform='mac-client', firmware=self.mac_os)
            if self.device_in_inventory:
                self.mac_server_ip = self.device_in_inventory.get('internalIPAddress')
            else:
                raise self.err.TestSkipped('There is no spare mac client can be checked out from Inventory Server.')
        else:
            self.log.info("Use specified MAC OS client to test, IP address: {}".format(self.mac_server_ip))

        self.mac_ssh = SSHClient(self.mac_server_ip, self.mac_username, self.mac_password)
        self.mac_ssh.connect()

    def test(self):
        self.mac_ssh.execute_cmd('sudo mkdir {}'.format(self.mountpoint))

        self.log.info("Step 1: Mount test folder via AFP protocol in MAC OS client")
        self.mac_ssh.execute_cmd('sudo mount -t afp afp://{0}:{1}@{2} {3}'.format(self.afp_user, self.afp_password,
                                                                                  self.share_location, self.mountpoint),
                                 timeout=60*3)
        self.log.info("Step 2: Create a dummy test file: {}".format(self.filename))
        self.mac_ssh.execute_cmd('dd if=/dev/urandom of={0} bs=1m count={1}'.format(self.filename, self.count))

        self.log.info("Step 3: Start the Write test")
        self.mac_ssh.execute_cmd('sudo cp {0} {1}'.format(self.filename, self.mountpoint), timeout=self.timeout)
        if not self.ssh_client.check_file_in_device('/shares/Public/{}'.format(self.filename)):
            raise self.err.TestFailure('Upload file failed!')

        self.log.info("Step 4: Compare the md5 checksum")
        local_md5 = self.mac_ssh.execute_cmd('md5 {}'.format(self.filename))[0].split()[-1]
        device_md5 = self.ssh_client.execute_cmd('busybox md5sum {0}/{1}'.format('/shares/Public', self.filename))[0]
        if not local_md5.split()[0] == device_md5.split()[0]:
            raise self.err.TestFailure('Basic AFP Write Test Failed! Error: md5 checksum does not match!')
        else:
            self.log.info("md5 checksum matches!")

        self.log.info("Step 5: Start the Read test")
        self.mac_ssh.execute_cmd('sudo cp -f {0}/{1} {2}_clone'.format(self.mountpoint, self.filename, self.filename),
                                 timeout=self.timeout)
        if not self.mac_ssh.check_file_exist('{}_clone'.format(self.filename)):
            raise self.err.TestFailure('Download file failed!')

        self.log.info("Step 6: Compare the md5 checksum")
        local_clone_md5 = self.mac_ssh.execute_cmd('md5 {}_clone'.format(self.filename))[0].split()[-1]
        if not local_md5.split()[0] == local_clone_md5.split()[0]:
            raise self.err.TestFailure('Basic AFP Read Test Failed! Error: md5 checksum does not match!')
        else:
            self.log.info("md5 checksum matches!")

    def after_test(self):
        self.mac_ssh.execute_cmd('sudo rm {}'.format(self.filename))
        self.mac_ssh.execute_cmd('sudo rm {}_clone'.format(self.filename))
        if self.mac_ssh.check_folder_mounted(src_folder=self.share_location, dst_folder=self.mountpoint, protocol='afp'):
            self.mac_ssh.execute_cmd('sudo rm {0}/{1}'.format(self.mountpoint, self.filename))
            self.mac_ssh.execute_cmd('sudo umount {}'.format(self.mountpoint))
        self.mac_ssh.close()

        if self.device_in_inventory:
            self._checkin_device()

        delete_local_file(self.filename)
        delete_local_file("{}_clone".format(self.filename))

    def _checkout_device(self, device_ip=None, uut_platform=None, firmware=None):
        jenkins_job = '{0}-{1}-{2}'.format(os.getenv('JOB_NAME', ''),
                                           os.getenv('BUILD_NUMBER', ''),
                                           self.__class__.__name__)  # Values auto set by jenkins.
        if device_ip: # Device IP has first priority to use.
            self.log.info('Check out a device with IP: {}.'.format(device_ip))
            device = self.inventory.device.get_device_by_ip(device_ip)
            if not device:
                raise self.err.StopTest('Failed to find out the device with specified IP.')
            checkout_device = self.inventory.device.check_out(device['id'], jenkins_job, force=False)
        elif uut_platform: # Find device with matching below conditions.
            self.log.info('Looking for a available device.')
            checkout_device = self.inventory.device.matching_check_out_retry(
                uut_platform, tag='', firmware=firmware, variant='', environment='', uboot='',
                location='', site='', jenkins_job=jenkins_job, retry_counts=24,
                retry_delay=300, force=False
            )
            # retry_delay 180 seconds, retry_count 120 times.
        else:
            raise self.err.StopTest('Device Platform or Device IP is required.')
        return checkout_device

    def _checkin_device(self):
        if not self.inventory.device.check_in(self.device_in_inventory['id'], is_operational=True):
            raise self.err.StopTest('Failed to check in the device.')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** AFP Read/Write Check Script ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/afp_rw_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    parser.add_argument('--inventory_server_ip', help='inventory_server_ip', default='10.6.160.250')
    parser.add_argument('--mac_os', help='mac operating system verison', default='')
    parser.add_argument('--mac_server_ip', help='mac operating system verison', default='')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='fitlab')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac client', default='fituser')
    parser.add_argument('--afp_user', help='AFP login user name', default="admin")
    parser.add_argument('--afp_password', help='AFP login password', default="adminadmin")
    parser.add_argument('--share_folder', help='The test share folder name', default="Public")

    # Test Arguments
    test = AFPRW(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
