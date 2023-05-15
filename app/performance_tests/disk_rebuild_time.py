import argparse
import json
import re
import requests
import sys
import time

from platform_libraries.adblib import ADB
from platform_libraries import common_utils


class disk_rebuild_time(object):
    def __init__(self, uut_ip=None, port=None, adb_server_ip=None, adb_server_port=None):
        self.log = common_utils.create_logger()
        if adb_server_ip:
            self.adb = ADB(adbServer=adb_server_ip, adbServerPort=adb_server_port, uut_ip=uut_ip, port=port)
        else:
            self.adb = ADB(uut_ip=uut_ip, port=port)
        self.adb.connect()
        self.version = self.adb.getFirmwareVersion().split()[0]
        self.file_name = 'TEST_FILE_FOR_DISK_REBUILD'
        self.file_path = '/data/wd/diskVolume0'

    def run(self, iterations=None, failed_disk=None, noresult=None, logstash=None):
        for i in xrange(iterations):
            self.log.info('### iteration: {0} ###'.format(i+1))
            try:
                self.create_random_file(file_name=self.file_name, file_path=self.file_path, file_size=2097152)
                self.original_checksum = self.md5_checksum(file_name=self.file_name, file_path=self.file_path)

                # Mark the specified disk as failed.
                self.adb.executeShellCommand('mdadm /dev/md1 --fail /dev/block/{0}'.format(failed_disk))
                self.checksum_compare()

                # Remove the failed disk from RAID.
                self.adb.executeShellCommand('mdadm /dev/md1 --remove /dev/block/{0}'.format(failed_disk))
                mdadm_status = self.adb.executeShellCommand('mdadm --detail /dev/md1', timeout=10)[0]
                if 'State : clean, degraded' and 'removed' in mdadm_status:
                    pass
                else:
                    self.error('Failed to remove the specified disk: {0} from RAID!!!'.format(failed_disk))
                self.checksum_compare()

                # Re-add the same disk to RAID and wait until the RAID finishing recovering.
                self.adb.executeShellCommand('mdadm /dev/md1 --add /dev/block/{0}'.format(failed_disk))

                rebuild_start_time = time.time()
                while True:
                    mdadm_status = self.adb.executeShellCommand('mdadm --detail /dev/md1', timeout=300)[0]
                    if 'recovering' not in mdadm_status and 'Rebuild Status' not in mdadm_status:
                        break
                    elif time.time() - rebuild_start_time > 86400:  # Accoding to the experiment, Pelican with 8T disk * 2 needs more than 800 mins to rebuild RAID.
                        self.error('disk rebuild doesn\'t finish within 86400 seconds.')
                        sys.exit(1)
                    time.sleep(60)  
                rebuild_total_time = (time.time() - rebuild_start_time)/60

                self.checksum_compare()

                print 'rebuild_total_time: {0} mins'.format(rebuild_total_time)
                self.upload_result(iteration=i+1, rebuild_total_time=rebuild_total_time, noresult=noresult, logstash=logstash)

            except Exception as ex:
                self.error('{0}!'.format(ex))

    # The basic unit of file_size is "512 bytes". 
    def create_random_file(self, file_name=None, file_path=None, file_size=None):
        self.log.info("Creating file: {}...".format(file_name))
        try:
            result = self.adb.executeShellCommand('dd if=/dev/urandom of={0}/{1} count={2}'.format(file_path, file_name, file_size), timeout=600)
        except Exception as e:
            self.error("Failed to create file: {0}/{1}, error message: {2}".format(file_path, file_name, repr(e)))

    def md5_checksum(self, file_name=None, file_path=None):
        result = self.adb.executeShellCommand('md5sum {0}/{1}'.format(file_path, file_name), timeout=600)
        if 'No such file or directory' in result[0]:
            self.error("The tested file: {0}/{1} disappeared !".format(file_path, file_name))
        else:
            result = result[0].strip().split()[0]
            return result

    def checksum_compare(self):
        if self.md5_checksum(file_name=self.file_name, file_path=self.file_path) != self.original_checksum:
            self.error('The md5_checksum is different between before and after removing disk!')

    def device_init(self):
        try:
            self.adb.connect()
            time.sleep(2)
            self.version = self.adb.getFirmwareVersion()
            self.platform = self.adb.getModel()
            self.log.info('Firmware is :{}'.format(self.version.split()[0]))
            self.log.info('Platform is :{}'.format(self.platform.split()[0]))
            time.sleep(1)
            return self.version.split()[0], self.platform.split()[0]
        except Exception as ex:
            self.error('Failed to connect to device and execute adb command! Err: {}'.format(ex))

    def upload_result(self, iteration=None, rebuild_total_time=None, noresult=None, logstash=None):
         # For Report Sequence
        if iteration < 10:
           iteration = '{}_itr_0{}'.format(self.version, iteration)
        else:
           iteration = '{}_itr_{}'.format(self.version, iteration)

        headers = {'Content-Type': 'application/json'}
        data = {'testName': "disk_rebuild_perf",
                'build': self.version,
                'iteration': iteration,
                'rebuild_total_time': rebuild_total_time}
        print data

        if noresult:
            pass
        else:
            print "\n### upload ###\n"
            response = requests.post(url=logstash, data=json.dumps(data), headers=headers)
            if response.status_code == 200:
                print 'Uploaded JSON results to logstash server {0}'.format(logstash)
            else:
                raise Exception('Upload to logstash server {0} failed, {1}, error message: {2}'.format(logstash, response.status_code, response.content))

    def error(self, message):
        """
            Save the error log and raise Exception at the same time
            :param message: The error log to be saved
        """
        self.log.error(message)
        raise Exception(message)
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
    parser.add_argument('--uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('--port', help='Destination port number, ex. 5555 (default)', default='5555')
    parser.add_argument('--failed_disk', help='Specify the disk which is going to be marked as "failed". By default is sataa2.', choices=['sataa2', 'satab2'], default='sataa2')
    parser.add_argument('--iteration', help='Number of test iterations. By default is 1.', default=1)
    parser.add_argument('--noresult', help='If using --noresult, the test result won\'t be upload to logstash', action='store_true')
    parser.add_argument('--logstash', help='Logstash server IP address, by default is 10.92.234.101', default='10.92.234.101')
    parser.add_argument('--adb_server_ip', help='The IP address of adb server, if you want to specify the adb server.')
    parser.add_argument('--adb_server_port', help='The port of adb server, if you want to specify the adb server.')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    if not args.uut_ip:
        print "Please enter uut_ip !"
        sys.exit(1)
    port = args.port
    iterations = int(args.iteration)
    failed_disk = args.failed_disk
    noresult = args.noresult
    logstash = 'http://{0}:8000'.format(args.logstash)

    adb_server_ip = args.adb_server_ip
    adb_server_port = args.adb_server_port
    if adb_server_ip or adb_server_port:
        if adb_server_ip and adb_server_port:
            pass
        else:
            print "If you want to specify the adb server, please enter adb_server_ip and adb_server_port at the same time!"
            sys.exit(1)

    # Create a object
    rebuild_object = disk_rebuild_time(uut_ip=uut_ip, port=port, adb_server_ip=adb_server_ip, adb_server_port=adb_server_port)
    
    # Execute main function
    rebuild_object.run(iterations=iterations, failed_disk=failed_disk, noresult=noresult, logstash=logstash)
