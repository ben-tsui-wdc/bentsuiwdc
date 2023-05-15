# -*- coding: utf-8 -*-
""" Test cases to update Firmware image by using fwupdate command for grack.
"""
__author__ = "Vance Lo <Vance.Lo@wdc.com>"

# std modules
import sys
import os
import time
import shutil

# platform modules
from middleware.arguments import GrackInputArgumentParser
from middleware.grack_test_case import GrackTestCase
from platform_libraries.gtech_rpc_api import GTechRPCAPI


class GRackFirmwareUpdate(GrackTestCase):

    TEST_SUITE = 'GRack_BAT'
    TEST_NAME = 'Firmware Update Test'


    def init(self):
        self.outputpath = '/root/app/output'
        self.downpath = 'https://repo.wdtest2.com/content/repositories/grack/'
        self.update_folder = '/mnt/fw_update/'
        self.version = self.env.firmware_version
        self.fw_name = 'gtech_{}_all.deb'.format(self.version)
        self.grack_ssh = GTechRPCAPI(uut_ip=self.env.uut_ip, username='admin', password='gtech', root_password='gtech')

    def test(self):
        # Create update folder
        self.log.info('Creating update folder {}'.format(self.update_folder))
        self.grack_ssh.run_cmd_on_grack('mkdir -p {}'.format(self.update_folder))
        # Remove any image files if already existing
        self.log.info('Removing any files if they exist')
        self.grack_ssh.run_cmd_on_grack('rm -rf {}*'.format(self.update_folder))

        self.log.info('***** Start to download firmware image *****')
        tries = 3
        for i in range(tries):
            try:
                download_url = '{0}{1}/{2}'.format(self.downpath, self.version, self.fw_name)
                self.grack_ssh.run_cmd_on_grack('wget -nv -t 10 {} -P {}'.format(download_url, self.update_folder))
                list = self.grack_ssh.run_cmd_on_grack('ls {}'.format(self.update_folder))[1]
                self.log.info(list)
            except Exception as ex:
                if i < tries - 1:
                    self.log.warning('Exception happened on download firmware part, try again..iter: {0}, Err: {1}'
                                     .format(i+1, ex))
                    continue
                else:
                    raise self.err.StopTest('Download fimware failed after retry {0} times. Err: {1}'.format(tries, ex))
            break

        self.log.info('***** Start to flash firmware image: {} *****'.format(self.version))
        resp = self.grack_ssh.run_cmd_on_grack('dpkg -i {}{}'.format(self.update_folder, self.fw_name))[1]
        self.log.info('Response: {}'.format(resp))
        current_fw = self.grack_ssh.run_cmd_on_grack('dpkg-query -W gtech')[1]
        self.log.info('Current Firmware: {}'.format(current_fw))
        if not self.version in current_fw:
            raise self.err.TestFailure('Current firmware({}) is not match with update firmware({}), Test Failed!!'
                                       .format(current_fw, self.version))
        else:
            self.log.info('Reboot system after flash firmware image ...')
            self.grack_ssh.run_cmd_on_grack('nohup reboot')
            if not self.wait_for_device_to_shutdown():
                raise self.err.TestFailure('Reboot device failed. Device not shutdown.')
            if self.wait_for_device_boot_completed():
                self.log.info('Device is boot completed')
                self.grack_ssh.retry_connect_SSH()
            else:
                raise self.err.TestFailure('Reboot device failed. Device seems down.')
            current_fw = self.grack_ssh.run_cmd_on_grack('dpkg-query -W gtech')[1]
            if self.version not in current_fw:
                raise self.err.TestFailure('Current firmware({}) is not match with update firmware({}), Test Failed!!'
                                           .format(current_fw, self.version))
            else:
                self.log.info('Current firmware: {}, update firmware:{}, test passed!!'.format(current_fw, self.version))
                if os.path.exists(self.outputpath):
                    self.log.info('Update Firmware Success!!!')
                    with open("UpdateSuccess.txt", "w") as f:
                        f.write('Update Firmware Success\n')
                    shutil.copy('UpdateSuccess.txt', '{}/UpdateSuccess.txt'.format(self.outputpath))

    def is_device_pingable(self):
        command = 'nc -zv -w 1 {0} 22 > /dev/null 2>&1'.format(self.env.uut_ip)
        response = os.system(command)
        if response == 0:
            return True
        else:
            return False

    def wait_for_device_to_shutdown(self, timeout=60*3, pingable_count=2):
        start_time = time.time()
        current_count = 0
        while (timeout > time.time() - start_time):
            if not self.is_device_pingable():
                current_count += 1
                self.log.info('Device is not pingable {} time...'.format(current_count))
                if current_count >= pingable_count:
                    self.log.info('Device is shutdown')
                    return True

            self.log.info('Waiting for device to shutdown...')
            time.sleep(5)
        self.log.warning('Device still works')
        return False

    def wait_for_device_boot_completed(self, timeout=60*10, wait_time=5):
        start_time = time.time()
        while (timeout > time.time() - start_time):
            if self.is_device_pingable():
                break
            self.log.info('Device not pingable, wait for 5 secs ...'.format(wait_time))
            time.sleep(wait_time)

        if not (timeout > time.time() - start_time):
            self.log.info('Wait timeout: {}s'.format(timeout))
            return False
        else:
            return True


if __name__ == '__main__':
    parser = GrackInputArgumentParser("""\
        *** Simple Test on Grack Platform ***
        Examples: ./run.sh grack_scripts/grack_test.py --uut_ip 10.92.234.16 --firmware_version 2.2.0.51\
        """)

    test = GRackFirmwareUpdate(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
